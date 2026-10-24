"""STYLEAI try-on worker: CatVTON (open-source) behind a tiny HTTP API.

    POST /tryon   multipart: person (image), garment (image), category = upper | lower | overall
                  -> image/png of the person wearing the garment
    GET  /health  -> {"ready": bool, "device": ..., "model": ..., "error": ...}

Run (after `python setup_worker.py`):  .venv/Scripts/python server.py    (macOS/Linux: .venv/bin/python server.py)
The main app uses it with STYLEAI_TRYON_PROVIDER=worker (and STYLEAI_TRYON_WORKER_URL if not local).

Environment: TRYON_DEVICE (auto | cuda | xpu | cpu), TRYON_STEPS (default 30), TRYON_SIZE (e.g. 768x1024;
default depends on the device), TRYON_PORT (8100), TRYON_HOST (127.0.0.1).

Licence: CatVTON code and weights are CC BY-NC-SA 4.0 (non-commercial use, attribution, share-alike);
see LICENSE-NOTICE.md. This worker is kept separate from the main application for that reason.
"""
from __future__ import annotations

import io
import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor" / "CatVTON"
sys.path.insert(0, str(VENDOR))

import uvicorn  # noqa: E402
from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from PIL import Image  # noqa: E402

import masking  # noqa: E402

# Stable Diffusion 1.5 inpainting (CatVTON's base model). The official repo ships a half-precision UNet
# (1.7 GB instead of 3.4 GB); it is upcast on CPU, so the result is the same model.
BASE_MODEL = os.environ.get("TRYON_BASE_MODEL", "stable-diffusion-v1-5/stable-diffusion-inpainting")
ATTN_MODEL = os.environ.get("TRYON_ATTN_MODEL", "zhengchong/CatVTON")
VAE_MODEL = "stabilityai/sd-vae-ft-mse"
ATTN_VERSION = "mix"
MAX_UPLOAD = 15 * 1024 * 1024
MODELS = HERE / "models" / "hf"


def local_model(repo: str) -> Path:
    path = MODELS / repo.replace("/", "--")
    if not path.exists():
        raise FileNotFoundError(f"{repo} is not downloaded; run setup_worker.py (expected in {path}).")
    return path

state = {"ready": False, "loading": True, "error": None, "device": None, "dtype": None, "load_seconds": None}
pipeline = None
inference_lock = threading.Lock()


def pick_device() -> str:
    import torch

    wanted = os.environ.get("TRYON_DEVICE", "auto").lower()
    if wanted != "auto":
        return wanted
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        return "xpu"
    return "cpu"


def default_size(device: str) -> tuple[int, int]:
    if os.environ.get("TRYON_SIZE"):
        w, h = os.environ["TRYON_SIZE"].lower().split("x")
        return int(w), int(h)
    # CatVTON is trained at 768x1024; smaller sizes are faster on integrated GPUs / CPUs, at some quality cost.
    return {"cuda": (768, 1024), "xpu": (576, 768)}.get(device, (384, 512))


def load() -> None:
    global pipeline
    started = time.time()
    try:
        import torch
        from diffusers import AutoencoderKL, UNet2DConditionModel
        from model.pipeline import CatVTONPipeline

        device = pick_device()
        dtype = torch.float16 if device in ("cuda", "xpu") else torch.float32
        state.update(device=device, dtype=str(dtype).replace("torch.", ""))
        # Plain local folders (models/hf, filled by setup_worker.py): no Hugging Face cache symlinks, which
        # Windows only allows in Developer Mode, and only the folders that are used.
        base, attn, vae = (str(local_model(BASE_MODEL)), str(local_model(ATTN_MODEL)), str(local_model(VAE_MODEL)))
        original = AutoencoderKL.from_pretrained.__func__
        # CatVTON loads the VAE by its Hub id; point that id at the local copy.
        AutoencoderKL.from_pretrained = classmethod(lambda cls, name, *a, **k: original(cls, vae if name == VAE_MODEL else name, *a, **k))
        if (Path(base) / "unet" / "diffusion_pytorch_model.fp16.safetensors").exists():
            unet_original = UNet2DConditionModel.from_pretrained.__func__
            UNet2DConditionModel.from_pretrained = classmethod(lambda cls, *a, **k: unet_original(cls, *a, variant="fp16", **k))
        pipeline = CatVTONPipeline(base_ckpt=base, attn_ckpt=attn, attn_ckpt_version=ATTN_VERSION,
                                   weight_dtype=dtype, device=device, skip_safety_check=True, use_tf32=device == "cuda")
        state.update(ready=True, load_seconds=round(time.time() - started, 1))
    except Exception as exc:  # reported by /health; the main app shows it to the user
        state["error"] = f"{type(exc).__name__}: {exc}"[:500]
    finally:
        state["loading"] = False


app = FastAPI(title="STYLEAI try-on worker")


@app.on_event("startup")
def _startup() -> None:
    threading.Thread(target=load, daemon=True).start()


@app.get("/health")
def health():
    device = state.get("device") or "unknown"
    w, h = default_size(device) if device != "unknown" else (None, None)
    return {**state, "model": f"catvton-{ATTN_VERSION}", "steps": int(os.environ.get("TRYON_STEPS", "30")),
            "size": f"{w}x{h}" if w else None, "license": "CC BY-NC-SA 4.0 (non-commercial)"}


async def _read(upload: UploadFile) -> Image.Image:
    data = await upload.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Image too large.")
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=422, detail="Unreadable image.")


@app.post("/tryon")
async def tryon(person: UploadFile = File(...), garment: UploadFile = File(...), category: str = Form("upper"),
                seed: int = Form(42)):
    if not state["ready"]:
        raise HTTPException(status_code=503, detail=state["error"] or "The model is still loading.")
    if category not in ("upper", "lower", "overall"):
        raise HTTPException(status_code=422, detail="category must be upper, lower or overall")
    import torch
    from utils import resize_and_padding

    person_img, garment_img = await _read(person), await _read(garment)
    try:
        mask = masking.garment_mask(person_img, category)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    width, height = default_size(state["device"])
    padded, box = masking.pad_to_ratio(person_img, width / height)
    padded_mask, _ = masking.pad_to_ratio(mask, width / height)
    steps = int(os.environ.get("TRYON_STEPS", "30"))
    with inference_lock:  # one image at a time; further requests wait
        generator = torch.Generator(device="cpu").manual_seed(seed)
        result = pipeline(
            image=padded.resize((width, height), Image.LANCZOS),
            condition_image=resize_and_padding(garment_img, (width, height)),
            mask=padded_mask.resize((width, height), Image.NEAREST),
            num_inference_steps=steps, guidance_scale=2.5, height=height, width=width, generator=generator,
        )[0]
    # Back to the original framing, keeping everything outside the garment area from the original photo.
    scale_x, scale_y = width / padded.width, height / padded.height
    crop = result.crop((round(box[0] * scale_x), round(box[1] * scale_y), round(box[2] * scale_x), round(box[3] * scale_y)))
    final = masking.blend_back(person_img, crop, mask)
    out = io.BytesIO()
    final.save(out, format="PNG")
    return Response(content=out.getvalue(), media_type="image/png")


if __name__ == "__main__":
    uvicorn.run(app, host=os.environ.get("TRYON_HOST", "127.0.0.1"), port=int(os.environ.get("TRYON_PORT", "8100")))
