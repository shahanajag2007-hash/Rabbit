"""Download every wheel the worker needs with resumable retries, then install from the local folder.

For slow or unstable connections, where pip's own downloads of the large PyTorch / Intel runtime wheels
keep failing. Usage (from tools/tryon-worker):  python fetch_wheels.py --device xpu
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
WHEELS = HERE / ".wheels"
INDEX = {"cuda": "https://download.pytorch.org/whl/cu124", "xpu": "https://download.pytorch.org/whl/xpu",
         "cpu": "https://download.pytorch.org/whl/cpu"}


def download(url: str, target: Path, size: int | None) -> None:
    for attempt in range(30):
        have = target.stat().st_size if target.exists() else 0
        if size and have >= size:
            return
        request = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, open(target, "ab" if have else "wb") as out:
                while chunk := response.read(1 << 20):
                    out.write(chunk)
            if not size or target.stat().st_size >= size:
                return
        except Exception as exc:  # resume on the next attempt
            print(f"  {target.name}: {type(exc).__name__}, resuming (attempt {attempt + 1})", flush=True)
            time.sleep(5)
    raise SystemExit(f"Could not download {url}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=list(INDEX), default="xpu")
    args = parser.parse_args()
    py = str(HERE / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
    WHEELS.mkdir(exist_ok=True)
    report = HERE / ".wheels" / "report.json"
    subprocess.check_call([py, "-m", "pip", "install", "--dry-run", "--ignore-installed", "--report", str(report),
                           "torch", "torchvision", "--extra-index-url", INDEX[args.device], "-r", str(HERE / "requirements.txt")])
    for item in json.loads(report.read_text(encoding="utf-8"))["install"]:
        info = item["download_info"]
        url = info["url"]
        name = url.rsplit("/", 1)[-1].replace("%2B", "+")
        if not name.endswith(".whl"):
            continue
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as head:
            size = int(head.headers.get("Content-Length") or 0) or None
        print(f"{name} ({(size or 0) / 1e6:.0f} MB) ...", flush=True)
        download(url, WHEELS / name, size)
    subprocess.check_call([py, "-m", "pip", "install", "--no-index", "--find-links", str(WHEELS), "torch", "torchvision",
                           "-r", str(HERE / "requirements.txt")])
    print("installed from local wheels")


if __name__ == "__main__":
    main()
