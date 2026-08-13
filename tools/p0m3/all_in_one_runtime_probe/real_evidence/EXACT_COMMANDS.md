# P0-M3-R3 All-In-One real evidence — exact commands

Commands were run from repository root on branch
`research/p0-feasibility`. Full upstream stdout/stderr was redirected to
gitignored private logs so source names could not enter tracked evidence.

## Frontier before private audio

```powershell
python tools\p0m3\all_in_one_runtime_probe\real_evidence\derive_frontier.py `
  --accepted-evidence tools\p0m3\audio_render_shootout\results\analyzer_evidence_recovery_sanitized.json `
  --out tools\p0m3\all_in_one_runtime_probe\real_evidence\results\frontier_derivation_sanitized.json
```

## Isolated FFmpeg dependency

The exact release asset was downloaded outside the repository:

```powershell
gh release download autobuild-2026-08-12-13-15 `
  --repo BtbN/FFmpeg-Builds `
  --pattern ffmpeg-N-126086-ge5ecfe8970-linux64-gpl.tar.xz `
  --dir E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\ffmpeg-pinned
Get-FileHash -Algorithm SHA256 `
  E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\ffmpeg-pinned\ffmpeg-N-126086-ge5ecfe8970-linux64-gpl.tar.xz
```

Observed SHA-256:
`cf55934e9faa1969bff4c3fc1e1352707c9c9384e4d7986388830a8c8a726913`.
The archive was extracted beneath the existing isolated runtime root only.

## Accepted RM014 smoke

The WSL invocation used these exact non-private paths and pins:

```bash
repo=/mnt/e/AIProjects/AutoMix
runtime=/home/pnhd/automix-p0m3r3-runtime-probe-20260813
export AUTOMIX_DETERMINISTIC_SEED=0
export PYTHONPATH=$repo/tools/p0m3/all_in_one_runtime_probe/real_evidence/deterministic_site
export AUTOMIX_FFMPEG_RELEASE_TAG=autobuild-2026-08-12-13-15
export AUTOMIX_FFMPEG_ARCHIVE_SHA256=cf55934e9faa1969bff4c3fc1e1352707c9c9384e4d7986388830a8c8a726913
export PATH=$runtime/ffmpeg-pinned/ffmpeg-N-126086-ge5ecfe8970-linux64-gpl/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=$runtime/p1-legacy/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib:${LD_LIBRARY_PATH:-}
$runtime/p1-legacy/bin/python $repo/tools/p0m3/all_in_one_runtime_probe/real_evidence/run_real_pipeline.py \
  --mapping $repo/tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json \
  --frontier $repo/tools/p0m3/all_in_one_runtime_probe/real_evidence/results/frontier_derivation_sanitized.json \
  --track-ids RM014 --repeats 2 --start-order 1 \
  --scratch $repo/tools/p0m3/audio_render_shootout/real_music/work_local/all_in_one_real_evidence_seeded \
  --out $repo/tools/p0m3/all_in_one_runtime_probe/real_evidence/results/rm014_smoke_sanitized.json
```

## Bounded expansion

```bash
$runtime/p1-legacy/bin/python $repo/tools/p0m3/all_in_one_runtime_probe/real_evidence/run_real_pipeline.py \
  --mapping $repo/tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json \
  --frontier $repo/tools/p0m3/all_in_one_runtime_probe/real_evidence/results/frontier_derivation_sanitized.json \
  --track-ids RM010 RM041 RM081 --repeats 1 --start-order 3 \
  --prior-smoke $repo/tools/p0m3/all_in_one_runtime_probe/real_evidence/results/rm014_smoke_sanitized.json \
  --scratch $repo/tools/p0m3/audio_render_shootout/real_music/work_local/all_in_one_real_evidence_expanded \
  --out $repo/tools/p0m3/all_in_one_runtime_probe/real_evidence/results/expanded_runs_sanitized.json
```

## Compile and verify

```powershell
python tools\p0m3\all_in_one_runtime_probe\real_evidence\compile_evidence.py `
  --frontier tools\p0m3\all_in_one_runtime_probe\real_evidence\results\frontier_derivation_sanitized.json `
  --smoke tools\p0m3\all_in_one_runtime_probe\real_evidence\results\rm014_smoke_sanitized.json `
  --expanded tools\p0m3\all_in_one_runtime_probe\real_evidence\results\expanded_runs_sanitized.json `
  --accepted-evidence tools\p0m3\audio_render_shootout\results\analyzer_evidence_recovery_sanitized.json `
  --evidence-out tools\p0m3\all_in_one_runtime_probe\real_evidence\results\all_in_one_real_evidence_sanitized.json `
  --replay-out tools\p0m3\all_in_one_runtime_probe\real_evidence\results\three_pair_replay_sanitized.json

python tools\p0m3\all_in_one_runtime_probe\real_evidence\verify_real_evidence.py `
  --frontier tools\p0m3\all_in_one_runtime_probe\real_evidence\results\frontier_derivation_sanitized.json `
  --evidence tools\p0m3\all_in_one_runtime_probe\real_evidence\results\all_in_one_real_evidence_sanitized.json `
  --replay tools\p0m3\all_in_one_runtime_probe\real_evidence\results\three_pair_replay_sanitized.json `
  --mapping tools\p0m3\audio_render_shootout\real_music\work_local\corpus\id_map.local.json `
  --scan-root tools\p0m3\all_in_one_runtime_probe\real_evidence `
  --report docs\research\P0-M3-R3-ALL-IN-ONE-REAL-EVIDENCE.md `
  --out tools\p0m3\all_in_one_runtime_probe\real_evidence\results\validation_precommit.json
```

No render, Signalsmith, Rubber Band, owner-pack, whole-subset or whole-corpus
command was run.
