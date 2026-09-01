from __future__ import annotations

from functools import lru_cache
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlparse

from app.settings import settings


class MediaStorageError(RuntimeError):
    pass


def validate_file_signature(data: bytes, content_type: str) -> None:
    signatures = {
        "image/jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
        "image/png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": lambda value: len(value) >= 12 and value.startswith(b"RIFF") and value[8:12] == b"WEBP",
        "image/gif": lambda value: value.startswith((b"GIF87a", b"GIF89a")),
        "video/mp4": lambda value: len(value) >= 12 and value[4:8] == b"ftyp",
        "video/quicktime": lambda value: len(value) >= 12 and value[4:8] == b"ftyp",
        "video/webm": lambda value: value.startswith(b"\x1a\x45\xdf\xa3"),
    }
    validator = signatures.get(content_type.lower())
    if not validator or not validator(data):
        raise MediaStorageError("Uploaded file content does not match its declared media type")


def _safe_key(value: str) -> str:
    key = str(PurePosixPath(str(value).replace("\\", "/"))).lstrip("/")
    if not key or key == "." or ".." in PurePosixPath(key).parts:
        raise MediaStorageError("Invalid media object key")
    return key


class MediaStorage:
    def __init__(self) -> None:
        self.backend = settings.media_storage_backend
        if self.backend not in {"local", "s3"}:
            raise MediaStorageError("MEDIA_STORAGE_BACKEND must be 'local' or 's3'")
        self.local_root = (settings.base_dir / "uploads").resolve()
        self.bucket = settings.s3_media_bucket
        self.region = settings.s3_media_region
        self.endpoint_url = settings.s3_media_endpoint_url or None
        self.key_prefix = settings.s3_media_key_prefix
        self.public_base_url = settings.cloudfront_media_base_url
        self._client = None
        if self.backend == "local":
            self.local_root.mkdir(parents=True, exist_ok=True)
        elif not self.bucket:
            raise MediaStorageError("S3_MEDIA_BUCKET is required when MEDIA_STORAGE_BACKEND=s3")

    @property
    def is_direct_upload_enabled(self) -> bool:
        return self.backend == "s3"

    def _object_key(self, key: str) -> str:
        safe = _safe_key(key)
        return f"{self.key_prefix}/{safe}" if self.key_prefix else safe

    def _s3(self):
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover - packaging guard
                raise MediaStorageError("boto3 is required for S3 media storage") from exc
            self._client = boto3.client("s3", region_name=self.region, endpoint_url=self.endpoint_url)
        return self._client

    def public_url(self, key: str) -> str:
        object_key = self._object_key(key)
        encoded_key = quote(object_key, safe="/")
        if self.backend == "local":
            relative_key = quote(_safe_key(key), safe="/")
            return f"/uploads/{relative_key}"
        if self.public_base_url:
            return f"{self.public_base_url}/{encoded_key}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{encoded_key}"

    def store_bytes(self, key: str, data: bytes, content_type: str) -> str:
        safe = _safe_key(key)
        if not data:
            raise MediaStorageError("Cannot store an empty media object")
        if self.backend == "local":
            target = (self.local_root / Path(*PurePosixPath(safe).parts)).resolve()
            try:
                target.relative_to(self.local_root)
            except ValueError as exc:
                raise MediaStorageError("Invalid local media target") from exc
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return self.public_url(safe)
        self._s3().put_object(
            Bucket=self.bucket,
            Key=self._object_key(safe),
            Body=data,
            ContentType=content_type,
            CacheControl="public,max-age=31536000,immutable",
        )
        return self.public_url(safe)

    def store_private_bytes(self, key: str, data: bytes, content_type: str) -> str:
        safe = _safe_key(key)
        if not data:
            raise MediaStorageError("Cannot store an empty media object")
        if self.backend == "local":
            return self.store_bytes(safe, data, content_type)
        self._s3().put_object(
            Bucket=self.bucket,
            Key=self._object_key(safe),
            Body=data,
            ContentType=content_type,
            CacheControl="private,no-store",
        )
        return f"media://{safe}"

    def delete_key(self, key: str) -> None:
        safe = _safe_key(key)
        if self.backend == "local":
            target = (self.local_root / Path(*PurePosixPath(safe).parts)).resolve()
            try:
                target.relative_to(self.local_root)
            except ValueError:
                return
            target.unlink(missing_ok=True)
            return
        self._s3().delete_object(Bucket=self.bucket, Key=self._object_key(safe))

    def read_private_bytes(self, reference: str | None) -> bytes:
        """Read a private object for an authorized server-side operation."""
        key = self.key_from_url(reference)
        if not key:
            raise MediaStorageError("Invalid private media reference")
        if self.backend == "local":
            target = (self.local_root / Path(*PurePosixPath(key).parts)).resolve()
            try:
                target.relative_to(self.local_root)
            except ValueError as exc:
                raise MediaStorageError("Invalid local media target") from exc
            return target.read_bytes()
        response = self._s3().get_object(Bucket=self.bucket, Key=self._object_key(key))
        return response["Body"].read()

    def key_from_url(self, url: str | None) -> str | None:
        if not url:
            return None
        value = str(url)
        if value.startswith("/uploads/"):
            return _safe_key(unquote(value.removeprefix("/uploads/")))
        if value.startswith("media://"):
            return _safe_key(unquote(value.removeprefix("media://")))
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            return None
        path = unquote(parsed.path.lstrip("/"))
        prefix = f"{self.key_prefix}/" if self.key_prefix else ""
        if not path.startswith(prefix):
            return None
        return _safe_key(path.removeprefix(prefix))

    def delete_url(self, url: str | None) -> None:
        key = self.key_from_url(url)
        if key:
            self.delete_key(key)

    def create_presigned_upload(self, key: str, content_type: str, max_bytes: int) -> dict:
        if self.backend != "s3":
            return {"mode": "backend"}
        safe = _safe_key(key)
        object_key = self._object_key(safe)
        signed = self._s3().generate_presigned_post(
            Bucket=self.bucket,
            Key=object_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, max_bytes],
            ],
            ExpiresIn=settings.s3_presign_ttl_seconds,
        )
        return {
            "mode": "direct",
            "uploadUrl": signed["url"],
            "fields": signed["fields"],
            "objectKey": safe,
            "publicUrl": self.public_url(safe),
            "expiresIn": settings.s3_presign_ttl_seconds,
        }

    def download_url(self, reference: str | None, expires_in: int = 300) -> str | None:
        key = self.key_from_url(reference)
        if not key:
            return reference
        if self.backend == "local" or not str(reference).startswith("media://"):
            return self.public_url(key)
        return self._s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": self._object_key(key)},
            ExpiresIn=expires_in,
        )

    def validate_uploaded_object(self, key: str, content_type: str, max_bytes: int) -> str:
        if self.backend != "s3":
            raise MediaStorageError("Direct upload completion is available only for S3 storage")
        safe = _safe_key(key)
        response = self._s3().head_object(Bucket=self.bucket, Key=self._object_key(safe))
        size = int(response.get("ContentLength") or 0)
        stored_type = str(response.get("ContentType") or "").lower()
        if size <= 0 or size > max_bytes:
            self.delete_key(safe)
            raise MediaStorageError("Uploaded media size is invalid")
        if stored_type != content_type.lower():
            self.delete_key(safe)
            raise MediaStorageError("Uploaded media type does not match the signed request")
        object_response = self._s3().get_object(
            Bucket=self.bucket,
            Key=self._object_key(safe),
            Range="bytes=0-31",
        )
        try:
            validate_file_signature(object_response["Body"].read(), content_type)
        except MediaStorageError:
            self.delete_key(safe)
            raise
        return self.public_url(safe)

    def mark_processed(self, key: str, content_type: str) -> dict:
        safe = _safe_key(key)
        if self.backend == "local":
            return {"processed": True, "mode": "local"}
        self._s3().put_object_tagging(
            Bucket=self.bucket,
            Key=self._object_key(safe),
            Tagging={"TagSet": [
                {"Key": "tailorahub-processed", "Value": "true"},
                {"Key": "content-type", "Value": content_type.replace("/", "-")[:128]},
            ]},
        )
        return {"processed": True, "mode": "s3", "objectKey": safe}


@lru_cache
def get_media_storage() -> MediaStorage:
    return MediaStorage()
