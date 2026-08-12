"""
Minimal dependency-light WAV I/O for the P0-M3-R3 render-shootout harness.

Uses numpy + Python's stdlib `wave` module only (no soundfile/scipy
dependency). Reads/writes 32-bit float PCM (WAVE_FORMAT_IEEE_FLOAT) so
round-tripping never quantizes intermediate renders; the final owner/PM
listening WAVs are written as 16-bit PCM (dither-free truncation is
acceptable for this research pass; documented in README.md).
"""
import struct
import wave
import numpy as np


def _read_riff_chunks(path):
    """
    Manual RIFF/WAVE chunk parser -- Python's stdlib `wave` module refuses
    to read WAVE_FORMAT_IEEE_FLOAT (format tag 3), which this harness uses
    for lossless intermediate renders, so float32 WAVs must be parsed by
    hand here.
    """
    with open(path, "rb") as f:
        riff = f.read(12)
        if riff[0:4] != b"RIFF" or riff[8:12] != b"WAVE":
            raise ValueError(f"{path}: not a RIFF/WAVE file")
        fmt = None
        data = None
        while True:
            header = f.read(8)
            if len(header) < 8:
                break
            chunk_id = header[0:4]
            chunk_size = struct.unpack("<I", header[4:8])[0]
            body = f.read(chunk_size)
            if chunk_size % 2 == 1:
                f.read(1)  # pad byte
            if chunk_id == b"fmt ":
                fmt = struct.unpack("<HHIIHH", body[:16])
            elif chunk_id == b"data":
                data = body
            if fmt is not None and data is not None:
                break
        if fmt is None or data is None:
            raise ValueError(f"{path}: missing fmt/data chunk")
        fmt_tag, n_channels, sample_rate, _byte_rate, _block_align, bits_per_sample = fmt
        return fmt_tag, n_channels, sample_rate, bits_per_sample, data


def read_wav_float(path) -> tuple[np.ndarray, int]:
    """Returns (samples[float32, shape=(n, channels)], sample_rate)."""
    fmt_tag, n_channels, sr, bits_per_sample, raw = _read_riff_chunks(path)
    sampwidth = bits_per_sample // 8
    if fmt_tag == 3 and sampwidth == 4:
        data = np.frombuffer(raw, dtype="<f4").astype(np.float32)
    elif sampwidth == 2:
        data = (np.frombuffer(raw, dtype="<i2").astype(np.float32)) / 32768.0
    elif sampwidth == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        as_i32 = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) |
                  (b[:, 2].astype(np.int32) << 16))
        as_i32 = np.where(as_i32 & 0x800000, as_i32 - 0x1000000, as_i32)
        data = as_i32.astype(np.float32) / 8388608.0
    else:
        raise ValueError(f"unsupported sample width {sampwidth} bytes")
    data = data.reshape(-1, n_channels)
    return data, sr


def write_wav_float32(path, samples: np.ndarray, sample_rate: int):
    """Writes 32-bit IEEE-float PCM WAV. samples shape (n, channels)."""
    if samples.ndim == 1:
        samples = samples[:, None]
    n_frames, n_channels = samples.shape
    data = np.ascontiguousarray(samples.astype("<f4"))
    _write_wav_raw(path, data.tobytes(), n_channels, sample_rate, sampwidth=4, is_float=True)


def write_wav_pcm16(path, samples: np.ndarray, sample_rate: int):
    """Writes 16-bit integer PCM WAV (for the blinded listening pack)."""
    if samples.ndim == 1:
        samples = samples[:, None]
    n_frames, n_channels = samples.shape
    clipped = np.clip(samples, -1.0, 0.999969)
    ints = np.round(clipped * 32767.0).astype("<i2")
    _write_wav_raw(path, np.ascontiguousarray(ints).tobytes(), n_channels, sample_rate, sampwidth=2, is_float=False)


def _write_wav_raw(path, raw_bytes: bytes, n_channels: int, sample_rate: int, sampwidth: int, is_float: bool):
    if not is_float:
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(sample_rate)
            wf.writeframes(raw_bytes)
        return

    # Python's `wave` module cannot write WAVE_FORMAT_IEEE_FLOAT (format tag
    # 3) directly -- build the RIFF/fmt/data chunks by hand for float32.
    byte_rate = sample_rate * n_channels * sampwidth
    block_align = n_channels * sampwidth
    fmt_chunk = struct.pack(
        "<HHIIHH", 3, n_channels, sample_rate, byte_rate, block_align, sampwidth * 8
    )
    data_chunk = raw_bytes
    riff_size = 4 + (8 + len(fmt_chunk)) + (8 + len(data_chunk))
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", riff_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", len(fmt_chunk)))
        f.write(fmt_chunk)
        f.write(b"data")
        f.write(struct.pack("<I", len(data_chunk)))
        f.write(data_chunk)
