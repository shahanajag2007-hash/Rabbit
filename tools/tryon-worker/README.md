# STYLEAI try-on worker (open-source, self-hosted)

Runs **CatVTON** (an open-source virtual try-on model) behind a small HTTP API, so STYLEAI can generate
photo try-ons repeatedly without a hosted quota or per-image fee. You pay in hardware time instead: the
model needs a few GB of disk and memory and is slow without a GPU.

The main app uses it when `STYLEAI_TRYON_PROVIDER` includes `worker` (the default chain in `.env.example`
is `worker,huggingface`: the worker when it is running, otherwise the hosted IDM-VTON Space).

## Licence — read before using

CatVTON's code and weights are licensed **CC BY-NC-SA 4.0**: non-commercial use only, with attribution,
and derivative work under the same licence. That suits a student / research project; it does not allow
commercial use. The worker therefore lives in its own folder, downloads CatVTON at setup time (it is not
committed to this repository) and is licensed separately — see [LICENSE-NOTICE.md](LICENSE-NOTICE.md).
The base model (Stable Diffusion 1.5 inpainting, `stable-diffusion-v1-5/stable-diffusion-inpainting`, half-precision UNet) is under the CreativeML OpenRAIL-M licence.

## Hardware

| Machine | Expected speed per image (30 steps) | Setup |
| --- | --- | --- |
| NVIDIA GPU with ≥ 8 GB VRAM | tens of seconds | `python setup_worker.py --device cuda` |
| Intel Arc / Core Ultra integrated GPU (XPU) | minutes (untested — see below) | `python setup_worker.py --device xpu` |
| CPU only | many minutes; development only | `python setup_worker.py --device cpu` |

Disk: ~2.2 GB of model weights (models/hf) + ~3 GB for PyTorch. RAM: 16 GB or more.
Image size defaults to 768×1024 on NVIDIA, 576×768 on Intel GPUs and 384×512 on CPU (`TRYON_SIZE` overrides).

The worker does not need to run on every teammate's laptop: one machine with a GPU (or a free notebook
GPU such as Kaggle's weekly allowance, subject to its terms) can run it, and everyone points
`STYLEAI_TRYON_WORKER_URL` at it. Teammates without it can still use every other feature.

## Setup and run

```bash
cd tools/tryon-worker
python setup_worker.py            # creates .venv, installs PyTorch + dependencies, downloads CatVTON and weights
.venv/Scripts/python server.py    # Windows  (macOS / Linux: .venv/bin/python server.py)
```

The first start loads the model (a minute or more); `GET http://127.0.0.1:8100/health` shows `"ready": true`
when it can take requests. Then start STYLEAI as usual with `STYLEAI_TRYON_PROVIDER=worker` (or the default
chain) in `.env`.

Slow or unstable connection? `python setup_worker.py --resumable` downloads every wheel with resumable
retries into `.wheels/` and installs from there. Model weights go into plain folders under `models/hf/`
(no Hugging Face cache symlinks, which Windows only allows in Developer Mode); interrupted weight downloads
resume when you run the setup again.

## How it works

1. `masking.py` finds the garment area with MediaPipe (clothes / skin segmentation + pose landmarks):
   upper body for tops, waist to ankles for bottoms, shoulders to ankles for sets and dresses. The face,
   hair and hands are never repainted.
2. The photo is padded (not cropped) to 3:4 so the head and feet stay in frame.
3. CatVTON repaints the masked area with the garment image (top, then bottom wear).
4. Everything outside the mask is copied back from the original photo.

Settings: `TRYON_DEVICE` (auto | cuda | xpu | cpu), `TRYON_STEPS` (30), `TRYON_SIZE` (e.g. 768x1024),
`TRYON_HOST` / `TRYON_PORT` (127.0.0.1:8100). The worker keeps no copies of the images it receives.
