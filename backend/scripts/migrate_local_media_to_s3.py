"""Migrate legacy `/uploads` and dispute data URLs to configured S3 storage.

Dry-run is the default. Set the S3/CloudFront environment variables and pass
`--apply` to upload objects and update database references transactionally.
Local source files are retained for rollback.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
from pathlib import Path, PurePosixPath
import sys
import uuid

from sqlalchemy import text


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import engine
from app.services.media_storage import get_media_storage, validate_file_signature
from app.settings import settings


def local_source(reference: str) -> tuple[str, Path, str] | None:
    if not reference.startswith("/uploads/"):
        return None
    key = reference.removeprefix("/uploads/")
    parts = PurePosixPath(key).parts
    if ".." in parts:
        raise RuntimeError("Unsafe legacy upload path")
    source = (settings.base_dir / "uploads" / Path(*parts)).resolve()
    source.relative_to((settings.base_dir / "uploads").resolve())
    content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    return key, source, content_type


def migrate_reference(reference: str | None, *, private: bool, apply: bool, declared_type: str | None = None) -> tuple[str | None, bool]:
    if not reference or reference.startswith(("http://", "https://", "media://")):
        return reference, False
    legacy = local_source(reference)
    if legacy:
        key, source, content_type = legacy
        if not apply:
            return reference, True
        data = source.read_bytes()
    elif reference.startswith("data:"):
        header, encoded = reference.split(",", 1)
        content_type = declared_type or header.removeprefix("data:").split(";", 1)[0]
        extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(content_type)
        if not extension:
            raise RuntimeError("Unsupported legacy data URL type")
        key = f"private/disputes/migrated/{uuid.uuid4().hex}{extension}"
        if not apply:
            return reference, True
        data = base64.b64decode(encoded, validate=True)
    else:
        return reference, False
    if content_type.startswith(("image/", "video/")):
        validate_file_signature(data, content_type)
    storage = get_media_storage()
    migrated = storage.store_private_bytes(key, data, content_type) if private else storage.store_bytes(key, data, content_type)
    return migrated, True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Upload and update database references")
    args = parser.parse_args()
    if args.apply and settings.media_storage_backend != "s3":
        raise RuntimeError("Set MEDIA_STORAGE_BACKEND=s3 before using --apply")

    migrated = 0
    context = engine.begin() if args.apply else engine.connect()
    with context as connection:
        for row in connection.execute(text("SELECT id, profile_image, portfolio FROM tailors")).mappings():
            profile_url, changed = migrate_reference(row["profile_image"], private=False, apply=args.apply)
            portfolio = list(row["portfolio"] or [])
            next_portfolio = []
            portfolio_changed = False
            for raw_entry in portfolio:
                try:
                    entry = json.loads(raw_entry)
                    next_url, entry_changed = migrate_reference(entry.get("url"), private=False, apply=args.apply, declared_type=entry.get("type"))
                    if entry_changed:
                        entry["url"] = next_url
                        raw_entry = json.dumps(entry)
                        portfolio_changed = True
                        migrated += 1
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
                next_portfolio.append(raw_entry)
            if changed:
                migrated += 1
            if args.apply and (changed or portfolio_changed):
                connection.execute(
                    text("UPDATE tailors SET profile_image=:profile, portfolio=:portfolio WHERE id=:id"),
                    {"profile": profile_url, "portfolio": next_portfolio, "id": row["id"]},
                )

        for table, id_column, url_column, private in (
            ("tailor_offers", "id", "media_url", False),
            ("tailor_wallets", "wallet_id", "qr_code_url", False),
            ("disputes", "id", "photo_url", True),
        ):
            type_column = ", photo_media_type" if table == "disputes" else ""
            rows = connection.execute(text(f"SELECT {id_column}, {url_column}{type_column} FROM {table}")).mappings()
            for row in rows:
                next_url, changed = migrate_reference(
                    row[url_column],
                    private=private,
                    apply=args.apply,
                    declared_type=row.get("photo_media_type"),
                )
                if changed:
                    migrated += 1
                    if args.apply:
                        connection.execute(
                            text(f"UPDATE {table} SET {url_column}=:url WHERE {id_column}=:id"),
                            {"url": next_url, "id": row[id_column]},
                        )

    mode = "migrated" if args.apply else "would migrate"
    print(f"Phase 3 media migration {mode} {migrated} reference(s).")


if __name__ == "__main__":
    main()
