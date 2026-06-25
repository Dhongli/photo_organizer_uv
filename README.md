# Photo Organizer · 照片/视频自动归档工具

> 一个用 Python 写的零全局污染、跨平台的照片/视频整理工具。自动从 **EXIF**、**ffprobe** 或**文件名**中恢复拍摄时间，按 `归档/年/年-月/` 目录自动归类；无法识别时间的文件统一放入 `未识别/`，原文件不会被删除或修改内容。

---

## 目录

- [功能特性](#-功能特性)
- [系统要求](#-系统要求)
- [快速开始](#-快速开始)
- [使用方法](#-使用方法)
- [归档目录结构](#-归档目录结构)
- [文件名识别规则](#-文件名识别规则)
- [命令行参数](#-命令行参数)
- [工作流程](#-工作流程)
- [常见问题](#-常见问题)
- [项目结构](#-项目结构)
- [依赖说明](#-依赖说明)

---

## ✨ 功能特性

- 🔍 **三层时间识别**：按优先级依次尝试 EXIF（图片）→ ffprobe（视频）→ 文件名规则，三者任一命中即归档
- 📅 **严格的日期校验**：拒绝 `2025-02-31` 这类非法日期；限定 1970–2037 年、且不超过当前时间 +365 天
- 🗂 **智能归档结构**：自动创建 `归档/<年>/<年>-<月>/` 目录
- 🇨🇳 **国产机型适配**：识别 `MYXJ_`、`mmexport`、`pt2018_12_23_23_45_07`、`2022-09-05 130147` 等常见命名
- 🔁 **同名文件防覆盖**：自动追加 `_(1)`, `_(2)` … 后缀，最多尝试 10 次，溢出后用时间戳兜底
- 👻 **幽灵文件过滤**：扫描后文件被外部删除时静默跳过，不再抛 `FileNotFoundError`
- 🛡 **目录排除**：自动跳过 `归档/`、`Archive/`、`未识别/` 三个目录（避免重复处理）
- 📝 **可选日志**：默认生成 `photo_fix_<时间戳>.log`，可用 `--no-log` 关闭
- 🌍 **跨平台**：Windows / macOS / Linux 全平台运行
- 📦 **零全局污染**：依赖全部由 `uv` 安装在本地 `.venv`，不污染系统 Python

---

## 📋 系统要求

| 组件 | 版本要求 | 说明 |
| --- | --- | --- |
| Python | **≥ 3.13** | 由 `.python-version` 文件锁定 |
| uv | 最新版 | 现代化的 Python 包管理工具 |
| ffmpeg / ffprobe | 任意较新版本 | **仅在处理 .mp4 / .mov 时需要**；未安装时仅影响视频时间提取，图片和文件名识别不受影响 |
| 操作系统 | Windows / macOS / Linux | 已实测三平台均可用 |

> ⚠️ **ffprobe 不是 Python 包**，无法通过 `uv` 安装。请在系统层面安装 ffmpeg/ffprobe（见下方"安装 ffmpeg"）。

---

## 🚀 快速开始

### 1. 安装 `uv`（只需一次）

```bash
# Windows (PowerShell)
winget install --id=astral-sh.uv

# macOS
brew install uv

# Linux / WSL
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 安装 ffmpeg / ffprobe（处理视频需要）

```bash
# Windows (PowerShell，用 winget 或 choco)
winget install --id=Gyan.FFmpeg
# 或
choco install ffmpeg

# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo install ffmpeg

# 验证安装
ffprobe -version
```

> 不想处理视频？跳过此步，工具仍能正常处理图片和带时间戳命名的视频文件。

### 3. 同步项目依赖

在项目根目录执行：

```bash
uv sync
```

`uv` 会自动读取 `pyproject.toml` 和 `uv.lock`，在 `.venv/` 内安装锁定版本的所有依赖（首次约 30 秒）。

---

## 📖 使用方法

### 基础用法

```bash
# 在项目根目录运行（默认处理当前目录）
uv run python photo_organizer.py

# 处理指定目录（推荐：把所有待整理的照片放进一个文件夹）
uv run python photo_organizer.py "D:/Photos/Unsorted"

# 不生成日志文件
uv run python photo_organizer.py "D:/Photos/Unsorted" --no-log
```

> 💡 **路径建议**：为安全起见，先把要整理的照片复制到一个临时目录（例如 `D:/Photos/Unsorted`），再对该目录运行脚本，验证归档结果无误后再清理原始目录。

### Windows 直接双击运行

如果不想用命令行，也可以：

1. 在项目根目录新建一个 `run.bat`：
   ```bat
   @echo off
   uv run python photo_organizer.py "%~1"
   pause
   ```
2. 把待整理的文件夹拖到 `run.bat` 上即可。

### 直接调用 venv 内的 Python

如果不想每次都 `uv run`：

```bash
# 一次性激活 venv（PowerShell）
.\.venv\Scripts\Activate.ps1
python photo_organizer.py "D:/Photos/Unsorted"
```

---

## 📁 归档目录结构

运行后，工具会在你指定的目录内自动创建如下结构：

```
<待整理目录>/
├── 归档/                        # ✅ 成功识别的文件
│   ├── 2022/
│   │   ├── 2022-09/
│   │   │   ├── IMG_20220905_130147.jpg
│   │   │   ├── mmexport1662457184000.jpg
│   │   │   └── MYXJ_20220915213943_fast.jpg
│   │   └── 2022-12/
│   │       └── VID_20221224_180022.mp4
│   └── 2024/
│       └── 2024-01/
│           └── 1735689600000.jpg
│
├── 未识别/                      # ❓ 无法提取时间的文件
│   ├── random_photo.jpg
│   └── unknown_video.mp4
│
└── photo_fix_20240625_153022.log # 📝 运行日志（默认生成）
```

**核心规则**：
- 排除目录：`归档/`、`Archive/`、`未识别/`（仅这 3 个，**`待检测/` 仍会被处理**）
- 同名文件自动重命名为 `IMG_1234_(1).jpg`、`IMG_1234_(2).jpg` … 最多 10 次
- 超出 10 次后用时间戳兜底：`IMG_1234_20240625153022.jpg`

---

## 🧠 文件名识别规则

工具支持以下 6 种文件名模式（按顺序匹配，命中即返回）：

| # | 模式示例 | 正则片段 | 用途 |
| --- | --- | --- | --- |
| 1 | `mmexport1537184364881` | `^mmexport(\d{13})$` | 微信、小程序导出 |
| 2 | `IMG_1662457184000` | `_(\d{13})$` | 13 位 Unix 毫秒时间戳结尾 |
| 3 | `20220905130147234` | `\d{17}` (含前后非数字边界) | 17 位 `YYYYMMDDhhmmssSSS` |
| 4 | `pt2018_12_23_23_45_07` | `\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}$` | 部分监控/行车记录仪 |
| 5 | `SAVE_20180721_103322` | `\d{8}[_\-]?\d{6}` | 部分手机/相机命名 |
| 6 | `2022-09-05 130147` | `\d{4}-\d{2}-\d{2}\s+\d{6}` | 标准日期+紧凑时间 |

**不识别的情况**：
- 纯英文/中文文件名（`photo.jpg`、`风景.png`）
- 无时间戳的数字串（如 `1234.jpg`）
- 非法日期（如 `2025-02-31 12:00:00`）

这些文件会被移入 `未识别/`，**不会被丢弃**。

---

## ⚙️ 命令行参数

```text
usage: photo_organizer.py [-h] [--no-log] [directory]

positional arguments:
  directory        要处理的目录路径（默认为当前目录 "."）

options:
  -h, --help       显示帮助信息并退出
  --no-log         不生成 photo_fix_<时间戳>.log 日志文件
```

**示例**：

```bash
# 查看帮助
uv run python photo_organizer.py --help

# 处理当前目录，不写日志
uv run python photo_organizer.py --no-log

# 处理指定目录
uv run python photo_organizer.py "D:/Photos/Unsorted"
```

---

## 🔄 工作流程

```
开始
  ↓
扫描目录（递归，匹配 7 种后缀）
  ↓
过滤排除目录（归档/Archive/未识别）
  ↓
对每个文件尝试提取时间：
   1️⃣ EXIF（图片）
   2️⃣ ffprobe（视频）
   3️⃣ 文件名正则
  ↓
[成功] → safe_move 到 归档/<年>/<年>-<月>/
[失败] → safe_move 到 未识别/
  ↓
输出统计 & 保存日志
  ↓
等待回车退出（Windows 友好）
```

---

## ❓ 常见问题

### Q1：运行后提示 `未找到任何待处理的媒体文件`？
A：检查目录内是否有 `.jpg/.jpeg/.png/.heic/.mp4/.mov/.gif` 文件。**`待检测` 目录会被处理**，但 `归档`、`Archive`、`未识别` 这三个目录会被跳过——把文件移出来即可。

### Q2：视频文件全部进了 `未识别/`？
A：90% 是因为没装 `ffprobe`。在终端运行 `ffprobe -version` 验证；若提示命令不存在，请按 [快速开始 - 第 2 步](#2-安装-ffmpeg--ffprobe处理视频需要) 安装 ffmpeg。

### Q3：HEIC 文件被跳过？
A：需要 `pillow-heif`（已包含在 `pyproject.toml`）。如果 `uv sync` 失败，请检查 Python 版本是否为 3.13+。HEIC 是 Apple 的默认格式，Windows 默认不识别显示，但工具能正常读取和处理。

### Q4：文件会不会被损坏或丢失？
A：**不会**。工具用 `shutil.move` 移动文件（不修改内容）；同名文件通过 `_(N)` 后缀区分；无法识别的文件统一进 `未识别/`，**不会删除任何文件**。

### Q5：可以撤销归档吗？
A：当前版本没有内建撤销。建议运行前备份原始目录，或在临时副本上先试运行。

### Q6：脚本最后会卡住要求"按回车退出"，能去掉吗？
A：编辑 `photo_organizer.py` 末尾，注释掉 `input("\n按回车退出...")` 即可。这是为 Windows 双击运行时的体验设计的（防止窗口一闪而过），CLI 调用时可移除。

### Q7：能处理 RAW 格式（.cr2 .nef .arw .dng）吗？
A：当前不支持。这些格式 EXIF 信息存在但工具的 `SUPPORTED_EXTENSIONS` 未包含。如需支持，编辑 `photo_organizer.py:23` 加入对应后缀即可。

### Q8：能按"年-月-日"再细分目录吗？
A：当前按 `归档/年/年-月/` 组织。如需 `归档/年/年-月/年-月-日/`，可修改 `main()` 函数中 `target_dir` 的构造逻辑（约第 230 行）。

---

## 📦 项目结构

```
photo_organizer_uv/
├── photo_organizer.py        # 核心脚本（单文件，268 行）
├── pyproject.toml            # 项目元数据 & 依赖声明
├── uv.lock                   # 锁定的依赖版本（可复现安装）
├── .python-version           # 锁定 Python 3.13
├── .venv/                    # uv 创建的虚拟环境（已 .gitignore）
├── .gitignore                # Git 忽略规则
├── requirements.txtbak       # 旧版 pip 依赖备份（仅供参考）
└── README.md                 # 本文件
```

---

## 📝 依赖说明

### Python 依赖（由 `uv` 管理）

| 包 | 版本 | 用途 |
| --- | --- | --- |
| `exifread` | ≥ 3.5.1 | 读取 JPEG/PNG 的 EXIF `DateTimeOriginal` |
| `Pillow` | ≥ 12.0.0 | 图像处理基础库 |
| `pillow-heif` | ≥ 1.1.1 | 启用 HEIC/HEIF 格式支持 |

### 系统依赖（需手动安装）

| 工具 | 是否必需 | 用途 |
| --- | --- | --- |
| `ffmpeg` / `ffprobe` | **仅视频必需** | 通过 `format_tags=creation_time` 提取视频创建时间 |
| `python` | 必需 | 由 `uv` 自动管理 |

### 升级依赖

```bash
# 升级所有依赖到 pyproject.toml 允许的最新版本
uv sync --upgrade

# 添加新依赖
uv add <package-name>

# 移除依赖
uv remove <package-name>
```

---

## 📜 许可

本项目为个人照片整理工具，未声明开源协议。如需二次发布请先与作者确认。

---

**祝你整理愉快！** 🎉
