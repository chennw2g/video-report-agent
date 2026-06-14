# whisper.cpp CUDA Build 2026-06-14

This note records the local Windows CUDA build used by `video-bundle-agent`.

## Result

- Source: official `ggml-org/whisper.cpp` tag `v1.8.6`, commit `23ee035`.
- Source path: `D:\Workshop\whisper.cpp\src-v1.8.6`.
- Build path: `D:\Workshop\whisper.cpp\src-v1.8.6\build-cuda`.
- Packaged runtime path: `D:\Workshop\whisper.cpp\v1.8.6-cuda\Release`.
- Active CLI: `D:\Workshop\whisper.cpp\v1.8.6-cuda\Release\whisper-cli.exe`.
- Existing CPU release preserved at `D:\Workshop\whisper.cpp\v1.8.6\Release`.

`src/video_bundle_agent/tools/paths.py` now prefers the CUDA release before the old CPU release.

## Toolchain

- GPU: NVIDIA GeForce RTX 5060 Laptop GPU.
- CUDA compute capability: `12.0`; CMake converts `CMAKE_CUDA_ARCHITECTURES=120` to `120a`.
- NVIDIA driver: 596.36, reported CUDA compatibility: 13.2.
- MSVC: Visual Studio Build Tools 2022, `cl.exe` 19.44.35228.
- Windows SDK: 10.0.26100.0.
- CMake/Ninja: installed into project `.venv` with `uv pip install cmake ninja`.
- CUDA Toolkit: local NVIDIA redist composition under `D:\Workshop\CUDA\v13.2.1-redist`.

CUDA redist components installed:

- `cuda_nvcc`
- `cuda_cccl`
- `cuda_crt`
- `cuda_cudart`
- `libcublas`
- `libnvvm`
- `libnvjitlink`
- `libnvptxcompiler`
- `libnvfatbin`

## Configure Command

Run from a PowerShell prompt:

```powershell
$src = 'D:/Workshop/whisper.cpp/src-v1.8.6'
$build = 'D:/Workshop/whisper.cpp/src-v1.8.6/build-cuda'
$cuda = 'D:/Workshop/CUDA/v13.2.1-redist'
$vcvars = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
$cmake = 'D:/W/Codex/video-summarize-program/.venv/Scripts/cmake.exe'
$ninja = 'D:/W/Codex/video-summarize-program/.venv/Scripts/ninja.exe'
$cl = 'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/cl.exe'
$rc = 'C:/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64/rc.exe'
$mt = 'C:/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64/mt.exe'

cmd /V:ON /d /s /c "call ""$vcvars"" && set CUDA_PATH=$cuda && set CUDAToolkit_ROOT=$cuda && set PATH=$cuda/bin;$cuda/bin/x64;D:\W\Codex\video-summarize-program\.venv\Scripts;!PATH! && ""$cmake"" -S ""$src"" -B ""$build"" -G Ninja -DCMAKE_MAKE_PROGRAM=""$ninja"" -DCMAKE_C_COMPILER=""$cl"" -DCMAKE_CXX_COMPILER=""$cl"" -DCMAKE_RC_COMPILER=""$rc"" -DCMAKE_MT=""$mt"" -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DGGML_CUDA_NCCL=OFF -DCMAKE_CUDA_COMPILER=""$cuda/bin/nvcc.exe"" -DCUDAToolkit_ROOT=""$cuda"" -DCMAKE_CUDA_ARCHITECTURES=120 -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF"
```

Important Windows detail: use `cmd /V:ON` and `!PATH!`. Plain `%PATH%` is expanded before `vcvars64.bat`
runs, causing `nvcc fatal : Cannot find compiler 'cl.exe' in PATH`.

## Build Command

```powershell
cmd /V:ON /d /s /c "call ""$vcvars"" && set CUDA_PATH=$cuda && set CUDAToolkit_ROOT=$cuda && set PATH=$cuda/bin;$cuda/bin/x64;D:\W\Codex\video-summarize-program\.venv\Scripts;!PATH! && ""$cmake"" --build ""$build"" --config Release --parallel 8"
```

## Verification

Direct CUDA smoke:

```powershell
D:\Workshop\whisper.cpp\v1.8.6-cuda\Release\whisper-cli.exe `
  -m D:\Workshop\whisper.cpp\models\ggml-base.bin `
  -f D:\W\Codex\video-summarize-program\outputs\asr-benchmark-20260612\bilibili_60s.wav `
  -l auto -dl
```

Expected evidence:

- `ggml_cuda_init: found 1 CUDA devices`
- `Device 0: NVIDIA GeForce RTX 5060 Laptop GPU, compute capability 12.0`
- `whisper_backend_init_gpu: using CUDA0 backend`
- `system_info` contains `CUDA : ARCHS = 1200` and `BLACKWELL_NATIVE_FP4 = 1`

Language-probe smoke result:

- Chinese sample: detected `zh`, confidence around `0.997`.
- GPU encode time on the 60-second probe: about `107 ms`.
- Previous CPU encode time on the same probe was about `549 ms`.

Full English benchmark on existing `youtube_16k.wav`:

- Model: `ggml-large-v3-turbo.bin`.
- Audio duration: `1238.0373125` seconds.
- CUDA transcription time: `38.1886913` seconds.
- Real-time factor: `0.030846`.
- WER vs YouTube official JSON3 subtitle: `1.29%` (`36` token errors over `2,783` reference tokens).
- Output: `outputs/asr-benchmark-20260614-gpu-whisper/youtube_turbo_gpu/`.

Previous CPU result on the same English source was `802.58` seconds, RTF `0.648`, WER `2.01%`.

## Rollback

The old CPU release is untouched. To fall back, remove the CUDA path preference in
`src/video_bundle_agent/tools/paths.py` or set `PATH` / environment overrides to the CPU release.
