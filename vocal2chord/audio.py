"""Audio ingestion: load any common format to mono float32, peak-normalised."""
from __future__ import annotations
import os, subprocess, tempfile
import numpy as np


def load_audio(path: str, normalize: bool = True):
    """Return (mono float32 signal, sample rate). Uses soundfile, falls back to ffmpeg."""
    import soundfile as sf
    try:
        y, sr = sf.read(path, dtype="float32", always_2d=True)
    except Exception:
        with tempfile.TemporaryDirectory() as d:
            wav = os.path.join(d, "x.wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", wav], check=True)
            y, sr = sf.read(wav, dtype="float32", always_2d=True)
    y = y.mean(axis=1)
    if normalize:
        peak = float(np.max(np.abs(y))) if y.size else 0.0
        if peak > 1e-6:
            y = y * (0.95 / peak)
    return y.astype(np.float32), int(sr)


def resample(y: np.ndarray, sr: int, target: int) -> np.ndarray:
    if sr == target:
        return y
    from scipy.signal import resample_poly
    g = int(np.gcd(sr, target))
    return resample_poly(y, target // g, sr // g).astype(np.float32)


def save_wav(path: str, y: np.ndarray, sr: int):
    import soundfile as sf
    sf.write(path, np.clip(y, -1, 1), sr, subtype="PCM_16")
