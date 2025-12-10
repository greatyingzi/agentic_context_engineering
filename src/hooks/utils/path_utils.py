#!/usr/bin/env python3
"""
Path and directory utilities for Claude hooks.
"""
import os
from datetime import datetime
from pathlib import Path
import glob


# 诊断文件管理配置
MAX_DIAGNOSTIC_FILES = 50  # 最大文件数
MAX_DIAGNOSTIC_DAYS = 7   # 保留天数
MAX_DIAGNOSTIC_SIZE_KB = 100  # 单个文件最大大小(KB)


def get_project_dir() -> Path:
    """Get the project directory from environment or current working directory."""
    project_dir = os.getenv("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    return Path.cwd()


def get_user_claude_dir() -> Path:
    """Get the user's Claude configuration directory."""
    home = Path.home()
    return home / ".claude"


def is_diagnostic_mode() -> bool:
    """Check if diagnostic mode is enabled."""
    flag_file = get_project_dir() / ".claude" / "diagnostic_mode"
    return flag_file.exists()


def save_diagnostic(content: str, name: str):
    """Save diagnostic content to a timestamped file with automatic cleanup."""
    # 1. 先清理旧文件
    _cleanup_old_diagnostic_files()

    # 2. 准备保存新文件
    diagnostic_dir = get_project_dir() / ".claude" / "diagnostic"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = diagnostic_dir / f"{timestamp}_{name}.txt"

    # 3. 限制单个文件大小
    if len(content) > MAX_DIAGNOSTIC_SIZE_KB * 1024:
        truncated_content = content[:MAX_DIAGNOSTIC_SIZE_KB * 1024]
        content = truncated_content + f"\n\n... [内容因过大被截断，原始大小: {len(content)} 字节]"

    # 4. 保存文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _cleanup_old_diagnostic_files():
    """清理旧的诊断文件，控制数量和保留时间"""
    diagnostic_dir = get_project_dir() / ".claude" / "diagnostic"
    if not diagnostic_dir.exists():
        return

    # 获取所有诊断文件并按修改时间排序
    files = []
    for pattern in ["*.txt", "*.log"]:
        files.extend(diagnostic_dir.glob(pattern))

    if not files:
        return

    # 按修改时间排序（最新的在前）
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # 1. 按文件数量限制
    current_count = len(files)
    if current_count > MAX_DIAGNOSTIC_FILES:
        files_to_delete = files[MAX_DIAGNOSTIC_FILES:]
        for old_file in files_to_delete:
            try:
                old_file.unlink()
                print(f"已删除旧诊断文件: {old_file.name}")
                # 从当前列表中移除
                files.remove(old_file)
            except Exception as e:
                print(f"删除文件失败 {old_file}: {e}")

    # 2. 按天数限制（基于更新后的文件列表）
    cutoff_time = datetime.now().timestamp() - (MAX_DIAGNOSTIC_DAYS * 24 * 3600)

    for f in files:  # 使用已更新的文件列表
        try:
            if f.stat().st_mtime < cutoff_time:
                f.unlink()
                print(f"已删除过期诊断文件: {f.name}")
        except Exception as e:
            print(f"删除过期文件失败 {f}: {e}")


def get_diagnostic_stats() -> dict:
    """获取诊断文件统计信息"""
    diagnostic_dir = get_project_dir() / ".claude" / "diagnostic"
    if not diagnostic_dir.exists():
        return {"total_files": 0, "total_size_kb": 0, "oldest_file": None, "newest_file": None}

    files = list(diagnostic_dir.glob("*.txt")) + list(diagnostic_dir.glob("*.log"))
    if not files:
        return {"total_files": 0, "total_size_kb": 0, "oldest_file": None, "newest_file": None}

    total_size = sum(f.stat().st_size for f in files)
    files.sort(key=lambda p: p.stat().st_mtime)

    return {
        "total_files": len(files),
        "total_size_kb": round(total_size / 1024, 2),
        "oldest_file": files[0].name if files else None,
        "newest_file": files[-1].name if files else None,
        "oldest_time": datetime.fromtimestamp(files[0].stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if files else None,
        "newest_time": datetime.fromtimestamp(files[-1].stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if files else None
    }