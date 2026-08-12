"""
P0-M3-R3 STAGE B -- owner real-music corpus analyzer.

Inventories the PM-authorized local-only root (passed via `--input-root`,
never hardcoded in this file so it stays generic/reusable, and so the
authorized root's own path never appears in a committed file) and
computes, per
track, the same class of local structural/compatibility evidence the R2
planner and pair-compatibility gate (tools/p0m3/transition_policy/policy/
compatibility.py, eligibility.py) already consume for synthetic fixtures --
tempo/BPM, beat grid, downbeat phase, key/chroma, loudness, an
HEURISTIC_PROXY vocal-density curve, and intro/outro texture regions.

This project does not have librosa/essentia/madmom/BeatNet available in
this environment (see docs/research/P0-M3-R1-ANALYZER-SHOOTOUT.md for the
prior ML-analyzer feasibility pass) -- every estimator below is implemented
from scratch on top of numpy/scipy using standard, well-known, textbook DSP
techniques (STFT spectral-flux onset detection, autocorrelation tempo
estimation, Krumhansl-Schmuckler key-profile correlation). None of this is
claimed to be as accurate as a trained ML beat/vocal model; every output
carries an explicit confidence/HEURISTIC_PROXY label per
`.agents/skills/automix-forensic-research/SKILL.md`'s capability
classification -- LOW/MEDIUM/HIGH confidence is a measured property of the
signal (autocorrelation peak prominence, key-profile correlation margin),
never invented certainty.

PRIVACY (Issue #7 PM STAGE B comment):
- Only decodes files strictly inside `--input-root` (rejects any resolved
  path that is not a descendant of it).
- Never prints a filename, absolute path, or any owner-file-derived string
  to stdout/stderr -- only opaque IDs (RM001, RM002, ...) and counts.
- Writes the ID->path mapping and full per-track analysis to a LOCAL-ONLY,
  gitignored output directory (`real_music/work_local/corpus/`); writes a
  SEPARATE sanitized aggregate-only summary (counts/histograms, no
  filenames/IDs-to-paths) that is safe to commit as PM evidence.

Usage:
    python scripts/analyze_owner_corpus.py --input-root "<owner-supplied local music root>" --out-dir real_music/work_local/corpus
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

FFMPEG_BIN = shutil.which("ffmpeg")
FFPROBE_BIN = shutil.which("ffprobe")
if not FFMPEG_BIN or not FFPROBE_BIN:
    import os
    for root, _dirs, files in os.walk(Path.home() / "AppData/Local/Microsoft/WinGet/Packages"):
        if "Gyan.FFmpeg" not in root:
            continue
        if not FFMPEG_BIN and "ffmpeg.exe" in files:
            FFMPEG_BIN = str(Path(root) / "ffmpeg.exe")
        if not FFPROBE_BIN and "ffprobe.exe" in files:
            FFPROBE_BIN = str(Path(root) / "ffprobe.exe")
        if FFMPEG_BIN and FFPROBE_BIN:
            break

ANALYSIS_SR = 22050
SUPPORTED_EXTS = {".wav", ".flac", ".mp3", ".m4a"}

N_FFT = 2048
HOP = 512
FRAME_RATE = ANALYSIS_SR / HOP  # frames per second, ~43.07

# ---- confidence bucket thresholds (documented PROJECT heuristics, not any external standard) ----
CONF_ORDER = ["NONE", "LOW", "MEDIUM", "HIGH"]


def bucket(value, high_t, med_t, low_t):
    if value >= high_t:
        return "HIGH"
    if value >= med_t:
        return "MEDIUM"
    if value >= low_t:
        return "LOW"
    return "NONE"


# PM STAGE B REVIEW R1 repair: real owner-local embedded-tag genre/style
# evidence, never a fabricated universal default. Deliberately excludes the
# "title" tag field -- a song title's incidental wording (e.g. a track
# literally titled "...Rock Paper Scissors...") must never be misread as a
# genre signal. A generic YouTube video-category tag (e.g. "Music",
# "Entertainment") is NOT genre evidence and is deliberately NOT in this
# map -- it does not distinguish any of compatibility.py's recognized
# genre families. Only recognized, documented keywords are mapped through
# to compatibility.py's own COMPATIBLE_GENRE_FAMILIES vocabulary; anything
# else stays UNKNOWN (empty list), which the existing R2 genre_ok gate
# already treats as GENRE_INCOMPATIBLE (empty-set intersection) -- no
# change to compatibility.py was needed or made.
GENRE_TAG_FIELDS = ("genre", "comment", "description", "synopsis")
GENRE_KEYWORD_MAP = {
    "k-pop": "pop", "kpop": "pop", "k pop": "pop", "dance pop": "pop", "pop": "pop",
    "hip hop": "hip-hop", "hip-hop": "hip-hop", "hiphop": "hip-hop",
    "r&b": "r&b", "r n b": "r&b", "rnb": "r&b", "soul": "soul",
    "rock": "rock", "indie": "indie",
    "house": "house", "edm": "edm", "electronic": "electronic", "techno": "techno",
    "dance": "dance", "disco": "disco",
    "ambient": "ambient", "downtempo": "downtempo", "chillout": "chillout",
}


def probe_format_tags(path: Path) -> dict:
    cmd = [FFPROBE_BIN, "-v", "quiet", "-print_format", "json", "-show_entries", "format_tags", str(path)]
    result = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    try:
        d = json.loads(result.stdout)
        return {k.lower(): v for k, v in d.get("format", {}).get("tags", {}).items()}
    except Exception:  # noqa: BLE001
        return {}


def match_genre_keywords(tags: dict):
    """Pure, file-I/O-free matcher (unit-testable without ffprobe/a real
    file -- see scripts/mutation_test_real_music_stage_b.py mutation #1).
    `tags` is a lowercase-keyed dict as returned by probe_format_tags().
    Returns (genre_tags: list[str], provenance: str). Never returns the raw
    tag text -- only the small set of RECOGNIZED, documented keyword
    tokens that were matched (or an empty list when none were)."""
    seen_values = set()
    matched = set()
    for field in GENRE_TAG_FIELDS:
        val = (tags.get(field) or "").strip()
        if not val or val in seen_values:
            continue  # dedupe identical field values (e.g. description == synopsis)
        seen_values.add(val)
        low = val.lower()
        for kw, mapped in GENRE_KEYWORD_MAP.items():
            if kw in low:
                matched.add(mapped)
    if matched:
        return sorted(matched), (
            "OWNER_LOCAL_EMBEDDED_TAG_KEYWORD_MATCH: matched against a documented sanitizer "
            "vocabulary from genre/comment/description/synopsis tag fields (never 'title', to "
            "avoid incidental wordplay false positives); raw tag text never written to committed "
            "evidence; no web enrichment performed"
        )
    return [], "UNKNOWN: no recognized genre/style keyword found in owner-local embedded tag fields; not web-enriched, not fabricated"


def extract_local_genre_tags(path: Path):
    """Returns (genre_tags: list[str], provenance: str) for a real local file."""
    return match_genre_keywords(probe_format_tags(path))


def decode_mono_pcm(path: Path, sr: int = ANALYSIS_SR) -> np.ndarray:
    cmd = [FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed exit={result.returncode}")
    audio = np.frombuffer(result.stdout, dtype="<f4").astype(np.float32).copy()
    return audio


def stft_mag(x: np.ndarray, n_fft: int = N_FFT, hop: int = HOP):
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    window = np.hanning(n_fft).astype(np.float32)
    n_frames = 1 + (len(x) - n_fft) // hop
    shape = (n_frames, n_fft)
    strides = (x.strides[0] * hop, x.strides[0])
    frames = np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides).copy()
    frames *= window
    spec = np.fft.rfft(frames, axis=1)
    mag = np.abs(spec).astype(np.float32)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / ANALYSIS_SR)
    return mag, freqs


def band_mask(freqs, lo, hi):
    return (freqs >= lo) & (freqs < hi)


def onset_envelope(mag: np.ndarray, mask: np.ndarray) -> np.ndarray:
    sub = mag[:, mask]
    flux = np.diff(sub, axis=0)
    flux = np.clip(flux, 0.0, None)
    return flux.sum(axis=1)


def frame_rms_db(x: np.ndarray, n_fft: int = N_FFT, hop: int = HOP) -> np.ndarray:
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    n_frames = 1 + (len(x) - n_fft) // hop
    shape = (n_frames, n_fft)
    strides = (x.strides[0] * hop, x.strides[0])
    frames = np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    with np.errstate(divide="ignore"):
        db = 20.0 * np.log10(np.maximum(rms, 1e-12))
    return db.astype(np.float32)


def estimate_tempo(onset_env: np.ndarray, bpm_min=70.0, bpm_max=190.0):
    env = onset_env - onset_env.mean()
    lag_min = max(1, int(round(FRAME_RATE * 60.0 / bpm_max)))
    lag_max = int(round(FRAME_RATE * 60.0 / bpm_min))
    lag_max = min(lag_max, len(env) - 1)
    best_lag, best_val = lag_min, -1.0
    vals = []
    for lag in range(lag_min, lag_max + 1):
        a, b = env[:-lag], env[lag:]
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        val = float(np.dot(a, b) / denom) if denom > 0 else 0.0
        vals.append(val)
        if val > best_val:
            best_val, best_lag = val, lag
    vals = np.array(vals)
    mean_v, std_v = float(vals.mean()), float(vals.std() + 1e-9)
    prominence = (best_val - mean_v) / std_v
    bpm = 60.0 * FRAME_RATE / best_lag
    conf = bucket(min(prominence / 5.0, best_val), 0.45, 0.25, 0.12)
    if prominence < 1.8:
        conf = "LOW" if conf != "NONE" else "NONE"
    return {
        "bpm": round(float(bpm), 2),
        "period_frames": best_lag,
        "acf_peak": round(best_val, 4),
        "acf_prominence": round(float(prominence), 3),
        "confidence": conf,
    }


def estimate_beat_phase(onset_env: np.ndarray, period_frames: int):
    n = len(onset_env)
    scores = []
    for phase in range(period_frames):
        idx = np.arange(phase, n, period_frames)
        if len(idx) < 4:
            scores.append(-np.inf)
            continue
        scores.append(float(onset_env[idx].mean()))
    scores = np.array(scores)
    finite = scores[np.isfinite(scores)]
    best_phase = int(np.argmax(scores))
    best_score = float(scores[best_phase])
    margin = (best_score - finite.mean()) / (finite.std() + 1e-9) if finite.size else 0.0
    # Thresholds calibrated against this corpus's own observed margin
    # distribution (see analyzer commit notes) -- a >=1.5 SD peak across
    # dozens of candidate phase hypotheses is a genuinely non-arbitrary lock,
    # not an inflated pass threshold.
    conf = bucket(margin, 1.5, 0.8, 0.3)
    return best_phase, conf, round(float(margin), 3)


def _zscore(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    return (x - x.mean()) / (x.std() + 1e-9)


def estimate_downbeat_phase(low_onset_env: np.ndarray, broadband_onset_env: np.ndarray, beat_phase: int, period_frames: int):
    """
    Bar-phase (downbeat) estimator: sums z-scored low-band (<150Hz, kick-ish)
    and broadband onset envelopes (standard weak-evidence-ensemble technique
    -- combining two independently-noisy onset detectors improves SNR when a
    real periodic bar-accent exists, without inventing certainty when it
    doesn't). Empirically, using ONLY the low-band kick-energy signal gave
    near-zero group separation on this corpus's four-on-the-floor-style
    dance/pop material (kick frequently falls on every beat, not just the
    downbeat, so bass energy alone often cannot reveal bar phase -- an
    honest DSP limitation, not a bug); the combined signal is measurably
    more discriminative on tracks where a real periodic bar-level accent
    exists (chord change, fill, texture shift), and stays low-margin
    (correctly low confidence) on tracks where it does not.
    """
    n = min(len(low_onset_env), len(broadband_onset_env))
    combined = _zscore(low_onset_env[:n]) + _zscore(broadband_onset_env[:n])
    beat_idx = np.arange(beat_phase, n, period_frames)
    if len(beat_idx) < 16:
        return 0, "NONE", 0.0
    group_scores = []
    for k in range(4):
        sel = beat_idx[k::4]
        sel = sel[sel < n]
        group_scores.append(float(combined[sel].mean()) if len(sel) else -np.inf)
    group_scores = np.array(group_scores)
    order = np.argsort(-group_scores)
    best, second = group_scores[order[0]], group_scores[order[1]]
    denom = abs(group_scores.mean()) + 1e-9
    margin = (best - second) / denom
    conf = bucket(margin, 1.0, 0.35, 0.12)
    return int(order[0]), conf, round(float(margin), 3)


KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def chroma_vector(mag: np.ndarray, freqs: np.ndarray) -> np.ndarray:
    mask = (freqs >= 80.0) & (freqs <= 2100.0)
    f = freqs[mask]
    m = mag[:, mask]
    # energetic frames only (drop near-silence to avoid diluting tonal content)
    frame_energy = m.sum(axis=1)
    thresh = np.percentile(frame_energy, 40) if len(frame_energy) else 0.0
    keep = frame_energy >= thresh
    m = m[keep] if keep.any() else m
    pitch_class = np.mod(np.round(12.0 * np.log2(f / 440.0) + 69.0), 12).astype(int)
    chroma = np.zeros(12, dtype=np.float64)
    for pc in range(12):
        sel = pitch_class == pc
        if sel.any():
            chroma[pc] = m[:, sel].sum()
    return chroma


def estimate_key(chroma: np.ndarray):
    total = chroma.sum()
    if total <= 0:
        return {"root": None, "mode": None, "correlation": 0.0, "margin": 0.0, "confidence": "NONE"}
    v = chroma / total
    scores = []
    for root in range(12):
        maj = np.roll(KS_MAJOR, root)
        minr = np.roll(KS_MINOR, root)
        maj_c = float(np.corrcoef(v, maj)[0, 1])
        min_c = float(np.corrcoef(v, minr)[0, 1])
        scores.append((root, "major", maj_c))
        scores.append((root, "minor", min_c))
    scores.sort(key=lambda t: -t[2])
    best_root, best_mode, best_corr = scores[0]
    margin = best_corr - scores[1][2]
    conf = bucket(min(best_corr, margin * 4), 0.55, 0.35, 0.15)
    return {
        "root": PITCH_CLASSES[best_root],
        "mode": best_mode,
        "correlation": round(best_corr, 4),
        "margin": round(margin, 4),
        "confidence": conf,
    }


def vocal_density_curve(mag: np.ndarray, freqs: np.ndarray) -> np.ndarray:
    """HEURISTIC_PROXY only -- no source separation / trained vocal model available in
    this environment. Combines (a) energy fraction in the 300-3400Hz vocal-formant band
    and (b) tonal salience (1 - spectral flatness) in that band, since sustained
    harmonic/tonal energy concentrated in the vocal-formant range is a reasonable, but
    not certain, proxy for vocal presence versus purely percussive/instrumental content."""
    mask = band_mask(freqs, 300.0, 3400.0)
    band = mag[:, mask]
    total = mag.sum(axis=1) + 1e-9
    band_ratio = band.sum(axis=1) / total
    geo_mean = np.exp(np.mean(np.log(band + 1e-6), axis=1))
    arith_mean = band.mean(axis=1) + 1e-6  # same epsilon floor as geo_mean -- see spectral_flatness_curve's note
    flatness = np.clip(geo_mean / arith_mean, 0.0, 1.0)
    tonal_salience = np.clip(1.0 - flatness, 0.0, 1.0)
    density = band_ratio * tonal_salience
    # smooth ~1s (FRAME_RATE frames/sec)
    win = max(1, int(round(FRAME_RATE * 1.0)))
    kernel = np.ones(win) / win
    smoothed = np.convolve(density, kernel, mode="same")
    return smoothed.astype(np.float32)


def find_instrumental_tail(vocal_density: np.ndarray, rms_db: np.ndarray, frame_rate: float,
                            search_from_frac: float, min_len_s: float, floor_db: float):
    """Scans BACKWARD from near end-of-track for the longest low-vocal-density,
    above-floor-energy run starting no earlier than search_from_frac*duration."""
    n = len(vocal_density)
    if n == 0:
        return None
    median_vd = float(np.median(vocal_density))
    low_thresh = 0.55 * median_vd if median_vd > 0 else 0.05
    start_search = int(n * search_from_frac)
    is_instrumental = (vocal_density <= low_thresh) & (rms_db >= floor_db)
    best_run = None
    run_start = None
    for i in range(start_search, n):
        if is_instrumental[i]:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                run_len_s = (i - run_start) / frame_rate
                if run_len_s >= min_len_s:
                    best_run = (run_start, i)  # keep the LAST qualifying run (closest to end)
                run_start = None
    if run_start is not None:
        run_len_s = (n - run_start) / frame_rate
        if run_len_s >= min_len_s:
            best_run = (run_start, n)
    return best_run


def find_instrumental_lead(vocal_density: np.ndarray, rms_db: np.ndarray, frame_rate: float,
                            search_until_frac: float, min_len_s: float, floor_db: float):
    n = len(vocal_density)
    if n == 0:
        return None
    median_vd = float(np.median(vocal_density))
    low_thresh = 0.55 * median_vd if median_vd > 0 else 0.05
    end_search = int(n * search_until_frac)
    is_instrumental = (vocal_density <= low_thresh) & (rms_db >= floor_db)
    if not is_instrumental[0]:
        return None
    i = 0
    while i < min(end_search, n) and is_instrumental[i]:
        i += 1
    run_len_s = i / frame_rate
    if run_len_s >= min_len_s:
        return (0, i)
    return None


def spectral_centroid_curve(mag: np.ndarray, freqs: np.ndarray, mask: np.ndarray) -> np.ndarray:
    m = mag[:, mask]
    f = freqs[mask]
    total = m.sum(axis=1) + 1e-9
    return (m @ f) / total


def spectral_flatness_curve(mag: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Bounded in [0,1] by the AM-GM inequality for any actual signal; a
    mismatched epsilon floor between the geometric- and arithmetic-mean
    terms can blow this up past 1.0 on near-digital-silence frames (the
    geo-mean epsilon dominates while the arith-mean can underflow closer to
    its own, smaller floor) -- both terms use the SAME epsilon here, plus
    an explicit clip as a safety net, so a near-silent frame reads as
    "flat" (flatness ~1.0), not a nonsensical >1 ratio."""
    m = mag[:, mask]
    geo = np.exp(np.mean(np.log(m + 1e-6), axis=1))
    arith = m.mean(axis=1) + 1e-6
    return np.clip(geo / arith, 0.0, 1.0)


def band_rms_db_curve(mag: np.ndarray, freqs: np.ndarray, lo: float, hi: float) -> np.ndarray:
    mask = band_mask(freqs, lo, hi)
    m = mag[:, mask]
    energy = np.sqrt(np.mean(m.astype(np.float64) ** 2, axis=1)) if m.shape[1] > 0 else np.zeros(mag.shape[0])
    with np.errstate(divide="ignore"):
        db = 20.0 * np.log10(np.maximum(energy, 1e-9))
    return db


def onset_density_per_s(onset_env: np.ndarray, frame_rate: float, start_frame: int, end_frame: int, z_thresh: float = 1.0) -> float:
    """Percussive/rhythmic-texture proxy: local-peak rate in the onset envelope over [start,end)."""
    start_frame = max(0, start_frame)
    end_frame = min(len(onset_env), end_frame)
    seg = onset_env[start_frame:end_frame]
    if len(seg) < 3:
        return 0.0
    z = (seg - seg.mean()) / (seg.std() + 1e-9)
    peaks = 0
    for i in range(1, len(z) - 1):
        if z[i] > z_thresh and z[i] >= z[i - 1] and z[i] >= z[i + 1]:
            peaks += 1
    duration_s = len(seg) / frame_rate
    return peaks / duration_s if duration_s > 0 else 0.0


def bar_synchronous_novelty(mag: np.ndarray, freqs: np.ndarray, rms_db: np.ndarray,
                             centroid_curve: np.ndarray, flatness_curve: np.ndarray,
                             beat_phase: int, period_frames: int, n_frames: int):
    """
    PM STAGE B REVIEW R2 repair: independent bar-synchronous structural-
    change ("novelty") curve, computed from RMS/chroma/spectral-centroid/
    spectral-flatness -- deliberately NEVER from beat/downbeat CONFIDENCE
    itself (only from the bar_period the beat/downbeat estimate defines, to
    know where bar boundaries fall; a wrong bar phase degrades this like
    any real segmentation algorithm, it does not fabricate structure).
    A standard, textbook self-similarity/novelty technique (adjacent-bar
    feature distance; Foote-style, simplified) -- not beat-grid-derived
    certainty.

    Returns None if there are too few bars to attempt segmentation
    meaningfully (caller must then treat structure as UNKNOWN).
    """
    bar_period = period_frames * 4
    bar_starts = list(range(beat_phase, n_frames - bar_period, bar_period))
    if len(bar_starts) < 6:
        return None

    feats_rms, feats_cen, feats_fla, feats_chroma = [], [], [], []
    for s in bar_starts:
        e = s + bar_period
        feats_rms.append(float(np.mean(rms_db[s:e])))
        feats_cen.append(float(np.mean(centroid_curve[s:e])))
        feats_fla.append(float(np.mean(flatness_curve[s:e])))
        c = chroma_vector(mag[s:e], freqs)
        feats_chroma.append(c / (c.sum() + 1e-9))

    rms_z = _zscore(np.array(feats_rms))
    cen_z = _zscore(np.array(feats_cen))
    fla_z = _zscore(np.array(feats_fla))
    chromas = np.array(feats_chroma)

    novelty = np.zeros(len(bar_starts))
    for i in range(1, len(bar_starts)):
        d_rms = abs(rms_z[i] - rms_z[i - 1])
        d_cen = abs(cen_z[i] - cen_z[i - 1])
        d_fla = abs(fla_z[i] - fla_z[i - 1])
        a, b = chromas[i], chromas[i - 1]
        denom = np.linalg.norm(a) * np.linalg.norm(b) + 1e-9
        d_chroma = 1.0 - float(np.dot(a, b) / denom)
        # Harmonic/chroma change is weighted higher -- a chord/section
        # change is the strongest, least-ambiguous structural-boundary
        # signal among these four; RMS/centroid/flatness corroborate.
        novelty[i] = d_rms + d_cen + d_fla + 4.0 * d_chroma

    return {"bar_start_frames": bar_starts, "bar_period_frames": bar_period, "novelty": novelty}


def find_nearest_novelty_peak(novelty_result: dict, target_frame: int, frame_rate: float, min_prominence_z: float = 1.0):
    """Returns (prominence_z, distance_bars) for the strongest novelty peak within +-1 bar
    of target_frame, or None if none qualifies."""
    if novelty_result is None:
        return None
    novelty = novelty_result["novelty"]
    bar_starts = novelty_result["bar_start_frames"]
    bar_period = novelty_result["bar_period_frames"]
    mean_n, std_n = float(novelty.mean()), float(novelty.std() + 1e-9)
    best = None
    for i in range(1, len(novelty) - 1):
        is_local_peak = novelty[i] > novelty[i - 1] and novelty[i] >= novelty[i + 1]
        if not is_local_peak:
            continue
        z = (novelty[i] - mean_n) / std_n
        if z < min_prominence_z:
            continue
        distance_bars = abs(bar_starts[i] - target_frame) / bar_period
        if distance_bars <= 1.0 and (best is None or z > best[0]):
            best = (z, distance_bars)
    return best


def nearest_downbeat_ms(target_frame: int, downbeat_phase: int, beat_phase: int, period_frames: int, frame_rate: float):
    bar_period = period_frames * 4
    base = beat_phase + downbeat_phase * period_frames
    k = round((target_frame - base) / bar_period)
    nearest_frame = base + k * bar_period
    return max(0.0, nearest_frame / frame_rate * 1000.0)


def analyze_one(path: Path) -> dict:
    pcm = decode_mono_pcm(path)
    duration_s = len(pcm) / ANALYSIS_SR
    mag, freqs = stft_mag(pcm)
    rms_db = frame_rms_db(pcm)
    n_frames = mag.shape[0]
    if len(rms_db) > n_frames:
        rms_db = rms_db[:n_frames]
    elif len(rms_db) < n_frames:
        n_frames = len(rms_db)
        mag = mag[:n_frames]

    broadband_mask = band_mask(freqs, 30.0, 8000.0)
    low_mask = band_mask(freqs, 30.0, 150.0)
    onset_env = onset_envelope(mag, broadband_mask)
    low_onset_env = onset_envelope(mag, low_mask)

    tempo = estimate_tempo(onset_env)
    beat_phase, beat_conf, beat_margin = estimate_beat_phase(onset_env, tempo["period_frames"])
    downbeat_phase, downbeat_conf, downbeat_margin = estimate_downbeat_phase(low_onset_env, onset_env, beat_phase, tempo["period_frames"])

    chroma = chroma_vector(mag, freqs)
    key = estimate_key(chroma)

    # PM STAGE B REVIEW R2/R3 repair: independent (non-beat/downbeat-
    # derived) structural, timbral, and low-frequency-activity curves.
    centroid_curve = spectral_centroid_curve(mag, freqs, broadband_mask)
    flatness_curve = spectral_flatness_curve(mag, broadband_mask)
    bass_energy_curve = band_rms_db_curve(mag, freqs, 30.0, 150.0)
    bass_p25 = float(np.percentile(bass_energy_curve, 25))
    bass_p60 = float(np.percentile(bass_energy_curve, 60))

    def _bass_bucket(value: float) -> str:
        if value <= bass_p25:
            return "LOW"
        if value <= bass_p60:
            return "MEDIUM"
        return "HIGH"

    # Bar-synchronous novelty curve for INDEPENDENT structure evidence (R2).
    # Only attempted when the downbeat estimate has at least some measured
    # confidence (NONE means the bar phase itself is untrustworthy, so
    # target-vs-peak bar alignment would be meaningless) -- otherwise
    # structure stays honestly UNKNOWN via the fallback path below.
    novelty_result = None
    if downbeat_conf != "NONE":
        novelty_result = bar_synchronous_novelty(
            mag, freqs, rms_db, centroid_curve, flatness_curve,
            beat_phase, tempo["period_frames"], n_frames,
        )

    vocal_density = vocal_density_curve(mag, freqs)
    median_vd = float(np.median(vocal_density)) if len(vocal_density) else 0.0
    # Per-track PERCENTILE-based risk bucketing (not a fixed multiplier of
    # the median): a track that carries dense vocal/ad-lib texture
    # throughout should be judged against ITS OWN distribution, not an
    # absolute threshold that would call every region of a vocal-dense
    # track "risky" regardless of relative variation.
    vd_p25 = float(np.percentile(vocal_density, 25)) if len(vocal_density) else 0.0
    vd_p60 = float(np.percentile(vocal_density, 60)) if len(vocal_density) else 0.0

    def _vocal_risk_bucket(value: float) -> str:
        if value <= vd_p25:
            return "LOW"
        if value <= vd_p60:
            return "MEDIUM"
        return "HIGH"

    silence_floor_db = float(np.percentile(rms_db, 15)) - 3.0 if len(rms_db) else -60.0
    silence_floor_db = max(silence_floor_db, -55.0)

    tail = find_instrumental_tail(vocal_density, rms_db, FRAME_RATE, search_from_frac=0.55, min_len_s=5.0, floor_db=silence_floor_db)
    lead = find_instrumental_lead(vocal_density, rms_db, FRAME_RATE, search_until_frac=0.20, min_len_s=2.5, floor_db=silence_floor_db)

    # Authored LEADING SILENCE (e.g. a logo-bumper/near-silent pre-roll some
    # MV exports carry before the music starts) is real non-musical content,
    # distinct from an "instrumental lead" (audible-but-vocal-free intro).
    # Skipping it is the boundary planner's own documented
    # AUTHORED_LEADING_SILENCE_SKIPPED path -- leaving entry_candidate_t_ms
    # at 0 inside true digital silence would both be a bad transition point
    # and would corrupt the entry-region loudness/vocal-density readings
    # used elsewhere in this analysis.
    hard_silence_floor_db = -50.0
    lead_silence_end_frame = 0
    while lead_silence_end_frame < n_frames and rms_db[lead_silence_end_frame] < hard_silence_floor_db:
        lead_silence_end_frame += 1
    lead_silence_end_ms = lead_silence_end_frame / FRAME_RATE * 1000.0
    has_leading_silence = lead_silence_end_ms >= 500.0 and lead_silence_end_frame < n_frames

    duration_ms = duration_s * 1000.0
    min_tail_margin_s = 14.0  # leave room for overlap + post-roll

    if tail is not None:
        tail_start_frame, tail_end_frame = tail
        exit_t_ms = nearest_downbeat_ms(tail_start_frame, downbeat_phase, beat_phase, tempo["period_frames"], FRAME_RATE)
        exit_t_ms = min(exit_t_ms, duration_ms - min_tail_margin_s * 1000.0)
        exit_t_ms = max(exit_t_ms, 0.0)
        is_outro_tail_opportunity = True
        exit_vocal_density = float(np.mean(vocal_density[tail_start_frame:tail_end_frame]))
        exit_energy_db = float(np.mean(rms_db[tail_start_frame:tail_end_frame]))
        # PM STAGE B REVIEW R2 repair: structural evidence for the exit
        # candidate must be INDEPENDENT of beat/downbeat confidence. A
        # detected sustained instrumental tail (vocal-density-based, not
        # beat-based) IS independent structural evidence -- the strongest
        # available -- so this branch alone may claim HIGH.
        exit_structure_confidence = "HIGH"
        exit_novelty_peak_detected = True
        exit_novelty_z = None
    else:
        fallback_frame = int(max(0, (duration_ms - min_tail_margin_s * 1000.0) / 1000.0 * FRAME_RATE))
        exit_t_ms = nearest_downbeat_ms(fallback_frame, downbeat_phase, beat_phase, tempo["period_frames"], FRAME_RATE)
        exit_t_ms = min(exit_t_ms, duration_ms - min_tail_margin_s * 1000.0)
        exit_t_ms = max(exit_t_ms, 0.0)
        is_outro_tail_opportunity = False
        win = min(n_frames, int(round(FRAME_RATE * 6.0)))
        f0 = max(0, min(n_frames - win, int(exit_t_ms / 1000.0 * FRAME_RATE)))
        exit_vocal_density = float(np.mean(vocal_density[f0:f0 + win])) if win > 0 else median_vd
        exit_energy_db = float(np.mean(rms_db[f0:f0 + win])) if win > 0 else float(np.mean(rms_db))
        # PM STAGE B REVIEW R2 repair: NO formally-detected instrumental
        # tail -- the ONLY remaining path to independent structural
        # evidence is a genuine bar-synchronous novelty (RMS/chroma/
        # centroid/flatness change-point) peak near this exact candidate
        # position. Beat/downbeat confidence is deliberately NEVER used
        # here anymore (it only supplied the bar_period/phase novelty
        # detection needs to know where bars fall -- not the evidence
        # itself). No qualifying peak -> honestly LOW, never fabricated.
        exit_frame_for_novelty = int(round(exit_t_ms / 1000.0 * FRAME_RATE))
        peak = find_nearest_novelty_peak(novelty_result, exit_frame_for_novelty, FRAME_RATE, min_prominence_z=1.0)
        if peak is not None:
            exit_novelty_z, _distance_bars = peak
            exit_novelty_peak_detected = True
            exit_structure_confidence = "HIGH" if exit_novelty_z >= 2.0 else "MEDIUM"
        else:
            exit_novelty_z = None
            exit_novelty_peak_detected = False
            exit_structure_confidence = "LOW"

    exit_vocal_risk = _vocal_risk_bucket(exit_vocal_density)
    exit_win = min(n_frames, int(round(FRAME_RATE * 6.0)))
    exit_f0 = max(0, min(n_frames - exit_win, int(exit_t_ms / 1000.0 * FRAME_RATE))) if exit_win > 0 else 0
    exit_bass_energy_db = float(np.mean(bass_energy_curve[exit_f0:exit_f0 + exit_win])) if exit_win > 0 else float(np.mean(bass_energy_curve))
    exit_bass_activity = _bass_bucket(exit_bass_energy_db)
    exit_bass_onset_density = onset_density_per_s(low_onset_env, FRAME_RATE, exit_f0, exit_f0 + exit_win)
    exit_spectral_centroid_hz = float(np.mean(centroid_curve[exit_f0:exit_f0 + exit_win])) if exit_win > 0 else float(np.mean(centroid_curve))
    exit_spectral_flatness = float(np.mean(flatness_curve[exit_f0:exit_f0 + exit_win])) if exit_win > 0 else float(np.mean(flatness_curve))
    exit_onset_density = onset_density_per_s(onset_env, FRAME_RATE, exit_f0, exit_f0 + exit_win)

    if lead is not None:
        lead_start_frame, lead_end_frame = lead
        entry_t_ms = lead_end_frame / FRAME_RATE * 1000.0
        entry_has_intro = True
        entry_is_silence_skip = False
        entry_vocal_density = float(np.mean(vocal_density[lead_start_frame:lead_end_frame]))
    elif has_leading_silence:
        entry_t_ms = lead_silence_end_ms
        entry_has_intro = False
        entry_is_silence_skip = True
        win = min(n_frames - lead_silence_end_frame, int(round(FRAME_RATE * 4.0)))
        entry_vocal_density = float(np.mean(vocal_density[lead_silence_end_frame:lead_silence_end_frame + win])) if win > 0 else median_vd
    else:
        entry_t_ms = 0.0
        entry_has_intro = False
        entry_is_silence_skip = False
        win = min(n_frames, int(round(FRAME_RATE * 4.0)))
        entry_vocal_density = float(np.mean(vocal_density[:win])) if win > 0 else median_vd

    entry_vocal_risk = _vocal_risk_bucket(entry_vocal_density)
    entry_start_frame_for_energy = int(round(entry_t_ms / 1000.0 * FRAME_RATE))
    entry_energy_win = min(n_frames - entry_start_frame_for_energy, int(round(FRAME_RATE * 4.0)))
    entry_region_rms_db = (
        float(np.mean(rms_db[entry_start_frame_for_energy:entry_start_frame_for_energy + entry_energy_win]))
        if entry_energy_win > 0 else None
    )

    # PM STAGE B REVIEW R3 repair: MEASURED (not hardcoded) bass/percussion
    # activity and timbral/rhythmic texture at the incoming entry region --
    # same methodology as the exit-side measurements above.
    entry_win = entry_energy_win
    entry_bass_energy_db = (
        float(np.mean(bass_energy_curve[entry_start_frame_for_energy:entry_start_frame_for_energy + entry_win]))
        if entry_win > 0 else float(np.mean(bass_energy_curve))
    )
    entry_bass_activity = _bass_bucket(entry_bass_energy_db)
    entry_bass_onset_density = onset_density_per_s(low_onset_env, FRAME_RATE, entry_start_frame_for_energy, entry_start_frame_for_energy + entry_win)
    entry_spectral_centroid_hz = (
        float(np.mean(centroid_curve[entry_start_frame_for_energy:entry_start_frame_for_energy + entry_win]))
        if entry_win > 0 else float(np.mean(centroid_curve))
    )
    entry_spectral_flatness = (
        float(np.mean(flatness_curve[entry_start_frame_for_energy:entry_start_frame_for_energy + entry_win]))
        if entry_win > 0 else float(np.mean(flatness_curve))
    )
    entry_onset_density = onset_density_per_s(onset_env, FRAME_RATE, entry_start_frame_for_energy, entry_start_frame_for_energy + entry_win)

    track_median_energy_db = float(np.median(rms_db))
    energy_continuity_hint = "STRONG" if abs(exit_energy_db - track_median_energy_db) <= 4.0 else "MODERATE"

    # PM STAGE B REVIEW R5 repair: PRE-RENDER source-level loudness/energy
    # diagnostics -- a stable "reference" window well before the exit
    # point (mirrors dsp/loudness_diagnostics.py's own
    # pre_transition_reference_db methodology, but computed here on SOURCE
    # audio before any rendering/pairing decision) and the short-term
    # trend (rising/falling) going into the boundary.
    ref_lookback_frames = int(round(3.0 * FRAME_RATE))
    ref_window_frames = int(round(2.0 * FRAME_RATE))
    ref_end = max(0, exit_f0 - ref_lookback_frames)
    ref_start = max(0, ref_end - ref_window_frames)
    exit_reference_rms_db = float(np.mean(rms_db[ref_start:ref_end])) if ref_end > ref_start else exit_energy_db
    exit_trend_db = exit_energy_db - exit_reference_rms_db  # negative = fading into the exit (real, not a defect)

    genre_tags, genre_provenance = extract_local_genre_tags(path)

    # BOUNDARY-LOCALIZED key estimates: harmonic compatibility for a DJ
    # transition depends on what is actually playing AT the exit/entry
    # point, not necessarily the song's single nominal/whole-track key
    # (which can differ from a specific section when a track modulates or
    # has harmonically distinct sections) -- computed over the ~30s window
    # immediately around each candidate boundary.
    win_frames = int(round(30.0 * FRAME_RATE))
    exit_frame = int(round(exit_t_ms / 1000.0 * FRAME_RATE))
    exit_win_start = max(0, exit_frame - win_frames)
    exit_win_end = min(n_frames, exit_frame + int(round(5.0 * FRAME_RATE)))
    key_at_exit = estimate_key(chroma_vector(mag[exit_win_start:exit_win_end], freqs)) if exit_win_end > exit_win_start else key

    entry_frame = int(round(entry_t_ms / 1000.0 * FRAME_RATE))
    entry_win_end = min(n_frames, entry_frame + win_frames)
    key_at_entry = estimate_key(chroma_vector(mag[entry_frame:entry_win_end], freqs)) if entry_win_end > entry_frame else key

    return {
        "duration_ms": round(duration_ms, 1),
        "sample_rate_analysis_hz": ANALYSIS_SR,
        "tempo": tempo,
        "beat": {"phase_frame": beat_phase, "confidence": beat_conf, "margin": beat_margin},
        "downbeat": {"phase_of_4": downbeat_phase, "confidence": downbeat_conf, "margin": downbeat_margin},
        "key": key,
        "key_at_exit": key_at_exit,
        "key_at_entry": key_at_entry,
        "loudness": {
            "track_median_rms_db": round(track_median_energy_db, 2),
            "exit_region_rms_db": round(exit_energy_db, 2),
            "entry_region_rms_db": round(entry_region_rms_db, 2) if entry_region_rms_db is not None else None,
            "exit_reference_rms_db": round(exit_reference_rms_db, 2),
            "exit_trend_db": round(exit_trend_db, 2),
        },
        "vocal_density_proxy": {
            "track_median": round(median_vd, 4),
            "exit_region": round(exit_vocal_density, 4),
            "entry_region": round(entry_vocal_density, 4),
            "method": "HEURISTIC_PROXY: 300-3400Hz band-energy-ratio * tonal-salience(1-spectral_flatness), no source separation available",
        },
        "bass_percussion": {
            "exit_bass_energy_db": round(exit_bass_energy_db, 2),
            "exit_bass_activity": exit_bass_activity,
            "exit_bass_onset_density_per_s": round(exit_bass_onset_density, 3),
            "entry_bass_energy_db": round(entry_bass_energy_db, 2),
            "entry_bass_activity": entry_bass_activity,
            "entry_bass_onset_density_per_s": round(entry_bass_onset_density, 3),
            "method": "MEASURED: 30-150Hz band RMS-dBFS percentile-bucketed per-track, plus low-band onset-peak density -- never a hardcoded constant",
        },
        "texture": {
            "exit_spectral_centroid_hz": round(exit_spectral_centroid_hz, 1),
            "exit_spectral_flatness": round(exit_spectral_flatness, 4),
            "exit_onset_density_per_s": round(exit_onset_density, 3),
            "entry_spectral_centroid_hz": round(entry_spectral_centroid_hz, 1),
            "entry_spectral_flatness": round(entry_spectral_flatness, 4),
            "entry_onset_density_per_s": round(entry_onset_density, 3),
            "method": "MEASURED: broadband (30-8000Hz) spectral centroid + spectral flatness + onset-peak density at each boundary region",
        },
        "candidates": {
            "exit_candidate_t_ms": round(exit_t_ms, 1),
            "exit_is_outro_tail_opportunity": is_outro_tail_opportunity,
            "exit_novelty_peak_detected": exit_novelty_peak_detected,
            "exit_novelty_peak_z": round(exit_novelty_z, 3) if exit_novelty_z is not None else None,
            "exit_structure_confidence": exit_structure_confidence,
            "exit_structure_evidence_method": (
                "INSTRUMENTAL_TAIL_DETECTED" if is_outro_tail_opportunity else
                ("BAR_SYNCHRONOUS_NOVELTY_PEAK" if exit_novelty_peak_detected else
                 "NO_INDEPENDENT_STRUCTURE_EVIDENCE_FOUND")
            ),
            "exit_vocal_collision_risk": exit_vocal_risk,
            "entry_candidate_t_ms": round(entry_t_ms, 1),
            "entry_has_detected_intro": entry_has_intro,
            "entry_is_authored_silence_skip": entry_is_silence_skip,
            "entry_vocal_collision_risk": entry_vocal_risk,
        },
        "energy_continuity_hint": energy_continuity_hint,
        "genre_tags": genre_tags,
        "genre_tag_provenance": genre_provenance,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-root", required=True)
    ap.add_argument("--out-dir", required=True, help="LOCAL-ONLY output dir (gitignored)")
    ap.add_argument("--summary-out", required=True, help="Sanitized aggregate-only summary path (safe to commit)")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if not FFMPEG_BIN:
        print("RESULT: BLOCKED")
        print("RESULT_REASON_CODE: ENVIRONMENT_BLOCKED (ffmpeg not found)")
        sys.exit(0)

    input_root = Path(args.input_root).resolve()
    if not input_root.is_dir():
        print("RESULT: OWNER_REAL_MUSIC_INPUT_REQUIRED")
        print("Input root does not exist or is not a directory.")
        sys.exit(0)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        (p for p in input_root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS and input_root in p.resolve().parents),
        key=lambda p: p.name.lower(),
    )
    if args.limit:
        files = files[: args.limit]

    id_map = {}
    analyses = {}
    failures = []
    t_start = time.perf_counter()
    for i, path in enumerate(files, start=1):
        opaque_id = f"RM{i:03d}"
        id_map[opaque_id] = str(path.resolve())
        try:
            analyses[opaque_id] = analyze_one(path)
            print(f"{opaque_id}: OK")
        except Exception as e:  # noqa: BLE001
            failures.append({"opaque_id": opaque_id, "error_type": type(e).__name__})
            print(f"{opaque_id}: FAILED ({type(e).__name__})")

    (out_dir / "id_map.local.json").write_text(json.dumps(id_map, indent=2), encoding="utf-8")
    (out_dir / "corpus_analysis.local.json").write_text(json.dumps(analyses, indent=2), encoding="utf-8")

    tempos = [a["tempo"]["bpm"] for a in analyses.values() if a["tempo"]["confidence"] != "NONE"]
    beat_conf_counts, downbeat_conf_counts, key_conf_counts = {}, {}, {}
    structure_evidence_counts, genre_known_count = {}, 0
    for a in analyses.values():
        beat_conf_counts[a["beat"]["confidence"]] = beat_conf_counts.get(a["beat"]["confidence"], 0) + 1
        downbeat_conf_counts[a["downbeat"]["confidence"]] = downbeat_conf_counts.get(a["downbeat"]["confidence"], 0) + 1
        key_conf_counts[a["key"]["confidence"]] = key_conf_counts.get(a["key"]["confidence"], 0) + 1
        method = a["candidates"]["exit_structure_evidence_method"]
        structure_evidence_counts[method] = structure_evidence_counts.get(method, 0) + 1
        if a["genre_tags"]:
            genre_known_count += 1

    summary = {
        "result": "ANALYSIS_COMPLETE" if analyses else "OWNER_REAL_MUSIC_INPUT_REQUIRED",
        "corpus_track_count_total": len(files),
        "corpus_track_count_analyzed": len(analyses),
        "corpus_track_count_failed": len(failures),
        "failed_error_types": sorted({f["error_type"] for f in failures}),
        "tempo_bpm_histogram": {
            "min": round(min(tempos), 1) if tempos else None,
            "max": round(max(tempos), 1) if tempos else None,
            "median": round(float(np.median(tempos)), 1) if tempos else None,
            "count_with_usable_confidence": len(tempos),
        },
        "beat_confidence_distribution": beat_conf_counts,
        "downbeat_confidence_distribution": downbeat_conf_counts,
        "key_confidence_distribution": key_conf_counts,
        "exit_structure_evidence_method_distribution": structure_evidence_counts,
        "tracks_with_known_genre_evidence": genre_known_count,
        "tracks_with_unknown_genre": len(analyses) - genre_known_count,
        "analysis_wall_time_s": round(time.perf_counter() - t_start, 1),
        "note": "Aggregate/statistical only -- no filenames, paths, IDs-to-paths mapping, raw embedded tag text, or per-track identity in this file by construction.",
    }
    Path(args.summary_out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nANALYZED={len(analyses)} FAILED={len(failures)} TOTAL={len(files)}")
    print(f"RESULT: {summary['result']}")


if __name__ == "__main__":
    main()
