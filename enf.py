import io
import hashlib
from dataclasses import dataclass
from typing import Tuple

import numpy as np
from scipy import signal
from scipy.io import wavfile
import matplotlib.pyplot as plt

@dataclass
class EnfSeries:
    t: np.ndarray
    f: np.ndarray
    quality: float
    f_mean: float
    f_std: float

def _bandpass(x: np.ndarray, fs: int, f0: float = 50.0, bw: float = 2.0, order: int = 4) -> np.ndarray:
    """Narrow bandpass around mains frequency (50Hz)"""
    low = max(0.1, f0 - bw) / (fs / 2.0)
    high = (f0 + bw) / (fs / 2.0)
    b, a = signal.butter(order, [low, high], btype="bandpass")
    return signal.filtfilt(b, a, x)

def _inst_freq_hilbert(x: np.ndarray, fs: int) -> np.ndarray:
    """Instantaneous frequency estimate via Hilbert analytic signal."""
    analytic = signal.hilbert(x)
    phase = np.unwrap(np.angle(analytic))
    # derivative of phase -> angular frequency
    dphi = np.diff(phase)
    inst_f = (fs / (2.0 * np.pi)) * dphi
    # pad to match length
    inst_f = np.concatenate([inst_f[:1], inst_f])
    return inst_f

def extract_enf_from_wav(wav_path: str, mains_hz: float = 50.0) -> Tuple[str, bytes, float, float, float]:
    """
    Extract ENF time-series around mains_hz, compute hash, and generate a real ENF PNG plot.

    Returns: (enf_hash, png_bytes, quality_score, f_mean, f_std)
    """
    fs, x = wavfile.read(wav_path)
    if x.ndim > 1:
        x = x[:, 0]
    # normalize to float32 [-1, 1]
    if x.dtype != np.float32:
        x = x.astype(np.float32)
        mx = np.max(np.abs(x)) + 1e-12
        x = x / mx

    # highpass a bit to remove DC/rumble
    b_hp, a_hp = signal.butter(2, 20/(fs/2), btype="highpass")
    x_hp = signal.filtfilt(b_hp, a_hp, x)

    # narrow band around 50 Hz
    x_bp = _bandpass(x_hp, fs, f0=mains_hz, bw=2.0, order=4)

    # quality estimation: energy in band vs broadband
    band_rms = float(np.sqrt(np.mean(x_bp**2) + 1e-12))
    broad_rms = float(np.sqrt(np.mean(x_hp**2) + 1e-12))
    snr_like = band_rms / (broad_rms + 1e-12)  # 0..1-ish
    # map to 0..100
    quality = float(np.clip(100.0 * (snr_like / 0.15), 0.0, 100.0))  # 0.15 is empirical

    # instantaneous frequency
    inst_f = _inst_freq_hilbert(x_bp, fs)

    # smooth to reduce jitter, then downsample to e.g. 10 Hz series
    # (ENF varies slowly; we don't need fs resolution)
    win = int(max(5, fs * 0.2))  # 200ms window
    if win % 2 == 0:
        win += 1
    inst_f_smooth = signal.medfilt(inst_f, kernel_size=win)

    step = int(fs / 10)  # 10 samples per second
    if step < 1:
        step = 1
    f_series = inst_f_smooth[::step]
    t_series = np.arange(len(f_series)) / 10.0

    # remove obvious outliers far from mains (bad segments)
    mask = (f_series > mains_hz - 3.0) & (f_series < mains_hz + 3.0)
    if np.sum(mask) >= max(5, int(0.3 * len(f_series))):
        f_use = f_series[mask]
        t_use = t_series[mask]
    else:
        # ENF not reliably detectable
        f_use = f_series
        t_use = t_series
        quality = min(quality, 25.0)

    f_mean = float(np.mean(f_use)) if len(f_use) else float("nan")
    f_std = float(np.std(f_use)) if len(f_use) else float("nan")

    # hash the time-series (rounded for stability)
    f_q = np.round(f_use.astype(np.float64), 4)
    h = hashlib.sha256(f_q.tobytes()).hexdigest()

    # generate real ENF plot PNG
    fig, ax = plt.subplots(figsize=(7, 2.2), dpi=150)
    ax.plot(t_use, f_use)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("frequency (Hz)")
    ax.set_title("Estimated ENF (mains frequency track)")
    ax.grid(True, which="both", linestyle=":", linewidth=0.5)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    png_bytes = buf.getvalue()

    return h, png_bytes, quality, f_mean, f_std
