from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from studio import model


def test_missing_model_is_actionable_and_never_downloads(monkeypatch, tmp_path):
    monkeypatch.setenv("DEALERSTUDIO_MODELS", str(tmp_path))
    monkeypatch.setattr(model.urllib.request, "urlopen", lambda *_a, **_k: pytest.fail("Unexpected download"))
    with pytest.raises(RuntimeError, match="Model setup"):
        model.Segmenter()


def test_cuda_failure_falls_back_to_cpu(monkeypatch):
    # Dependency-boundary fixture only. Real model execution is verification/run_real.py.
    monkeypatch.setattr(model, "verified", lambda _: True)
    monkeypatch.setattr(
        model.ort, "get_available_providers", lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]
    )
    calls = []

    def create_session(*_args, **kwargs):
        calls.append(kwargs["providers"])
        if "CUDAExecutionProvider" in kwargs["providers"]:
            raise RuntimeError("No CUDA device")
        return SimpleNamespace()

    monkeypatch.setattr(model.ort, "InferenceSession", create_session)
    model.Segmenter()
    assert calls == [["CUDAExecutionProvider", "CPUExecutionProvider"], ["CPUExecutionProvider"]]


def test_all_black_preprocessing_is_finite_and_empty_prediction_errors(monkeypatch):
    segmenter = object.__new__(model.Segmenter)

    def run(_names, feed):
        tensor = feed["input"]
        assert tensor.shape == (1, 3, 320, 320)
        assert np.isfinite(tensor).all()
        return [np.zeros((1, 1, 320, 320), dtype=np.float32)]

    segmenter.session = SimpleNamespace(get_inputs=lambda: [SimpleNamespace(name="input")], run=run)
    with pytest.raises(RuntimeError, match="No usable foreground"):
        segmenter.predict(Image.new("RGB", (100, 80)))


def test_install_rejects_bad_weights_and_removes_partial_file(tmp_path, monkeypatch):
    import io

    monkeypatch.setenv("DEALERSTUDIO_MODELS", str(tmp_path))
    monkeypatch.setattr(model.urllib.request, "urlopen", lambda *_a, **_k: io.BytesIO(b"invalid weights"))
    with pytest.raises(ValueError, match="checksum"):
        model.install()
    assert not model.model_path().exists()
    assert not model.model_path().with_suffix(".download").exists()
