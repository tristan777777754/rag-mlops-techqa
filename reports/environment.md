# ENV-001 — 開發環境實測

日期：2026-11-24（Asia/Taipei）  
狀態：`DONE`

## 已驗證

| 項目 | 實測結果 | 證據 |
|---|---|---|
| Windows | Windows 11，build `10.0.26200.9974` | 使用者提供的 `ver` 畫面與 `bcdedit` 輸出 |
| WSL | 預設版本 2，Ubuntu 使用 WSL2 | `wsl --status`、`wsl -l -v` |
| Linux kernel | `6.18.58.1-microsoft-standard-WSL2`，`x86_64` | Ubuntu `uname -a` |
| Python | `3.14.4` | Ubuntu `python3 --version` |
| Git | `2.53.0` | Ubuntu `git --version` |
| GPU | NVIDIA GeForce RTX 3060 Ti，8192 MiB 專屬 VRAM；WSL 可見 | Ubuntu `nvidia-smi` |
| WSL NVIDIA-SMI | `610.57.01`；KMD `610.88`；CUDA UMD `13.3` | Ubuntu `nvidia-smi` |
| Docker Desktop | `4.100.1`，Linux Engine `29.9.3`；Client 和 Server 已連通 | Ubuntu `docker version` |
| Docker Compose | `v5.7.1` | Ubuntu `docker compose version` |
| Git repository | `C:/Users/trist/OneDrive/桌面/rag-mlops-techqa`；`origin` 指向 `https://github.com/tristan777777754/rag-mlops-techqa.git`；`main` 工作樹乾淨 | 該目錄 `git remote -v`、`git status --short --branch`、`git rev-parse --show-toplevel` |

Windows 工作管理員另顯示 NVIDIA GeForce RTX 3060 Ti、專屬 GPU 記憶體 8.0 GB，以及顯示驅動版本 `32.0.16.1088`。這些數值來自使用者提供的畫面。

## 限制與待確認項目

- Ubuntu 的 `python3 -c 'import torch; ...'` 回傳 `ModuleNotFoundError: No module named 'torch'`。PyTorch 版本與 `torch.cuda.is_available()` 尚未驗證。`nvidia-smi` 成功只證明 WSL 能辨識 GPU。
- 專案目前使用的 clone 位於 Windows 的 OneDrive 桌面。Ubuntu 當時的工作目錄為 `/mnt/c/Users/trist`。若之後依執行指南使用 WSL 的 Linux 檔案系統開發，應確認實際 repo 位置。
- Docker 的 Linux GPU 容器能力尚未測試。CPU 資料稽核不需等待此項。

## 驗收與後續

已確認 WSL2、GPU、Python、Git、Docker 和 Compose 的實際版本與基本可用性。新專案資料夾是可用的 Git clone，符合 repo 啟動檢查。ENV-001 完成。PyTorch 尚未安裝，安裝後再補上 CUDA 驗證結果；依賴鎖檔、lint 和測試屬於 `REPO-001`。
