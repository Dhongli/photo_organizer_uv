#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片/视频自动归档工具 - Python 跨平台版 v1.4 (终极修复版)
✅ 仅排除 "归档"、"Archive"、"未识别" —— "待检测" 会被正常处理
✅ 主循环跳过已不存在的文件（防 FileNotFoundError）
✅ 仅对真实存在的文件计数（解决“6251个未识别但只有4个文件”问题）
✅ safe_move 限制重命名次数 + 时间戳兜底（防 _(...)_(...) 爆炸）
✅ 严格校验日期合法性（拒绝 2月31日等非法日期）
"""

import os
import re
import sys
import shutil
import argparse
import datetime
import subprocess
from pathlib import Path
from typing import Optional


SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.mp4', '.mov', '.gif'}
# ⚠️ 只排除这些目录；"待检测" 会被处理！
EXCLUDE_FOLDERS = {'归档', 'Archive', '未识别'}

def setup_heif_support():
    try:
        import pillow_heif
        from pillow_heif import register_heif_opener
        register_heif_opener()
        print("挺好的")
        return True
    except ImportError:
        print("⚠️  未安装 pillow-heif，HEIC 文件将被跳过。")
        return False

def is_valid_datetime(dt: datetime.datetime) -> bool:
    """严格校验日期是否真实存在（如拒绝 2025-02-31）"""
    now = datetime.datetime.now()
    future_limit = now + datetime.timedelta(days=365)
    try:
        # 强制验证日期合法性
        datetime.datetime(dt.year, dt.month, dt.day)
    except ValueError:
        return False
    return 1970 <= dt.year <= 2037 and dt <= future_limit

def parse_filename_time(stem: str) -> Optional[datetime.datetime]:
    # 1. mmexport1537184364881
    if m := re.match(r'^mmexport(\d{13})$', stem):
        ts = int(m.group(1)) / 1000
        dt = datetime.datetime.fromtimestamp(ts)
        return dt if is_valid_datetime(dt) else None

    # 2. _13位时间戳（结尾）
    if m := re.search(r'_(\d{13})$', stem):
        ts = int(m.group(1)) / 1000
        dt = datetime.datetime.fromtimestamp(ts)
        return dt if is_valid_datetime(dt) else None

    # 3. 17位结构化时间
    if m := re.search(r'(?:^|[^0-9])(\d{17})(?:[^0-9]|$)', stem):
        s = m.group(1)
        try:
            y, mo, d = int(s[0:4]), int(s[4:6]), int(s[6:8])
            h, mi, se, ms = int(s[8:10]), int(s[10:12]), int(s[12:14]), int(s[14:17])
            dt = datetime.datetime(y, mo, d, h, mi, se, ms * 1000)
            return dt if is_valid_datetime(dt) else None
        except ValueError:
            pass

    # 4. pt2018_12_23_23_45_07
    if m := re.search(r'(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})$', stem):
        y, mo, d, h, mi, se = map(int, m.groups())
        try:
            dt = datetime.datetime(y, mo, d, h, mi, se)
            return dt if is_valid_datetime(dt) else None
        except ValueError:
            pass

    # 5. SAVE_20180721_103322
    if m := re.search(r'(?<!\d)(\d{4})(\d{2})(\d{2})[_\-]?(\d{2})(\d{2})(\d{2})(?!\d)', stem):
        y, mo, d, h, mi, se = map(int, m.groups())
        try:
            dt = datetime.datetime(y, mo, d, h, mi, se)
            return dt if is_valid_datetime(dt) else None
        except ValueError:
            pass

    # 6. ✅ 2022-09-05 130147
    if m := re.search(r'(\d{4})-(\d{2})-(\d{2})\s+(\d{6})(?=\D|$)', stem):
        y, mo, d = map(int, m.groups()[:3])
        t_str = m.group(4)
        if len(t_str) == 6:
            h, mi, se = int(t_str[0:2]), int(t_str[2:4]), int(t_str[4:6])
            try:
                dt = datetime.datetime(y, mo, d, h, mi, se)
                return dt if is_valid_datetime(dt) else None
            except ValueError:
                pass

    return None

def get_exif_time(filepath: Path) -> Optional[datetime.datetime]:
    try:
        import exifread
        with open(filepath, 'rb') as f:
            tags = exifread.process_file(f, stop_tag='DateTimeOriginal', details=False)
            dt_str = str(tags.get('EXIF DateTimeOriginal', ''))
            if dt_str and ':' in dt_str:
                dt = datetime.datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                return dt if is_valid_datetime(dt) else None
    except Exception:
        pass
    return None

def get_video_creation_time(filepath: Path) -> Optional[datetime.datetime]:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format_tags=creation_time",
             "-of", "default=nw=1", str(filepath)],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("creation_time="):
                dt_str = line.split("=", 1)[1].strip()
                if dt_str.endswith('Z'):
                    dt_str = dt_str[:-1]
                dt = datetime.datetime.fromisoformat(dt_str)
                dt = dt.astimezone().replace(tzinfo=None)
                return dt if is_valid_datetime(dt) else None
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        pass
    return None

def safe_move(src: Path, dest_dir: Path) -> Path:
    """
    安全移动文件：
    - 若已在目标目录，直接返回
    - 否则移动，最多重命名10次，之后用时间戳兜底
    """
    try:
        src.resolve().relative_to(dest_dir.resolve())
        return src
    except ValueError:
        pass

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    counter = 1
    while dest.exists() and counter <= 10:
        name = f"{src.stem}_({counter}){src.suffix}"
        dest = dest_dir / name
        counter += 1

    if dest.exists():
        # 兜底：用时间戳确保唯一
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f")[:17]
        dest = dest_dir / f"{src.stem}_{ts}{src.suffix}"

    shutil.move(str(src), str(dest))
    return dest

def main(photo_dir: Path, no_log: bool = False):
    has_heif = setup_heif_support()
    log_lines = []
    def log(msg: str, level: str = "INFO"):
        line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {msg}"
        print(line)
        if not no_log:
            log_lines.append(line)

    archive_root = photo_dir / "归档"
    unrecognized_root = photo_dir / "未识别"
    archive_root.mkdir(exist_ok=True)
    unrecognized_root.mkdir(exist_ok=True)

    all_files = []
    for ext in SUPPORTED_EXTENSIONS:
        all_files.extend(photo_dir.rglob(f"*{ext}"))
        all_files.extend(photo_dir.rglob(f"*{ext.upper()}"))

    filtered_files = []
    for f in all_files:
        rel_parts = f.relative_to(photo_dir).parts[:-1]
        if any(part in EXCLUDE_FOLDERS for part in rel_parts):
            continue
        if f.suffix.lower() == '.heic' and not has_heif:
            continue
        filtered_files.append(f)

    if not filtered_files:
        log("未找到任何待处理的媒体文件（已跳过“归档”等目录）", "WARN")
        input("\n按回车退出...")
        return

    log(f"开始处理目录: {photo_dir}")
    log(f"扫描到 {len(filtered_files)} 个候选路径（可能含已删除文件）")

    results = []
    actual_processed = 0  # ← 关键：只统计真实存在的文件

    for file_path in filtered_files:
        if not file_path.exists():
            continue  # 跳过幽灵文件

        actual_processed += 1
        source_time = None
        method = ""

        if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.heic'}:
            source_time = get_exif_time(file_path)
            if source_time:
                method = "EXIF"

        if not source_time and file_path.suffix.lower() in {'.mp4', '.mov'}:
            source_time = get_video_creation_time(file_path)
            if source_time:
                method = "FFprobe"

        if not source_time:
            source_time = parse_filename_time(file_path.stem)
            if source_time:
                method = "文件名"

        if source_time:
            year = source_time.year
            month = f"{source_time.month:02d}"
            target_dir = archive_root / str(year) / f"{year}-{month}"
            dest = safe_move(file_path, target_dir)
            results.append({"success": True, "source": str(file_path), "dest": str(dest),
                           "time": source_time.strftime("%Y-%m-%d %H:%M:%S"), "method": method})
            log(f"✅ 归档: {file_path.name} → {dest.relative_to(photo_dir)} [时间: {results[-1]['time']}, 来源: {method}]")
        else:
            dest = safe_move(file_path, unrecognized_root)
            results.append({"success": False, "source": str(file_path), "dest": str(dest)})
            log(f"❓ 未识别: {file_path.name} → {dest.relative_to(photo_dir)}", "WARN")

    total = actual_processed
    success = sum(1 for r in results if r["success"])
    fail = total - success

    log("")
    log(f"✅ 实际处理文件：{total} 个")
    log(f"📁 成功归档：{success} 个")
    log(f"❓ 未识别文件：{fail} 个")

    if not no_log:
        log_file = photo_dir / f"photo_fix_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))
        print(f"\n📝 日志已保存至: {log_file}")

    input("\n按回车退出...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="照片/视频自动归档工具")
    parser.add_argument("directory", nargs="?", default=".", help="要处理的目录路径")
    parser.add_argument("--no-log", action="store_true", help="不生成日志文件")
    args = parser.parse_args()

    photo_dir = Path(args.directory).resolve()
    if not photo_dir.is_dir():
        print(f"错误：{photo_dir} 不是有效目录")
        sys.exit(1)
    
    main(photo_dir, args.no_log)