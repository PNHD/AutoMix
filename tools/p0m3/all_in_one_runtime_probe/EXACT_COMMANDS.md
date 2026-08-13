# P0-M3-R3 All-In-One runtime probe — exact command evidence

All environments, third-party clones, wheels, caches, and model weights lived
outside the repository. The commands below use sanitized scratch roots; they do
not contain owner-media locations.

## Source pins and metadata inspection

```powershell
git clone --filter=blob:none --no-checkout https://github.com/SHI-Labs/NATTEN.git E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\NATTEN
git -C E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\NATTEN fetch --depth 1 origin tag v0.14.6
git -C E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\NATTEN checkout --detach v0.14.6
git clone --filter=blob:none --no-checkout https://github.com/mir-aidj/all-in-one.git E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\all-in-one-canonical
git -C E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\all-in-one-canonical fetch --depth 1 origin 18e78903c0365147a2c5d4e5e57ebf88cb7d800e
git -C E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\all-in-one-canonical checkout --detach 18e78903c0365147a2c5d4e5e57ebf88cb7d800e
git clone --filter=blob:none --no-checkout https://github.com/mir-aidj/all-in-one.git E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\all-in-one-pr37
git -C E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\all-in-one-pr37 fetch --depth 1 origin 5c2b2ce571c04054a0b54ceba365c0b8c1188099
git -C E:\AIProjects\_automix-p0m3r3-runtime-probe-20260813\all-in-one-pr37 checkout --detach 5c2b2ce571c04054a0b54ceba365c0b8c1188099
gh pr view 37 --repo mir-aidj/all-in-one --json number,state,headRefOid,baseRefOid,body,commits,url,title
gh release view v0.14.6 --repo SHI-Labs/NATTEN --json tagName,targetCommitish,publishedAt,url,assets
gh release view v0.21.0 --repo SHI-Labs/NATTEN --json tagName,targetCommitish,publishedAt,url,assets
```

## Isolated environments and P1 packages

```bash
python3 -m venv /home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv
/home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv/bin/python -m pip install uv==0.8.13
UV_PYTHON_INSTALL_DIR=/home/pnhd/automix-p0m3r3-runtime-probe-20260813/python /home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv/bin/uv python install 3.10.18 3.11.13
UV_PYTHON_INSTALL_DIR=/home/pnhd/automix-p0m3r3-runtime-probe-20260813/python /home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv/bin/uv venv --python 3.10.18 /home/pnhd/automix-p0m3r3-runtime-probe-20260813/p1-legacy
UV_PYTHON_INSTALL_DIR=/home/pnhd/automix-p0m3r3-runtime-probe-20260813/python /home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv/bin/uv venv --python 3.11.13 /home/pnhd/automix-p0m3r3-runtime-probe-20260813/p2-pr37
/home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv/bin/uv pip install --python /home/pnhd/automix-p0m3r3-runtime-probe-20260813/p1-legacy/bin/python --index-url https://download.pytorch.org/whl/cu118 torch==2.0.0+cu118 torchvision==0.15.1+cu118 torchaudio==2.0.1+cu118
curl -fL --retry 3 -o natten-0.14.6+torch200cu118-cp310-cp310-linux_x86_64.whl https://github.com/SHI-Labs/NATTEN/releases/download/v0.14.6/natten-0.14.6%2Btorch200cu118-cp310-cp310-linux_x86_64.whl
echo 'afb05fc4857dbf623fd026f2f8e1db42e3531ba6bff30cf4741339418f299efa  natten-0.14.6+torch200cu118-cp310-cp310-linux_x86_64.whl' | sha256sum -c -
/home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv/bin/uv pip install --python /home/pnhd/automix-p0m3r3-runtime-probe-20260813/p1-legacy/bin/python --no-deps ./natten-0.14.6+torch200cu118-cp310-cp310-linux_x86_64.whl
/home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv/bin/uv pip install --python /home/pnhd/automix-p0m3r3-runtime-probe-20260813/p1-legacy/bin/python nvidia-cuda-nvrtc-cu11==11.8.89
```

P1 also installed the canonical package editable from its detached clean
checkout plus its declared runtime dependencies. The normal loader call was:

```python
model = load_pretrained_model("harmonix-fold0", cache_dir=cache_dir, device="cuda")
```

The first synthetic forward failed with
`libnvrtc.so: cannot open shared object file`. The exact CUDA 11.8 NVRTC
runtime package was added inside P1 only, and an unversioned `libnvrtc.so`
symlink was created inside that virtual environment. No system path changed.

## P2 exact claimed matrix

```bash
/home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv/bin/uv pip install --python /home/pnhd/automix-p0m3r3-runtime-probe-20260813/p2-pr37/bin/python --index-url https://download.pytorch.org/whl/cu128 torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128
curl -fL --retry 3 -o natten-0.21.0+torch270cu128-cp311-cp311-linux_x86_64.whl https://github.com/SHI-Labs/NATTEN/releases/download/v0.21.0/natten-0.21.0%2Btorch270cu128-cp311-cp311-linux_x86_64.whl
echo 'b3d946655dde77c616611b4a9b2f75b9cb8fa2653e6176718c5d9ec001cd6bcc  natten-0.21.0+torch270cu128-cp311-cp311-linux_x86_64.whl' | sha256sum -c -
/home/pnhd/automix-p0m3r3-runtime-probe-20260813/bootstrap-uv/bin/uv pip install --python /home/pnhd/automix-p0m3r3-runtime-probe-20260813/p2-pr37/bin/python --no-deps ./natten-0.21.0+torch270cu128-cp311-cp311-linux_x86_64.whl
```

The PR checkout was installed editable and unmodified. Import failed because
`natten.functional` exported none of `na1d_qk`, `na1d_av`, `na2d_qk`, or
`na2d_av` under the claimed matrix.

## Repository verification

```powershell
python tools\p0m3\all_in_one_runtime_probe\verify_runtime_probe.py --evidence tools\p0m3\all_in_one_runtime_probe\results\runtime_probe_sanitized.json --out tools\p0m3\all_in_one_runtime_probe\results\runtime_probe_validation.json
python tools\p0m3\all_in_one_runtime_probe\verify_runtime_probe.py --evidence tools\p0m3\all_in_one_runtime_probe\results\runtime_probe_sanitized.json --require-origin-match
```
