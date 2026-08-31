from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_NAMES = {
    ".env",
    "admin-credentials.txt",
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p8", ".jks", ".keystore", ".zip", ".tgz"}
SCREENSHOT_SUFFIXES = {".png", ".jpg", ".jpeg"}
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Razorpay live key": re.compile(r"\brzp_live_[A-Za-z0-9]{8,}\b"),
    "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
}
FRONTEND_SECRET_NAME = re.compile(r"\bVITE_[A-Z0-9_]*(?:SECRET|PASSWORD|PRIVATE|AADHAAR|DATABASE)[A-Z0-9_]*\b")
TEXT_SUFFIXES = {
    ".css", ".html", ".js", ".json", ".jsx", ".md", ".mjs", ".py", ".sh",
    ".sql", ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.name.lower() in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"forbidden tracked artifact: {relative}")
            continue
        if relative.startswith("deployment/") and path.suffix.lower() in SCREENSHOT_SUFFIXES:
            findings.append(f"deployment screenshot must not be tracked: {relative}")
            continue
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 2_000_000:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {relative}")
        if relative.startswith("frontend/") and FRONTEND_SECRET_NAME.search(text):
            findings.append(f"server secret exposed through VITE variable: {relative}")

    if findings:
        print("Secret hygiene check failed:")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1
    print(f"Secret hygiene check passed for {len(tracked_files())} tracked files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
