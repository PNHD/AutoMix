# P0-M3-R3 RM014 incoming-entry anchor feasibility — exact commands

All inputs are already-accepted, already-committed evidence from prior
passes (10 raw `allin1.analyze` run files, the accepted madmom benchmark
grid, the accepted RM041 exit harmonic-sensitivity cells). No All-In-One
rerun, no RM041 audio decode. RM014 audio is decoded only for the
content-preservation and harmonic-re-evaluation steps, via the same
harmonic/structure oracle venv (librosa 0.11.0, madmom 0.17.dev0 — madmom
is not actually invoked by this pass, only librosa) already accepted for
Issue #7. The private opaque-id -> local-path mapping is read but never
printed.

## Operator-supplied variables (out of band, never committed)

These commands are environment-generic. Two values are supplied locally by
the operator, out of band, and are never written to any tracked file or
committed anywhere in this repository:

- `AUTOMIX_REPO_ROOT` — absolute path to this repository checkout, as seen
  from inside the WSL distribution used to run the harmonic/structure
  oracle venv (typically a `/mnt/<drive>/...` path when the checkout lives
  on a Windows-mounted drive). The actual drive letter and directory layout
  are local-machine-specific and are intentionally not recorded here.
- `AUTOMIX_ALLINONE_PY` — absolute path to the Python interpreter inside
  the already-accepted harmonic/structure oracle virtualenv (the same
  environment already accepted for Issue #7). Its exact filesystem
  location, including any local username that may appear in the path, is
  intentionally not recorded here.

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
wsl.exe -d Ubuntu -- bash -lc "cd \"$AUTOMIX_REPO_ROOT\" && \"$AUTOMIX_ALLINONE_PY\" tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/content_preservation_analysis.py \
  --mapping tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json \
  --intro-clusters tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/intro_clusters.json \
  --current-entry-ms 0.0 \
  --out tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/content_preservation.json"
```

## Step 3 — harmonic re-evaluation for the top-2 candidates (RM014 audio, WSL)

```bash
wsl.exe -d Ubuntu -- bash -lc "cd \"$AUTOMIX_REPO_ROOT\" && \"$AUTOMIX_ALLINONE_PY\" tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/harmonic_reeval_candidates.py \
  --mapping tools/p0m3/audio_render_shootout/real_music/work_local/corpus/id_map.local.json \
  --intro-clusters tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/intro_clusters.json \
  --accepted-harmonic-sensitivity tools/p0m3/all_in_one_runtime_probe/pair_stability/results/harmonic_sensitivity.json \
  --out tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/results/harmonic_reeval.json"
```

## Verification

```bash
python tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/verify_entry_anchor_feasibility.py
```

Optional: to also assert absence of a real owner-private sentinel value
across every scanned target (never printed, never embedded in any check
label — see the verifier's module docstring), supply it out of band and
never on a command line that could persist in shell history:

```bash
AUTOMIX_PRIVATE_SENTINEL="<value, supplied out of band>" python tools/p0m3/all_in_one_runtime_probe/entry_anchor_feasibility/verify_entry_anchor_feasibility.py
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

## Environment-path privacy note

This document intentionally contains no literal Windows absolute path, no
literal WSL mount-style absolute path (`/mnt/` followed by a drive letter),
and no literal Linux home-directory absolute path (`/home/` followed by a
username) — including no exception for this repository's own checkout
location.
`verify_entry_anchor_feasibility.py` scans this file (and every other
tracked source/result/doc/handoff file in scope, plus every text-decodable
PM-review ZIP member) for those generic path shapes unconditionally; there
is no allowlisted path prefix anywhere in the verifier.
