import io
import hashlib
from typing import Tuple

import numpy as np
from scipy import signal
from scipy.io import wavfile

# 🔴 BITNO ZA FLY / DOCKER
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


def _bandpass(
    x: np.ndarray,
    fs: int,
    f0: float = 50.0,
    bw: float = 1.5,
    order: int = 4
) -> np.ndarray:
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
) -> Tuple[str, bytes, bytes, float, float, float]:

    fs, x = wavfile.read(wav_path)

    if x.ndim > 1:
        x = x[:, 0]

    duration = len(x) / fs
    if duration < min_seconds:
        raise ValueError("Clip too short for reliable ENF")

    x = x.astype(np.float32)
    x /= (np.max(np.abs(x)) + 1e-12)

    # ---------------- HIGH-PASS ----------------
    b_hp, a_hp = signal.butter(2, 20 / (fs / 2), btype="highpass")
    x_hp = signal.filtfilt(b_hp, a_hp, x)

    # ---------------- BAND-PASS ----------------
    x_bp = _bandpass(x_hp, fs, f0=mains_hz)

    # ---------------- QUALITY ----------------
    freqs, psd = signal.welch(x_hp, fs, nperseg=fs * 2)

    band = (freqs > mains_hz - 0.3) & (freqs < mains_hz + 0.3)
    neigh = (freqs > mains_hz - 5) & (freqs < mains_hz + 5)

    snr_like = np.sum(psd[band]) / (np.sum(psd[neigh]) + 1e-12)
    quality = float(np.clip(100 * (snr_like / 0.12), 0, 100))

    # ---------------- INSTANT FREQUENCY ----------------
    inst_f = _inst_freq_hilbert(x_bp, fs)

    win = int(fs * 0.4) | 1
    inst_f = signal.medfilt(inst_f, kernel_size=win)

    step = int(fs / 10)  # 10 Hz ENF sampling
    f_series = inst_f[::step]
    t_series = np.arange(len(f_series)) / 10.0

    mask = (f_series > mains_hz - 2) & (f_series < mains_hz + 2)
    f_use = f_series[mask]
    t_use = t_series[mask]

    f_mean = float(np.mean(f_use))
    f_std = float(np.std(f_use))

    enf_hash = hashlib.sha256(
        np.round(f_use, 4).tobytes()
    ).hexdigest()

    # ================= TRACE GRAPH =================
    fig1, ax1 = plt.subplots(figsize=(7, 2.2), dpi=150)

    ax1.plot(t_use, f_use, linewidth=1.2)
    ax1.set_xlabel("time (s)")
    ax1.set_ylabel("frequency (Hz)")
    ax1.set_title("Estimated ENF (mains frequency track)")
    ax1.grid(True, linestyle=":", linewidth=0.5)

    buf_trace = io.BytesIO()
    fig1.tight_layout()
    fig1.savefig(buf_trace, format="png")
    plt.close(fig1)

    # ================= SPECTROGRAM (IMPROVED) =================
    fig2, ax2 = plt.subplots(figsize=(7, 2.2), dpi=150)

    Pxx, freqs_s, bins, im = ax2.specgram(
        x_hp,
        NFFT=2048,
        Fs=fs,
        noverlap=1536,
        cmap="inferno",
        scale="dB"
    )

    ax2.set_ylim(mains_hz - 5, mains_hz + 5)
    ax2.set_xlabel("time (s)")
    ax2.set_ylabel("frequency (Hz)")
    ax2.set_title("ENF Spectrogram (raw signal, dB scale)")

    cbar = fig2.colorbar(im, ax=ax2)
    cbar.set_label("Power (dB)")

    buf_spec = io.BytesIO()
    fig2.tight_layout()
    fig2.savefig(buf_spec, format="png")
    plt.close(fig2)

    return (
        enf_hash,
        buf_trace.getvalue(),
        buf_spec.getvalue(),
        quality,
        f_mean,
        f_std
    )
