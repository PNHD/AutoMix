# P0-M3-R3 RM014 incoming-entry anchor feasibility — exact commands

All inputs are already-accepted, already-committed evidence from prior
passes (10 raw `allin1.analyze` run files, the accepted madmom benchmark
grid, the accepted RM041 exit harmonic-sensitivity cells). No All-In-One
rerun, no RM041 audio decode. RM014 audio is decoded only for the
content-preservation and harmonic-re-evaluation steps, via the same WSL
`allinone_venv` (librosa 0.11.0, madmom 0.17.dev0 — madmom is not actually
invoked by this pass, only librosa) already accepted for Issue #7. The
private opaque-id -> local-path mapping is read but never printed.

## Step 1 — derive intro downbeat clusters (pure Python, no audio decode)

```bash
python tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/derive_intro_clusters.py \
  --raw-dir tools/p0m3/all_in_one_runtime_probe/pair_stability/results/raw_runs \
  --accepted-analyzer-evidence tools/p0m3/audio_render_shootout/results/analyzer_evidence_recovery_sanitized.json \
  --current-entry-ms 0.0 \
  --out tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/intro_clusters.json
```

## Step 2 — skipped-content preservation diagnostics (RM014 audio, WSL)

```bash
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/e/AIProjects/AutoMix && /home/pnhd/allinone_venv/bin/python tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/content_preservation_analysis.py \
  --mapping tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json \
  --intro-clusters tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/intro_clusters.json \
  --current-entry-ms 0.0 \
  --out tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/content_preservation.json"
```

## Step 3 — harmonic re-evaluation for the top-2 candidates (RM014 audio, WSL)

```bash
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/e/AIProjects/AutoMix && /home/pnhd/allinone_venv/bin/python tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/harmonic_reeval_candidates.py \
  --mapping tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json \
  --intro-clusters tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/intro_clusters.json \
  --accepted-harmonic-sensitivity tools/p0m3/all_in_one_runtime_probe/pair_stability/results/harmonic_sensitivity.json \
  --out tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/harmonic_reeval.json"
```

## Verification

```bash
python tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/verify_entry_anchor_feasibility.py
```

```bash
# canonical files unchanged (compared against the accepted starting HEAD)
git diff --stat b181f4274d6f675deba17f3e78b7021e968768db -- tools/p0m3/transition_policy/policy/compatibility.py
git diff --stat b181f4274d6f675deba17f3e78b7021e968768db -- tools/p0m3/transition_policy/policy/contract.py
git diff --stat b181f4274d6f675deba17f3e78b7021e968768db -- tools/p0m3/transition_policy/policy/boundary.py
git diff --stat b181f4274d6f675deba17f3e78b7021e968768db -- tools/p0m3/audio_render_shootout/scripts/select_real_music_pairs.py
git diff --stat b181f4274d6f675deba17f3e78b7021e968768db -- tools/p0m3/all_in_one_runtime_probe/pair_stability/
git branch --show-current
git rev-parse main
```

No render, Signalsmith, Rubber Band, owner-listening pack, RM041 audio
decode, or All-In-One (allin1.analyze) invocation was run this pass.
