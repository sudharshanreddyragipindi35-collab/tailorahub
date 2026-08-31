from __future__ import annotations

import os
import urllib.request


def main() -> None:
    if os.getenv("SERVICE_ROLE", "web").strip().lower() != "web":
        return
    port = os.getenv("PORT", "8001")
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=4) as response:
        if response.status >= 400:
            raise RuntimeError(f"Health endpoint returned HTTP {response.status}")


if __name__ == "__main__":
    main()
