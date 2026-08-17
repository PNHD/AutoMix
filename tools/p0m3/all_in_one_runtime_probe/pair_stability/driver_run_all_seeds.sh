#!/bin/bash
# P0-M3-R3 RM041<->RM014 evidence stability -- cross-seed driver.
#
# Runs exactly 10 real allin1.analyze invocations: RM041 x {0,1,2,3,4} then
# RM014 x {0,1,2,3,4}, each in its own Python process (so the
# AUTOMIX_DETERMINISTIC_SEED env var read once at interpreter start by
# sitecustomize.py genuinely varies per run) and its own fresh
# demix/spectrogram scratch directory (unseeded Demucs preprocessing was
# previously shown to be non-repeatable across a shared cache directory).
#
# One optional diagnostic retry of a single failed (track,seed) is allowed
# by the task; this driver stops immediately on the first failure so a
# human/agent can decide whether to invoke the retry manually instead of
# silently cherry-picking seeds.
set -euo pipefail

repo=/mnt/e/AIProjects/AutoMix
runtime=/home/pnhd/automix-p0m3r3-runtime-probe-20260813
here=$repo/tools/p0m3/all_in_one_runtime_probe/pair_stability

export PYTHONPATH=$repo/tools/p0m3/all_in_one_runtime_probe/real_evidence/deterministic_site
export AUTOMIX_FFMPEG_RELEASE_TAG=autobuild-2026-08-12-13-15
export AUTOMIX_FFMPEG_ARCHIVE_SHA256=cf55934e9faa1969bff4c3fc1e1352707c9c9384e4d7986388830a8c8a726913
export PATH=$runtime/ffmpeg-pinned/ffmpeg-N-126086-ge5ecfe8970-linux64-gpl/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=$runtime/p1-legacy/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib:${LD_LIBRARY_PATH:-}

mapping=$repo/tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json
scratch=$repo/tools/p0m3/audio_render_shootout/real_music/work_local/pair_stability_cross_seed
out_dir=$here/results/raw_runs
log_dir=$scratch/logs
mkdir -p "$out_dir" "$log_dir"

# Full upstream stdout/stderr (which can print the private source filename
# via tqdm progress-bar labels) is redirected to a LOCAL, GITIGNORED log
# file per run -- never printed to the calling terminal/transcript. Only
# the sanitized status line below is echoed.
order=1
for track in RM041 RM014; do
  for seed in 0 1 2 3 4; do
    out="$out_dir/${track}-seed${seed}.json"
    log="$log_dir/${track}-seed${seed}.log"
    AUTOMIX_DETERMINISTIC_SEED=$seed "$runtime/p1-legacy/bin/python" \
      "$here/run_cross_seed_stability.py" \
      --mapping "$mapping" \
      --track-id "$track" \
      --seed "$seed" \
      --execution-order "$order" \
      --scratch "$scratch" \
      --out "$out" \
      >"$log" 2>&1
    status=$?
    result=$(python3 -c "import json; print(json.load(open('$out'))['run']['execution_result'])" 2>/dev/null || echo "UNKNOWN")
    echo "run ${order}/10: ${track} seed=${seed} -> ${result} (exit ${status})"
    order=$((order + 1))
    if [ "$result" != "PASS" ]; then
      echo "STOPPING: non-PASS result, see local log ${log}"
      exit 1
    fi
  done
done

echo "ALL_10_RUNS_COMPLETE"
