"""The only networking in the app is the explicit, verified model installer."""

import hashlib
import os
from pathlib import Path
import urllib.request

import numpy as np
import onnxruntime as ort
from PIL import Image

URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
SHA256 = "8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491"
SIZE = 175997641


def model_path():
    return (
        Path(os.environ.get("DEALERSTUDIO_MODELS", Path.home() / ".dealerstudio" / "models")) / "u2net.onnx"
    )


def verified(path):
    if not path.is_file() or path.stat().st_size != SIZE:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == SHA256


def install(progress=lambda value: None):
    path = model_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".download")
    try:
        with urllib.request.urlopen(URL, timeout=60) as response, tmp.open("wb") as out:
            total = 0
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
                total += len(chunk)
                progress(min(99, int(total * 100 / SIZE)))
        if not verified(tmp):
            raise ValueError("Model checksum failed. Retry setup; no unverified weights will run.")
        tmp.replace(path)
        progress(100)
    finally:
        tmp.unlink(missing_ok=True)


class Segmenter:
    def __init__(self, cpu=False):
        path = model_path()
        if not verified(path):
            raise RuntimeError(f"Install the U²-Net model (176 MB) using Model setup. Expected: {path}")
        providers = ["CPUExecutionProvider"]
        if not cpu and "CUDAExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "CUDAExecutionProvider")
        options = ort.SessionOptions()
        options.intra_op_num_threads = max(1, min(4, os.cpu_count() or 1))
        try:
            self.session = ort.InferenceSession(str(path), sess_options=options, providers=providers)
        except Exception:
            self.session = ort.InferenceSession(
                str(path), sess_options=options, providers=["CPUExecutionProvider"]
            )

    def predict(self, image):
        pixels = np.asarray(
            image.convert("RGB").resize((320, 320), Image.Resampling.LANCZOS), dtype=np.float32
        )
        pixels /= max(float(pixels.max()), 1.0)
        pixels = (pixels - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
            [0.229, 0.224, 0.225], dtype=np.float32
        )
        output = self.session.run(None, {self.session.get_inputs()[0].name: pixels.transpose(2, 0, 1)[None]})[
            0
        ][0, 0]
        span = float(output.max() - output.min())
        if span < 1e-8:
            raise RuntimeError("No usable foreground found. Use another photo or create a manual mask.")
        output = (output - output.min()) / span
        return Image.fromarray((output.clip(0, 1) * 255).astype("uint8")).resize(
            image.size, Image.Resampling.LANCZOS
        )
