import os
import threading
import time
from typing import List, Tuple, Callable, Optional

from .rclone_wrapper import (
    RcloneWrapper, RcloneConfigManager, RcloneProgressParser,
    RcloneProgress, get_rclone_path
)


class RcloneFileOperations:
    def __init__(self, rclone: RcloneWrapper, config_mgr: RcloneConfigManager):
        self.rclone = rclone
        self.config_mgr = config_mgr
        self._remote_name: str = ""
        self._cancelled = False

    def setup_remote(self, name: str, host: str, username: str, password: str,
                     port: int = 445, domain: str = "") -> bool:
        self._remote_name = name
        return self.config_mgr.create_smb_remote(
            name=name, host=host, username=username,
            password=password, port=port, domain=domain
        )

    @property
    def remote_prefix(self) -> str:
        return f"{self._remote_name}:" if self._remote_name else ""

    def upload_files_async(
        self,
        local_files: List[Tuple[str, str, bool]],
        remote_base: str,
        on_progress: Callable[[str, int, int], None],
        on_complete: Callable[[int, int], None],
        on_error: Callable[[str, str], None],
        on_log: Callable[[str], None],
        manager=None,
        task_id=None,
    ):
        self._cancelled = False

        def upload_thread():
            success_count = 0
            total_files = len(local_files)
            remote_base_norm = remote_base.replace("\\", "/")
            if not remote_base_norm.startswith("/"):
                remote_base_norm = "/" + remote_base_norm

            task = manager.get_task(task_id) if manager and task_id else None
            items = task.items if task else []

            for i, (filename, local_path, is_dir) in enumerate(local_files):
                if self._cancelled:
                    on_log("上传已取消")
                    if manager and task_id:
                        for item in items:
                            if item.status == "pending":
                                manager.update_task_status(task_id, item, "failed", "用户取消")
                    break

                item = items[i] if manager and i < len(items) else None
                on_progress(filename, i + 1, total_files)

                try:
                    if item and manager:
                        manager.update_task_status(task_id, item, "running")

                    if is_dir:
                        remote_dir = f"{self.remote_prefix}{remote_base_norm}/{filename}"
                        ret = self._upload_directory(local_path, remote_dir, on_log, manager, task_id, item)
                    else:
                        remote_file = f"{self.remote_prefix}{remote_base_norm}/{filename}"
                        ret = self._upload_file(local_path, remote_file, on_log, manager, task_id, item)

                    if ret:
                        success_count += 1
                        if item and manager:
                            manager.update_task_status(task_id, item, "completed")
                    else:
                        on_error(filename, "rclone 传输失败")
                        if item and manager:
                            manager.update_task_status(task_id, item, "failed", "rclone 传输失败")
                except Exception as e:
                    on_error(filename, str(e))
                    if item and manager:
                        manager.update_task_status(task_id, item, "failed", str(e))

            on_complete(success_count, total_files)

        threading.Thread(target=upload_thread, daemon=True).start()

    def download_files_async(
        self,
        remote_files: List[Tuple[str, str, str, bool]],
        local_base: str,
        on_progress: Callable[[str, int, int], None],
        on_complete: Callable[[int, int], None],
        on_error: Callable[[str, str], None],
        on_log: Callable[[str], None],
        manager=None,
        task_id=None,
    ):
        self._cancelled = False

        def download_thread():
            success_count = 0
            total_files = len(remote_files)

            task = manager.get_task(task_id) if manager and task_id else None
            items = task.items if task else []

            for i, (filename, remote_path, local_path, is_dir) in enumerate(remote_files):
                if self._cancelled:
                    on_log("下载已取消")
                    if manager and task_id:
                        for item in items:
                            if item.status == "pending":
                                manager.update_task_status(task_id, item, "failed", "用户取消")
                    break

                item = items[i] if manager and i < len(items) else None
                on_progress(filename, i + 1, total_files)

                try:
                    if item and manager:
                        manager.update_task_status(task_id, item, "running")

                    remote_norm = remote_path.replace("\\", "/")
                    if not remote_norm.startswith("/"):
                        remote_norm = "/" + remote_norm
                    remote_full = f"{self.remote_prefix}{remote_norm}"

                    if is_dir:
                        ret = self._download_directory(remote_full, local_path, on_log, manager, task_id, item)
                    else:
                        ret = self._download_file(remote_full, local_path, on_log, manager, task_id, item)

                    if ret:
                        success_count += 1
                        if item and manager:
                            manager.update_task_status(task_id, item, "completed")
                    else:
                        on_error(filename, "rclone 传输失败")
                        if item and manager:
                            manager.update_task_status(task_id, item, "failed", "rclone 传输失败")
                except Exception as e:
                    on_error(filename, str(e))
                    if item and manager:
                        manager.update_task_status(task_id, item, "failed", str(e))

            on_complete(success_count, total_files)

        threading.Thread(target=download_thread, daemon=True).start()

    def _upload_file(self, local_path: str, remote_path: str,
                     on_log: Callable[[str], None],
                     manager=None, task_id=None, item=None) -> bool:
        filename = os.path.basename(local_path)
        on_log(f"正在上传: {filename} (rclone)")

        def handle_stderr(line: str):
            progress = RcloneProgressParser.parse_line(line)
            if progress and progress.percentage > 0:
                speed_str = progress.speed_human or ""
                on_log(f"正在上传: {filename} - {progress.percentage:.0f}% ({speed_str})")
                if manager and task_id and item:
                    manager.update_task_progress(task_id, item, progress.percentage / 100.0, speed_str)
            elif line.strip() and "ERROR" in line.upper():
                on_log(f"[rclone] {line}")

        ret = self.rclone.execute(
            [
                "copyto", local_path, remote_path,
                "--progress",
                "--inplace",
                "--stats", "1s",
                "--stats-one-line",
                "--stats-log-level", "NOTICE",
            ],
            on_output=lambda line: None,
            on_error=handle_stderr,
        )

        if ret == 0:
            on_log(f"上传成功: {filename}")
            return True
        else:
            on_log(f"上传失败 (退出码 {ret}): {filename}")
            return False

    def _download_file(self, remote_path: str, local_path: str,
                       on_log: Callable[[str], None],
                       manager=None, task_id=None, item=None) -> bool:
        filename = os.path.basename(local_path)
        on_log(f"正在下载: {filename} (rclone)")

        local_dir = os.path.dirname(local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

        def handle_stderr(line: str):
            progress = RcloneProgressParser.parse_line(line)
            if progress and progress.percentage > 0:
                speed_str = progress.speed_human or ""
                on_log(f"正在下载: {filename} - {progress.percentage:.0f}% ({speed_str})")
                if manager and task_id and item:
                    manager.update_task_progress(task_id, item, progress.percentage / 100.0, speed_str)
            elif line.strip() and "ERROR" in line.upper():
                on_log(f"[rclone] {line}")

        ret = self.rclone.execute(
            [
                "copyto", remote_path, local_path,
                "--progress",
                "--inplace",
                "--stats", "1s",
                "--stats-one-line",
                "--stats-log-level", "NOTICE",
            ],
            on_output=lambda line: None,
            on_error=handle_stderr,
        )

        if ret == 0:
            on_log(f"下载成功: {filename}")
            return True
        else:
            on_log(f"下载失败 (退出码 {ret}): {filename}")
            return False

    def _upload_directory(self, local_dir: str, remote_dir: str,
                          on_log: Callable[[str], None],
                          manager=None, task_id=None, item=None) -> bool:
        dirname = os.path.basename(local_dir)
        on_log(f"正在上传目录: {dirname} (rclone)")

        def handle_stderr(line: str):
            progress = RcloneProgressParser.parse_line(line)
            if progress and progress.percentage > 0:
                speed_str = progress.speed_human or ""
                on_log(f"上传进度: {progress.files_transferred}/{progress.files_total} 文件 - {progress.percentage:.0f}% ({speed_str})")
                if manager and task_id and item:
                    manager.update_task_progress(task_id, item, progress.percentage / 100.0, speed_str)
            elif line.strip() and "ERROR" in line.upper():
                on_log(f"[rclone] {line}")

        ret = self.rclone.execute(
            [
                "copy", local_dir, remote_dir,
                "--progress",
                "--transfers", "4",
                "--stats", "1s",
                "--stats-one-line",
                "--stats-log-level", "NOTICE",
            ],
            on_output=lambda line: None,
            on_error=handle_stderr,
        )

        if ret == 0:
            on_log(f"目录上传成功: {dirname}")
            return True
        else:
            on_log(f"目录上传失败 (退出码 {ret}): {dirname}")
            return False

    def _download_directory(self, remote_dir: str, local_dir: str,
                            on_log: Callable[[str], None],
                            manager=None, task_id=None, item=None) -> bool:
        dirname = os.path.basename(local_dir)
        on_log(f"正在下载目录: {dirname} (rclone)")

        os.makedirs(local_dir, exist_ok=True)

        def handle_stderr(line: str):
            progress = RcloneProgressParser.parse_line(line)
            if progress and progress.percentage > 0:
                speed_str = progress.speed_human or ""
                on_log(f"下载进度: {progress.files_transferred}/{progress.files_total} 文件 - {progress.percentage:.0f}% ({speed_str})")
                if manager and task_id and item:
                    manager.update_task_progress(task_id, item, progress.percentage / 100.0, speed_str)
            elif line.strip() and "ERROR" in line.upper():
                on_log(f"[rclone] {line}")

        ret = self.rclone.execute(
            [
                "copy", remote_dir, local_dir,
                "--progress",
                "--transfers", "4",
                "--stats", "1s",
                "--stats-one-line",
                "--stats-log-level", "NOTICE",
            ],
            on_output=lambda line: None,
            on_error=handle_stderr,
        )

        if ret == 0:
            on_log(f"目录下载成功: {dirname}")
            return True
        else:
            on_log(f"目录下载失败 (退出码 {ret}): {dirname}")
            return False

    def cancel(self):
        self._cancelled = True
        self.rclone.cancel()
