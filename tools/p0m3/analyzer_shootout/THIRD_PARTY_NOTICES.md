# Third-Party Notices

This disposable P0-M3-R1 research harness (`tools/p0m3/analyzer_shootout/`)
adapts one piece of third-party MIT-licensed code directly. This file
exists to satisfy that license's copyright/permission-notice preservation
requirement (PM REPAIR R3). No other file in this harness is a direct
adaptation of third-party source — every other candidate/baseline runner
in `candidates/` and `baselines/` is an independent implementation that
only *calls* third-party packages/model checkpoints through their public
APIs (see `docs/research/P0-M3-R1-ARTIFACT-LICENSE-MATRIX.md` for the
full license audit of every model/checkpoint/config artifact used, as
distinct from code).

---

## ETH-DISCO/cue-detr — covers `candidates/run_cuedetr.py`

**Upstream source:** `https://github.com/ETH-DISCO/cue-detr`, file
`cue_points.py`, pinned revision `d0462856ed2f59a1fb65267cfbe87340a65ad1bb`.

**What was adapted:** `candidates/run_cuedetr.py`'s `run()` function is a
direct, minimally-restructured port of upstream `cue_points.py`'s
inference pipeline (mel-spectrogram construction, sliding-window image
tiling, DETR preprocessing/inference/post-processing, and score-based peak
picking). The only changes are: (a) processing one file at a time and
returning this harness's normalized `AnalyzerResult` instead of writing a
`_cue_points.txt` file, (b) module-level model caching for honest
cold/warm lifecycle reporting (PM REPAIR R1), and (c) passing
`use_pretrained_backbone=False` to skip an unnecessary transitive
download, proven bit-identical to upstream's default (PM REPAIR R4, see
that file's module docstring for the verification). None of these changes
alter the algorithmic behavior of the ported pipeline.

**Exact upstream license text** (`LICENSE` file at the pinned revision,
reproduced verbatim per MIT's own requirement to include the copyright
and permission notice in copies/substantial portions of the Software):

```
MIT License

Copyright (c) 2024 ETH DISCO

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

This adaptation is not represented as wholly original AutoMix code
anywhere in this repository; `candidates/run_cuedetr.py`'s own module
docstring points back to this notice.
