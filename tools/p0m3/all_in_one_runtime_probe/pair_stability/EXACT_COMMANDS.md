# P0-M3-R3 RM041<->RM014 evidence stability — exact commands

All environments, third-party clones, wheels, caches, and model weights live
outside the repository (reused unmodified from the accepted
`P0-M3-R3-ALL-IN-ONE-REAL-EVIDENCE` pass). Commands below use sanitized
scratch/runtime roots; they never contain owner-media locations. Full
upstream `allin1.analyze` stdout/stderr (which can print the private source
filename via tqdm progress-bar labels) is redirected to a LOCAL, GITIGNORED
log file per run and is never printed to a terminal/transcript.

## Environment verification (reused, unmodified)

```bash
# WSL Ubuntu, pinned p1-legacy venv (Python 3.10.18, torch 2.0.0+cu118, NATTEN 0.14.6)
/home/pnhd/automix-p0m3r3-runtime-probe-20260813/p1-legacy/bin/python -c \
  "import sys,torch,natten; print(sys.version.split()[0], torch.__version__, torch.version.cuda, torch.cuda.is_available())"

# canonical All-In-One source pin, semantic-diff clean (ignoring EOL)
git -C /mnt/e/AIProjects/_automix-p0m3r3-runtime-probe-20260813/all-in-one-canonical rev-parse HEAD
git -C /mnt/e/AIProjects/_automix-p0m3r3-runtime-probe-20260813/all-in-one-canonical diff --ignore-space-at-eol --quiet

# harmonic/structure oracle venv (librosa 0.11.0, madmom 0.17.dev0)
/home/pnhd/allinone_venv/bin/python -c "import librosa, madmom; print(librosa.__version__, madmom.__version__)"
```

## A1 — cross-seed All-In-One inference (10 real runs)

```bash
bash tools/p0m3/all_in_one_runtime_probe/pair_stability/driver_run_all_seeds.sh
```

This runs, in order, RM041 seed=0,1,2,3,4 then RM014 seed=0,1,2,3,4 — exactly
10 real `allin1.analyze` calls, each in its own Python process (so
`AUTOMIX_DETERMINISTIC_SEED` genuinely varies per run) and its own fresh
`demix`/`spec` scratch directory. It stops immediately on any non-PASS
result (the task's one-diagnostic-retry allowance was not needed — all 10
runs PASSed on the first attempt). Per-run raw stdout/stderr is written to
`tools/p0m3/audio_render_shootout/real_music/work_local/pair_stability_cross_seed/logs/`
(gitignored, local only).

Each run internally invokes:

```python
allin1.analyze(
    source,
    model="harmonix-fold0",
    device="cuda",
    include_activations=False,
    include_embeddings=False,
    demix_dir=call_dir / "demix",
    spec_dir=call_dir / "spec",
    keep_byproducts=False,
    overwrite=True,
    multiprocess=False,
)
```

Output: `tools/p0m3/all_in_one_runtime_probe/pair_stability/results/raw_runs/{RM041,RM014}-seed{0..4}.json`.

## A2/A3 — cross-seed BPM/beat/downbeat metrics + boundary-local consensus

```bash
python tools/p0m3/all_in_one_runtime_probe/pair_stability/analyze_downbeat_consensus.py \
  --raw-dir tools/p0m3/all_in_one_runtime_probe/pair_stability/results/raw_runs \
  --accepted-analyzer-evidence tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_sanitized.json \
  --out tools/p0m3/all_in_one_runtime_probe/pair_stability/results/cross_seed_metrics.json
```

## A4 — functional structure stability

```bash
python tools/p0m3/all_in_one_runtime_probe/pair_stability/analyze_structure_consensus.py \
  --raw-dir tools/p0m3/all_in_one_runtime_probe/pair_stability/results/raw_runs \
  --out tools/p0m3/all_in_one_runtime_probe/pair_stability/results/structure_consensus.json
```

## A5/A6/A7 — harmonic window-sensitivity

```bash
/home/pnhd/allinone_venv/bin/python tools/p0m3/all_in_one_runtime_probe/pair_stability/analyze_harmonic_sensitivity.py \
  --mapping tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json \
  --out tools/p0m3/all_in_one_runtime_probe/pair_stability/results/harmonic_sensitivity.json
```

## A9 — analysis_confidence counterfactual matrix

```bash
python tools/p0m3/all_in_one_runtime_probe/pair_stability/build_counterfactual_matrix.py
```

## Verification

```bash
python tools/p0m3/all_in_one_runtime_probe/pair_stability/verify_pair_stability.py
```

```bash
# canonical files unchanged (compared against the accepted starting HEAD)
git diff --stat f0b212939979f5528a00f111b22ff92198e1c544 -- tools/p0m3/transition_policy/policy/compatibility.py
git diff --stat f0b212939979f5528a00f111b22ff92198e1c544 -- tools/p0m3/audio_render_shootout/scripts/select_real_music_pairs.py
git branch --show-current
```

No render, Signalsmith, Rubber Band, owner-pack, or whole-subset/whole-corpus
command was run.
