# P0-M3-R3 -- DSP Candidate Provenance / License / Environment Audit

Status date: 2026-08-12

Retrieval method for all remote facts below: `git ls-remote`, GitHub raw-content
fetch (`curl`), and local environment probing (`where`/`find`/`ffmpeg -h`) run
directly in this task's session. Exact commands are reproduced in each
section so the PM can re-run them.

## 1. Signalsmith Stretch -- production candidate (`HIGH_PRIORITY_PRODUCTION_CANDIDATE`)

- Repo: `Signalsmith-Audio/signalsmith-stretch`
- Pinned commit (per Issue #7): `57b93f4e9206a089a45387eaa39bdc9f310d3308`
- Verification: `git ls-remote https://github.com/Signalsmith-Audio/signalsmith-stretch.git` returns
  `57b93f4e9206a089a45387eaa39bdc9f310d3308  refs/heads/main` -- **the pin is HEAD of `main` at task creation time; confirmed, FACT.**
- License: `LICENSE.txt` at the pinned commit is the standard MIT License, copyright
  `2022 Geraint Luff / Signalsmith Audio Ltd.` (fetched verbatim, reproduced locally at
  `tools/p0m3/audio_render_shootout/vendor/signalsmith-stretch/LICENSE.txt`, gitignored/local
  only, re-fetchable from the URL above). No additional bundled third-party
  license notices were found in `LICENSE.txt`, `README.md`, or `.gitmodules` at
  this commit. **FACT.**
- Repo tree at the pinned commit (`GET /repos/.../git/trees/<sha>?recursive=1`):
  single-header C++ library (`signalsmith-stretch.h`), a `cmd/` CLI demo,
  and a `web/` directory containing an **official prebuilt web release**
  (`web/release/SignalsmithStretch.mjs`, `.js`, `package.json`, `README.md`),
  version `1.3.2` per `package.json`. **FACT.**

### 1.1 Native C++ path -- environment blocker (documented, not silently bypassed)

Per Issue #7: "Prefer native C++ on Windows if the existing environment
supports it... Official upstream WASM/WebAudio may be used only as an
EXPLICIT, documented fallback if native compilation is unavailable."

Probed in this session:

| Toolchain | Command | Result |
|---|---|---|
| GCC/G++ (MSYS2/mingw64, on `PATH`) | `where g++` / `which g++` | not found |
| MSVC `cl.exe` | `where cl` | not found |
| CMake | `where cmake` | not found |
| clang / clang-cl | `where clang++` / `where clang-cl` | not found |
| Visual Studio installs (`vswhere -all`) | `vswhere.exe -all -property installationPath/displayName` | `Visual Studio Professional 2026` present at `C:\Program Files\Microsoft Visual Studio\18\Professional`, but... |
| ...its C++ build tools | `find ".../18/Professional/VC/Tools/MSVC" -maxdepth 1` | **directory does not exist** -- the "Desktop development with C++" workload was never installed for this VS instance (only `VC/Auxiliary`, `VC/Redist` are present, no compiler toolset) |
| Emscripten (`emcc`) | `where emcc` | not found |

**Conclusion: `NATIVE_COMPILATION_UNAVAILABLE_ENVIRONMENT`** -- no C/C++ compiler
of any kind (MSVC, MinGW GCC, clang) is present on `PATH`, and the one
installed Visual Studio instance has the IDE but not the C++ compiler
toolset. Per AGENTS.md / Issue #7, installing the "Desktop development with
C++" workload (a multi-GB admin-elevated Visual Studio Installer operation)
was **not** performed, because doing so purely to unlock a reference/candidate
build is exactly the kind of system-wide/admin toolchain install the task
instructs against for the Rubber Band probe, and this project applies the
same discipline symmetrically to Signalsmith's native path rather than
installing an admin toolchain silently. This blocker, not a preference, is
why this pass uses the documented fallback below.

### 1.2 Official WASM/WebAudio fallback -- what was actually used

Per the repo tree (1. above), the pinned commit **already ships an official
prebuilt WASM/WebAudio release** at `web/release/SignalsmithStretch.mjs`
(ES module) -- this is not a from-source WASM build performed by this task
(which would also require `emcc`, also absent); it is the vendor's own
committed release artifact at the exact pinned commit.

Downloaded verbatim (local-only, gitignored, re-fetchable) to
`tools/p0m3/audio_render_shootout/vendor/signalsmith-stretch/` from
`https://raw.githubusercontent.com/Signalsmith-Audio/signalsmith-stretch/57b93f4e9206a089a45387eaa39bdc9f310d3308/...`.
SHA-256 of each fetched file (computed locally, `hashlib.sha256`):

```
ee2ef82481ffb445ecdd4b3a4c1f82c0cddb2da8fe39d8e8dc384fffb3e7f06f  LICENSE.txt
d2c43d92312154a09660bffbb06b408f3b470662f89cb4123fa5268a4ced444c  README.md
1188667959ac19dd40c0a6abbce694e44705615ec4f0e8db8af0f1cfb4c5dea7  signalsmith-stretch.h
cdb829028989a8d676482539991d89cab752b07c867d4040ebf98ed0dba00567  web/release/package.json
3d8e24bb763fbd373c5c19f62addfab5aab3b2e783ddcf45da4b67005acc0203  web/release/README.md
fe0e23b6bb5dbffb231a91e7dc39f9d2a7d10c7f793fb0237d819ca748f7f778  web/release/SignalsmithStretch.js
97530b11d5bc01015af4cde40d6aa55ff10c40aa1294ca4c8c5762027d517a46  web/release/SignalsmithStretch.mjs
4b380e40efee6c7a8ac3c9abce8911e7dcf77d659a91f771dd6db398715b5872  web/web-wrapper.js
```

Inspection of `SignalsmithStretch.mjs` (grep for `wasmBinaryFile`,
`findWasmBinary`, `audioWorklet.addModule`) confirms: it is a standard
Emscripten-generated glue module with the compiled WASM binary embedded
**inline as a base64 `data:` URI** (no separate `.wasm` fetch needed -- fully
self-contained, single file), and it registers itself as a real
`AudioWorkletProcessor` via `audioContext.audioWorklet.addModule(...)`. This
means it can only run inside an actual (Offline)AudioContext with
AudioWorklet support -- i.e. a real browser engine, not plain Node.js (Node
has no Web Audio API). This project's execution surface already includes a
Chromium-based Browser pane (`mcp__Claude_Browser`), which supports
`OfflineAudioContext` + `AudioWorkletNode` natively, so the render harness
drives the **unmodified, pinned, official** `SignalsmithStretch.mjs` inside
that real browser engine (`tools/p0m3/audio_render_shootout/web/stretch_worker.html`),
not a reimplementation. Renders are produced as real WAV bytes and written
back to local disk via a small local upload endpoint
(`tools/p0m3/audio_render_shootout/scripts/serve.py`) -- audio never leaves
localhost.

**No silent implementation-path change**: the native path was probed first,
found blocked by the documented environment gap above, and the officially
released WASM/WebAudio artifact from the same pinned commit was used
instead, exactly as Issue #7 permits.

## 2. Rubber Band Library / CLI -- quality reference only (`QUALITY_REFERENCE_ONLY`)

- Repo (official mirror per Issue #7): `breakfastquay/rubberband`
- Pinned commit: `e4296ac80b1170018a110bc326fd0d45a0eb27d6`
- Verification: `git ls-remote https://github.com/breakfastquay/rubberband.git` returns
  `e4296ac80b1170018a110bc326fd0d45a0eb27d6  refs/heads/default` -- **pin confirmed HEAD of `default`, FACT.**
- License at the pinned commit (`COPYING`): **GNU GPL v2** (fetched verbatim; Rubber Band
  is dual-licensed GPLv2+/commercial per upstream, consistent with Issue #7's stated role).

### 2.1 Probe order (per Issue #7)

| Tier | Probe | Result |
|---|---|---|
| 1 | already-installed `rubberband` / `rubberband-r3` CLI on `PATH` | `where rubberband` / `where rubberband-r3` -- **not found** |
| 2 | already-available FFmpeg Rubber Band filter | **FOUND.** The system's installed FFmpeg (`ffmpeg version 8.1.1-full_build-www.gyan.dev`, at `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe`) was built with `--enable-gpl --enable-version3 --enable-librubberband` (`ffmpeg -version` build configuration). `ffmpeg -h filter=rubberband` lists a working `rubberband` `AVOption` filter (`tempo`, `pitch`, `transients`, `detector`, `phase`, `window`, `smoothing`, `formant`, `pitchq`, `channels`). |
| 3 | non-admin local build environment | not attempted -- tier 2 already satisfied the requirement, and tier 3 would require the same missing C/C++ toolchain documented in §1.1 |

**Tier 2 is used for `M3`.** Per Issue #7 this is explicitly acceptable
("Prefer, in order: 1. already-installed CLI; 2. already-available FFmpeg
Rubber Band filter; 3. non-admin local build"). Rubber Band is invoked
**only** as an external `ffmpeg` subprocess for the M3 quality-reference
render -- no Rubber Band source or binary is linked, vendored, or copied into
`tools/p0m3/audio_render_shootout/dsp/` or any prospective shipping code
(AC3).

### 2.2 Exact linked-library version -- honestly unresolved

The `ffmpeg -h filter=rubberband` option set (`transients`/`detector`/
`phase`/`window`/`smoothing`/`formant`/`pitchq`/`channels`, i.e. the classic
`RubberBandStretcher::Option` flags) matches the historical Rubber Band
Library `Option` API. This ffmpeg build's `avfilter/af_rubberband.c` wrapper
does **not** expose an explicit R2-vs-R3/"Finer" engine selector option, and
no embedded human-readable version string for the linked `librubberband`
could be recovered from the ffmpeg binary (`strings ffmpeg.exe | grep -i
rubberband` returned no version string, only the option names already shown
above). **Therefore this task cannot assert which Rubber Band engine
generation (R2/"Faster" vs R3/"Finer") the linked library actually runs**,
and does not claim R3/Finer was used. This is recorded honestly as
`UNKNOWN_NEEDS_RUNTIME_PROOF` rather than assumed. M3's exact invocation
(recorded in `results/machine_metrics.json`) is fully reproducible regardless
of which internal engine ffmpeg's build happens to link, and M3 remains
labeled `QUALITY_REFERENCE_ONLY` per Issue #7 -- it is not a claim about
which Rubber Band engine tier is shipping-representative.

## 3. Isolation guarantee (AC3)

- `dsp/` (the shared mixing/gain/EQ/headroom engine) contains **no** import
  of, or vendored code from, `breakfastquay/rubberband` or
  `Signalsmith-Audio/signalsmith-stretch`'s C++ source.
- M2 (Signalsmith) is invoked only via the pinned, unmodified, officially
  released `web/release/SignalsmithStretch.mjs` running inside a real
  browser AudioWorklet context, driven by a thin local HTML harness
  (`web/stretch_worker.html`) that only calls the module's public
  documented JS API (`SignalsmithStretch(ctx, ...)`, `.addBuffers()`,
  `.schedule()`, `.start()`) -- no reimplementation of its DSP.
- M3 (Rubber Band) is invoked only as an external `ffmpeg -af rubberband=...`
  subprocess call -- no Rubber Band source, headers, or binaries are present
  anywhere under `tools/p0m3/audio_render_shootout/` except the license/audit
  text quoted above for provenance purposes.
- Neither candidate is referenced from, or linked into, any file outside
  `tools/p0m3/audio_render_shootout/` (AGENTS.md rule 5 / Issue #7 "Do NOT
  modify production app code").

## 4. Files

- `docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md` (this document)
- `tools/p0m3/audio_render_shootout/vendor/signalsmith-stretch/` (local-only,
  gitignored, re-fetchable via the commands in §1.2)
