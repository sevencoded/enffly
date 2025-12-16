import io
import hashlib
from typing import Tuple

import numpy as np
from scipy import signal
from scipy.io import wavfile
import matplotlib.pyplot as plt


def _bandpass(x: np.ndarray, fs: int, f0: float = 50.0, bw: float = 1.5, order: int = 4) -> np.ndarray:
    low = max(0.1, f0 - bw) / (fs / 2.0)
    high = (f0 + bw) / (fs / 2.0)
    b, a = signal.butter(order, [low, high], btype="bandpass")
    return signal.filtfilt(b, a, x)


def _inst_freq_hilbert(x: np.ndarray, fs: int) -> np.ndarray:
    analytic = signal.hilbert(x)
    phase = np.unwrap(np.angle(analytic))
    dphi = np.diff(phase)
    inst_f = (fs / (2.0 * np.pi)) * dphi
    return np.concatenate([inst_f[:1], inst_f])


def extract_enf_from_wav(
    wav_path: str,
    mains_hz: float = 50.0,
    min_seconds: float = 30.0
) -> Tuple[str, bytes, float, float, float]:

    fs, x = wavfile.read(wav_path)

    if x.ndim > 1:
        x = x[:, 0]

    duration = len(x) / fs
    if duration < min_seconds:
        raise ValueError("Clip too short for reliable ENF (min 30s required)")

    x = x.astype(np.float32)
    x /= (np.max(np.abs(x)) + 1e-12)

    # high-pass (remove DC / rumble)
    b_hp, a_hp = signal.butter(2, 20 / (fs / 2), btype="highpass")
    x_hp = signal.filtfilt(b_hp, a_hp, x)

    # band-pass around mains
    x_bp = _bandpass(x_hp, fs, f0=mains_hz)

    # --- QUALITY (band vs neighborhood PSD) ---
    freqs, psd = signal.welch(x_hp, fs, nperseg=fs * 2)

    band_mask = (freqs > mains_hz - 0.3) & (freqs < mains_hz + 0.3)
    neigh_mask = (freqs > mains_hz - 5) & (freqs < mains_hz + 5)

    band_power = np.sum(psd[band_mask])
    neigh_power = np.sum(psd[neigh_mask]) + 1e-12

    snr_like = band_power / neigh_power
    quality = float(np.clip(100.0 * (snr_like / 0.12), 0.0, 100.0))

    # instantaneous frequency
    inst_f = _inst_freq_hilbert(x_bp, fs)

    # smoother window (400 ms)
    win = int(fs * 0.4)
    if win % 2 == 0:
        win += 1

    inst_f_smooth = signal.medfilt(inst_f, kernel_size=win)

    step = int(fs / 10)
    f_series = inst_f_smooth[::step]
    t_series = np.arange(len(f_series)) / 10.0

    mask = (f_series > mains_hz - 2.0) & (f_series < mains_hz + 2.0)

    if np.sum(mask) < int(0.4 * len(f_series)):
        quality = min(quality, 30.0)

    f_use = f_series[mask]
    t_use = t_series[mask]

    f_mean = float(np.mean(f_use))
    f_std = float(np.std(f_use))

    f_q = np.round(f_use.astype(np.float64), 4)
    h = hashlib.sha256(f_q.tobytes()).hexdigest()

    # --- PLOT ---
    fig, ax = plt.subplots(figsize=(7, 2.2), dpi=150)
    ax.plot(t_use, f_use)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("frequency (Hz)")
    ax.set_title("Estimated ENF (mains frequency track)")
    ax.grid(True, linestyle=":", linewidth=0.5)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)

    return h, buf.getvalue(), quality, f_mean, f_std
