"""One-time setup of the open-source try-on worker (run with any Python 3.10-3.12):

    python setup_worker.py                 # auto-detects an NVIDIA GPU, else Intel GPU (XPU) build, else CPU
    python setup_worker.py --device cuda   # force a PyTorch build: cuda | xpu | cpu
    python setup_worker.py --skip-weights  # don't pre-download the ~3 GB of model weights now

It creates tools/tryon-worker/.venv (nothing is installed into your global Python), downloads the CatVTON
source at a pinned commit into vendor/ and the MediaPipe segmentation model into models/, and caches the
model weights in your Hugging Face cache. All of these are git-ignored.
"""
from __future__ import annotations

import argparse
import io
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
CATVTON_COMMIT = "7818397f25613beedb3d861a34769f607cfcf3b1"
SEGMENTER_URL = "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite"
TORCH_INDEX = {"cuda": "https://download.pytorch.org/whl/cu124", "xpu": "https://download.pytorch.org/whl/xpu",
               "cpu": "https://download.pytorch.org/whl/cpu"}


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.check_call(list(args))


def detect_device() -> str:
    if shutil.which("nvidia-smi"):
        return "cuda"
    if sys.platform == "win32":
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_VideoController).Name"],
                             capture_output=True, text=True).stdout
        if "Intel" in out and "Arc" in out:
            return "xpu"
    return "cpu"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=["auto", "cuda", "xpu", "cpu"], default="auto")
    parser.add_argument("--skip-weights", action="store_true")
    parser.add_argument("--resumable", action="store_true", help="download wheels with resumable retries (slow connections)")
    args = parser.parse_args()
    device = detect_device() if args.device == "auto" else args.device
    print(f"PyTorch build: {device}")

    if not venv_python().exists():
        run(sys.executable, "-m", "venv", str(VENV))
    py = str(venv_python())
    run(py, "-m", "pip", "install", "--upgrade", "pip")
    if args.resumable:  # slow / unstable connections: resumable downloads, then install from .wheels/
        run(py, str(HERE / "fetch_wheels.py"), "--device", device)
    else:
        run(py, "-m", "pip", "install", "torch", "torchvision", "--index-url", TORCH_INDEX[device])
        run(py, "-m", "pip", "install", "-r", str(HERE / "requirements.txt"))

    vendor = HERE / "vendor" / "CatVTON"
    if not (vendor / "model" / "pipeline.py").exists():
        print(f"Downloading CatVTON source ({CATVTON_COMMIT[:8]}) ...")
        data = urllib.request.urlopen(f"https://github.com/Zheng-Chong/CatVTON/archive/{CATVTON_COMMIT}.zip", timeout=120).read()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            archive.extractall(HERE / "vendor")
        shutil.move(str(HERE / "vendor" / f"CatVTON-{CATVTON_COMMIT}"), str(vendor))

    models = HERE / "models"
    models.mkdir(exist_ok=True)
    if not (models / "selfie_multiclass_256x256.tflite").exists():
        urllib.request.urlretrieve(SEGMENTER_URL, models / "selfie_multiclass_256x256.tflite")

    if not args.skip_weights:
        # Into plain folders under models/hf (no cache symlinks: those need Developer Mode on Windows).
        root = (models / "hf").as_posix()
        code = ("from huggingface_hub import snapshot_download as s;"
                f"s('stable-diffusion-v1-5/stable-diffusion-inpainting', allow_patterns=['scheduler/*','unet/config.json',"
                f"'unet/diffusion_pytorch_model.fp16.safetensors'], local_dir='{root}/stable-diffusion-v1-5--stable-diffusion-inpainting');"
                f"s('stabilityai/sd-vae-ft-mse', allow_patterns=['config.json','diffusion_pytorch_model.safetensors'], local_dir='{root}/stabilityai--sd-vae-ft-mse');"
                f"s('zhengchong/CatVTON', allow_patterns=['mix-48k-1024/*'], local_dir='{root}/zhengchong--CatVTON')")
        run(py, "-c", code)
    print(f"\nDone. Start the worker with:  {py} {HERE / 'server.py'}")


if __name__ == "__main__":
    main()
