# P0-M3-R3 — All-In-One runtime compatibility probe

Status date: 2026-08-13

Binding task: Issue #7 comment `5277857804`

Starting branch/HEAD: `research/p0-feasibility` at
`2d68c86ec3e47e53a92448bf16bf8f6255cbf8a3`

## Result

`ALL_IN_ONE_RUNTIME_RECOVERED_SYNTHETIC_ONLY`

This is runtime compatibility evidence, not an analyzer-quality PASS and not a
render authorization. The accepted prior result remains
`ANALYZER_EVIDENCE_INSUFFICIENT_AND_MEASURED_INCOMPATIBILITY`.

## Canonical exact-legacy path

The canonical source was tested unmodified at
`mir-aidj/all-in-one@18e78903c0365147a2c5d4e5e57ebf88cb7d800e`.
Official NATTEN v0.14.6 metadata establishes a plausible Linux matrix:

- NATTEN source tag `v0.14.6` resolves to commit
  `3b54c76185904f3cb59a49fff7bc044e4513d106`;
- its `requirements.txt` pins PyTorch `2.0.0` and CUDA 11.8 wheels;
- its `setup.py` allows Python `>=3.7`, and its README explicitly supports
  Python 3.10 with PyTorch >=1.11;
- its source `src/natten/functional.py` exposes exact legacy
  `natten1dqkrpb(query,key,rpb,kernel_size,dilation)` and
  `natten1dav(attn,value,kernel_size,dilation)` functions, plus 2D equivalents;
- the official v0.14.6 release publishes the CPython 3.10 / Torch 2.0.0 /
  CUDA 11.8 wheel with SHA-256 `afb05fc4...f299efa`.

The isolated runtime used Python `3.10.18`, PyTorch `2.0.0+cu118`, CUDA build
`11.8`, and NATTEN `0.14.6+torch200cu118`. The current NVIDIA driver exposed
an RTX 2060 to WSL2.

Observed ladder:

1. dependencies/environment: PASS;
2. canonical top-level import unmodified: PASS;
3. actual `AllInOne` construction on GPU: PASS (`300631` parameters);
4. normal loader downloaded `harmonix-fold0-0vra4ys2.pth` from
   `taejunkim/allinone` revision
   `379e5fd010b3fdd0ee8381ff8cbcfa51d70b5c19`;
5. strict state-dict load: PASS, zero missing keys, zero unexpected keys, zero
   shape mismatches, identical key sets;
6. checkpoint SHA-256:
   `0db596dfb0995f41d62f6267d76a9d54c046f1649bd35e1dbeca0c5f9a7b8acd`;
7. deterministic non-audio tensor inference: PASS twice, bit-exact repeat,
   no NaN/Inf.

The first forward exposed a missing unversioned `libnvrtc.so`. The exact CUDA
11.8 NVRTC runtime package was added inside this isolated environment only;
an environment-local symlink and `LD_LIBRARY_PATH` resolved the loader. This
did not modify system packages, the existing WSL Python, or third-party source.

## PR #37 exact claimed matrix

PR #37 is closed and unmerged. Its head is
`5c2b2ce571c04054a0b54ceba365c0b8c1188099`, and its body claims PyTorch
`2.7.0`, CUDA `12.8`, and NATTEN `0.21.0+torch270cu128`.

That exact matrix was installed in a separate Python 3.11.13 environment. The
official NATTEN wheel was available and its published SHA-256
`b3d94665...1cd6bcc` verified. Direct symbol inspection found:

| Symbol | Present |
|---|---:|
| `na1d_qk` | no |
| `na1d_av` | no |
| `na2d_qk` | no |
| `na2d_av` | no |
| combined `na1d` | yes |
| combined `na2d` | yes |
| `neighborhood_attention_generic` | yes |

The unmodified PR source consequently failed top-level import with
`ImportError: cannot import name 'na1d_qk' from 'natten.functional'`.
Model construction and checkpoint load were not reached. Therefore the PR's
runtime claim is **falsified** for its exact published package matrix.

## Optional v0.15.1 path

Not attempted. The canonical exact-legacy path already recovered strict model
load and deterministic synthetic inference. No adapter was needed, and no
modern attention algorithm or combined API was used as a replacement.

## Synthetic and bounded real smoke

The synthetic input was a deterministic non-audio tensor shaped
`[1,4,128,81]`. Output shapes were:

- beats/downbeats/sections: `[1,128]` each;
- functional labels: `[1,10,128]`;
- embeddings: `[1,4,128,24]`.

Two repeats took `0.796400 s` (first/JIT) and `0.024658 s`; the maximum absolute
repeat difference was exactly `0.0`. Private smoke count is `0`. No owner track
was needed to answer the runtime-compatibility question.

## License boundary

Unchanged:

- All-In-One code: MIT;
- checkpoint repository: self-declared MIT metadata;
- benchmark: `CLEAR_FOR_BENCHMARK`;
- production evaluation: `UNKNOWN_NEEDS_LEGAL_REVIEW` because training-audio
  provenance and rights remain unresolved.

Technical runtime recovery does not alter that legal conclusion.

## Scope and privacy

- no owner audio read or analyzed;
- no owner transition rendered and no listening pack created;
- no Signalsmith or Rubber Band run;
- no 19-track or 100-track analysis;
- no filenames, paths, titles, artists, hashes, tags, mappings, weights,
  wheels, environments, or package caches committed;
- no P1 work and no `main` merge;
- no modern attention rewrite.

Machine evidence is in
`tools/p0m3/all_in_one_runtime_probe/results/runtime_probe_sanitized.json`.
Exact commands and intervening failures are retained in `EXACT_COMMANDS.md`.
