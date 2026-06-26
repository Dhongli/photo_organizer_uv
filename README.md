# Photo Organizer · 照片/视频自动归档工具

## 缘起

手机照片和视频导入电脑或上传网盘后，文件的修改时间经常被 Windows「吃掉」——系统会把时间戳改成导入那天，而不是实际拍摄的日期。网盘同步后也是一样。

这导致所有照片混在一起，完全失去了按年份排序的能力。当我想回顾过去某段时光时，根本无法快速定位到那个年份、那个月份的照片。试过不少整理工具，要么操作繁琐，要么识别不准。

后来我想：既然 Windows 和网盘的时间处理都靠不住，不如干脆按拍摄时间，把照片自动归档到 `年份/年-月/` 的文件夹里。手机拍的照片命名本身就有规律——时间戳、年月日、微信导出格式等，是可以从文件名中恢复出拍摄时间的。

于是就有了这个工具。

> **下载 exe**：从 [Releases](../../releases) 页面直接下载，无需 Python 环境。

---

## 它能做什么

扫描指定目录下所有照片和视频，自动从 **EXIF 信息**、**视频元数据** 或 **文件名** 中提取拍摄时间，然后按 `归档/2023/2023-10/` 这样的结构自动归类。无法识别时间的文件放入 `未识别/` 目录，**不会被删除**。

提供两种使用方式：

- **命令行（CLI）**：适合熟悉终端的用户
- **桌面 GUI**：双击运行，选择目录即可，适合所有用户

---

## 支持的格式

| 类型 | 格式 |
|---|---|
| 图片 | `.jpg` `.jpeg` `.png` `.heic` `.gif` |
| RAW | `.dng` `.cr2` `.nef` `.arw` |
| 视频 | `.mp4` `.mov` |

---

## 文件名识别规则

工具按优先级依次尝试以下 6 种模式：

| # | 示例 | 说明 |
|---|---|---|
| 1 | `mmexport1537184364881` | 微信/小程序导出（13 位毫秒时间戳） |
| 2 | `IMG_1662457184000` | 文件名末尾 13 位 Unix 时间戳 |
| 3 | `20220905130147234` | 17 位 `YYYYMMDDhhmmssSSS` |
| 4 | `pt2018_12_23_23_45_07` | 监控/行车记录仪格式 |
| 5 | `SAVE_20180721_103322` | 部分手机/相机命名 |
| 6 | `2022-09-05 130147` | 标准日期 + 紧凑时间 |

无法匹配的文件不会被丢弃，统一移入 `未识别/` 目录。

---

## 归档目录结构

```
<待整理目录>/
├── 归档/
│   ├── 2022/
│   │   ├── 2022-09/
│   │   │   ├── IMG_20220905_130147.jpg
│   │   │   └── mmexport1662457184000.jpg
│   │   └── 2022-12/
│   │       └── VID_20221224_180022.mp4
│   └── 2024/
│       └── 2024-01/
│           └── 1735689600000.jpg
├── 未识别/
│   └── random_photo.jpg
└── photo_fix_20240625_153022.log
```

---

## 使用方法

### 方式一：下载 exe（推荐）

从 [Releases](../../releases) 页面下载最新版 `PhotoOrganizer.exe`，无需安装 Python，双击即可使用。

### 方式二：源码运行

1. 安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)（如已安装跳过）

```bash
# Windows
winget install --id=astral-sh.uv

# macOS
brew install uv
```

2. 在项目目录安装依赖并启动

```bash
uv sync

# GUI 版
uv run python photo_organizer_gui.py

# 或命令行版
uv run python photo_organizer.py "D:/Photos/Unsorted"
```

### 命令行参数

```
usage: photo_organizer.py [-h] [--no-log] [directory]

positional arguments:
  directory        要处理的目录路径（默认为当前目录）

options:
  -h, --help       显示帮助信息
  --no-log         不生成日志文件
```

---

## 工作流程

```
扫描目录（递归，匹配所有支持的后缀）
  ↓
跳过 已归档 / Archive / 未识别 目录
  ↓
对每个文件尝试提取拍摄时间：
  1. EXIF（图片 / RAW）
  2. ffprobe（视频）
  3. 文件名正则
  ↓
[成功] → 移动到 归档/<年>/<年>-<月>/
[失败] → 移动到 未识别/
  ↓
输出统计，保存日志
```

---

## 打包为 exe

exe 已在 [Releases](../../releases) 页面提供下载。如需自行打包：

```bash
uv run pyinstaller --onefile --windowed --name "PhotoOrganizer" photo_organizer_gui.py
```

---

## 依赖说明

### Python 依赖

| 包 | 用途 |
|---|---|
| `exifread` | 读取图片/RAW 的 EXIF 拍摄时间 |
| `Pillow` | 图像处理基础库 |
| `pillow-heif` | HEIC/HEIF 格式支持 |
| `PyQt6` | 桌面 GUI 界面 |
| `PyInstaller` | 打包为 exe（开发依赖） |

### 系统依赖

| 工具 | 是否必需 | 用途 |
|---|---|---|
| `ffmpeg` / `ffprobe` | 仅视频必需 | 提取视频创建时间 |

> 不处理视频可跳过安装 ffmpeg，图片和文件名识别不受影响。

---

## 常见问题

**Q：运行后提示「未找到任何待处理的媒体文件」？**
A：检查目录内是否有支持格式的文件。`归档`、`Archive`、`未识别` 这三个目录会被自动跳过。

**Q：视频全部进了「未识别/」？**
A：大概率是没装 ffprobe。运行 `ffprobe -version` 验证，未安装请按上方说明安装 ffmpeg。

**Q：文件会不会被损坏或丢失？**
A：不会。工具仅移动文件（`shutil.move`），不修改文件内容。同名文件自动加 `_(1)`、`_(2)` 后缀区分。

**Q：可以撤销归档吗？**
A：没有内建撤销功能。建议运行前先备份原始目录。

---

## 项目结构

```
photo_organizer_uv/
├── photo_organizer.py          # 核心逻辑（CLI）
├── photo_organizer_gui.py      # PyQt6 桌面 GUI
├── PhotoOrganizer.spec         # PyInstaller 打包配置
├── dist/
│   └── PhotoOrganizer.exe      # 打包好的可执行文件
├── pyproject.toml              # 项目依赖声明
├── uv.lock                     # 锁定的依赖版本
└── README.md                   # 本文件
```

---

本项目为个人照片整理工具，未声明开源协议。如需二次发布请先与作者确认。
