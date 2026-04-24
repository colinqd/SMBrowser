import os
import threading
import shutil
import time
from typing import Callable, List, Tuple
from smb.base import NotConnectedError


def format_speed(bytes_per_sec):
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.1f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"


class ProgressFileWrapper:
    CHUNK_SIZE = 65536

    def __init__(self, file_obj, total_size, filename,
                 manager=None, task_id=None, item=None):
        self.file_obj = file_obj
        self.total_size = total_size
        self.filename = filename
        self.manager = manager
        self.task_id = task_id
        self.item = item
        self.bytes_read = 0
        self.last_reported_time = 0
        self.last_reported_percent = -1
        self.start_time = time.time()
        if manager and task_id and item:
            manager.update_item_size(task_id, item, total_size)

    def read(self, size=-1):
        if size < 0:
            size = self.CHUNK_SIZE
        data = self.file_obj.read(size)
        self.bytes_read += len(data)
        now = time.time()
        if self.total_size > 0:
            percent = int((self.bytes_read / self.total_size) * 100)
            time_elapsed = now - self.last_reported_time
            if (percent != self.last_reported_percent and time_elapsed >= 0.15) or percent >= 100:
                elapsed = now - self.start_time
                speed = self.bytes_read / elapsed if elapsed > 0 else 0
                speed_str = format_speed(speed)
                if self.manager and self.task_id and self.item:
                    self.manager.update_task_progress(
                        self.task_id, self.item, percent / 100.0,
                        speed_str, self.bytes_read, speed
                    )
                self.last_reported_percent = percent
                self.last_reported_time = now
        return data

    def close(self):
        self.file_obj.close()


class ProgressWriteFileWrapper:
    def __init__(self, file_obj, total_size, filename, start_offset=0,
                 manager=None, task_id=None, item=None):
        self.file_obj = file_obj
        self.total_size = total_size
        self.filename = filename
        self.start_offset = start_offset
        self.manager = manager
        self.task_id = task_id
        self.item = item
        self.bytes_written = 0
        self.last_reported_time = 0
        self.last_reported_percent = -1
        self.start_time = time.time()
        if manager and task_id and item:
            manager.update_item_size(task_id, item, total_size)

    def write(self, data):
        self.file_obj.write(data)
        self.bytes_written += len(data)
        now = time.time()
        if self.total_size > 0:
            total = self.start_offset + self.bytes_written
            percent = int((total / self.total_size) * 100)
            time_elapsed = now - self.last_reported_time
            if (percent != self.last_reported_percent and time_elapsed >= 0.15) or percent >= 100:
                elapsed = now - self.start_time
                speed = self.bytes_written / elapsed if elapsed > 0 else 0
                speed_str = format_speed(speed)
                if self.manager and self.task_id and self.item:
                    self.manager.update_task_progress(
                        self.task_id, self.item, percent / 100.0,
                        speed_str, total, speed
                    )
                self.last_reported_percent = percent
                self.last_reported_time = now

    def close(self):
        self.file_obj.close()


class FileOperations:
    def __init__(self, conn_manager):
        self.conn_manager = conn_manager
        self._retry_count = 3
        self._retry_delay = 1

    def _normalize_remote_path(self, path: str) -> str:
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        return path

    def enumerate_local_dir(self, local_dir: str, base_dir: str = None) -> List[Tuple[str, str, bool]]:
        if base_dir is None:
            base_dir = local_dir
        result = []
        try:
            for entry in os.listdir(local_dir):
                full_path = os.path.join(local_dir, entry)
                rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
                if os.path.isdir(full_path):
                    result.append((rel_path, full_path, True))
                    result.extend(self.enumerate_local_dir(full_path, base_dir))
                else:
                    result.append((rel_path, full_path, False))
        except Exception:
            pass
        return result

    def enumerate_remote_dir(self, remote_dir: str, base_dir: str = None) -> List[Tuple[str, str, bool]]:
        if base_dir is None:
            base_dir = remote_dir
        result = []
        try:
            remote_dir_norm = self._normalize_remote_path(remote_dir)
            items = self.conn_manager.list_path(self.conn_manager.current_share, remote_dir_norm)
            for item in items:
                if item.filename in [".", ".."]:
                    continue
                # 计算相对于 base_dir 的路径，而不是包含 base_dir 的完整路径
                # 例如：base_dir="/a/v", remote_dir="/a/v" -> rel_path="c.txt"
                # 例如：base_dir="/a/v", remote_dir="/a/v/sub" -> rel_path="sub/c.txt"
                if remote_dir == base_dir or remote_dir == base_dir.rstrip("/"):
                    rel_path = item.filename
                else:
                    rel_dir = remote_dir[len(base_dir.rstrip("/")):].lstrip("/")
                    rel_path = (rel_dir + "/" + item.filename) if rel_dir else item.filename
                remote_path = self._normalize_remote_path(remote_dir + "/" + item.filename)
                if item.isDirectory:
                    result.append((rel_path, remote_path, True))
                    result.extend(self.enumerate_remote_dir(remote_path, base_dir))
                else:
                    result.append((rel_path, remote_path, False))
        except Exception:
            pass
        return result

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
        def upload_thread():
            success_count = 0
            total_files = len(local_files)

            task = manager.get_task(task_id) if manager and task_id else None
            items = task.items if task else []

            for i, (filename, local_path, is_dir) in enumerate(local_files):
                item = items[i] if task and i < len(items) else None
                on_progress(filename, i + 1, total_files)

                try:
                    if is_dir:
                        remote_dir = self._normalize_remote_path(
                            remote_base.rstrip("/") + "/" + filename
                        )
                        try:
                            self.conn_manager.create_directory(
                                self.conn_manager.current_share, remote_dir
                            )
                        except Exception:
                            pass
                        if item and manager:
                            manager.update_task_status(task_id, item, "completed")
                        success_count += 1
                    else:
                        remote_path = self._normalize_remote_path(
                            remote_base.rstrip("/") + "/" + filename
                        )
                        remote_dir = self._normalize_remote_path(
                            "/".join(remote_path.split("/")[:-1])
                        )
                        try:
                            self.conn_manager.create_directory(
                                self.conn_manager.current_share, remote_dir
                            )
                        except Exception:
                            pass

                        if item and manager:
                            local_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
                            if local_size > 0:
                                manager.update_item_size(task_id, item, local_size)
                            manager.update_task_status(task_id, item, "running")

                        if self._upload_file_with_retry(local_path, remote_path, manager, task_id, item):
                            success_count += 1
                            if item and manager:
                                manager.update_task_status(task_id, item, "completed")
                        else:
                            if item and manager:
                                manager.update_task_status(task_id, item, "failed", "上传失败")

                except Exception as e:
                    on_error(filename, str(e))
                    if item and manager:
                        manager.update_task_status(task_id, item, "failed", str(e))

            on_complete(success_count, total_files)

        threading.Thread(target=upload_thread, daemon=True).start()

    def _upload_file_with_retry(self, local_path: str, remote_path: str,
                                 manager=None, task_id=None, item=None) -> bool:
        local_file_size = os.path.getsize(local_path)
        filename = os.path.basename(local_path)

        for attempt in range(self._retry_count):
            try:
                remote_file_info = self.conn_manager.get_file_info(
                    self.conn_manager.current_share, remote_path
                )

                if remote_file_info and not remote_file_info['is_directory']:
                    if remote_file_info['size'] >= local_file_size:
                        if item and manager:
                            manager.update_task_status(task_id, item, "completed")
                        return True

                with open(local_path, "rb") as f:
                    progress_file = ProgressFileWrapper(f, local_file_size, filename,
                                                        manager, task_id, item)
                    self.conn_manager.store_file(
                        self.conn_manager.current_share, remote_path, progress_file
                    )
                return True

            except Exception as e:
                error_msg = str(e)
                if "unpack requires a buffer" in error_msg:
                    time.sleep(self._retry_delay)
                    continue
                if attempt < self._retry_count - 1:
                    time.sleep(self._retry_delay)
                else:
                    raise

        return False

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
        def download_thread():
            success_count = 0
            total_files = len(remote_files)

            task = manager.get_task(task_id) if manager and task_id else None
            items = task.items if task else []

            for i, (filename, remote_path, local_path, is_dir) in enumerate(remote_files):
                item = items[i] if task and i < len(items) else None
                on_progress(filename, i + 1, total_files)

                try:
                    if is_dir:
                        # 只创建相对于 local_base 的目录层级，不创建 local_base 之上的目录
                        # local_path 格式应该是 local_base/dir_name 或 local_base/dir_name/subdir
                        # 不应该创建 local_base 之上的任何目录
                        os.makedirs(local_path, exist_ok=True)
                        if item and manager:
                            manager.update_task_status(task_id, item, "completed")
                        success_count += 1
                    else:
                        # 对于文件，只创建 local_base 之下的目录结构
                        local_parent_dir = os.path.dirname(local_path)
                        if local_parent_dir:
                            # 确保只创建 local_base 之下的目录
                            if not os.path.exists(local_parent_dir):
                                os.makedirs(local_parent_dir, exist_ok=True)
                        if item and manager:
                            manager.update_task_status(task_id, item, "running")
                        if self._download_file_with_retry(remote_path, local_path, manager, task_id, item):
                            success_count += 1
                            if item and manager:
                                manager.update_task_status(task_id, item, "completed")
                        else:
                            if item and manager:
                                manager.update_task_status(task_id, item, "failed", "下载失败")

                except Exception as e:
                    on_error(filename, str(e))
                    if item and manager:
                        manager.update_task_status(task_id, item, "failed", str(e))

            on_complete(success_count, total_files)

        threading.Thread(target=download_thread, daemon=True).start()

    def _download_file_with_retry(self, remote_path: str, local_path: str,
                                   manager=None, task_id=None, item=None) -> bool:
        remote_path_normalized = self._normalize_remote_path(remote_path)
        filename = os.path.basename(local_path)

        for attempt in range(self._retry_count):
            try:
                remote_file_info = self.conn_manager.get_file_info(
                    self.conn_manager.current_share, remote_path_normalized
                )

                if not remote_file_info:
                    return False

                file_size = remote_file_info['size']

                if os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    if local_size >= file_size:
                        if item and manager:
                            manager.update_item_size(task_id, item, file_size)
                            manager.update_task_status(task_id, item, "completed")
                        return True
                    if local_size > 0 and local_size < file_size:
                        with open(local_path, "ab") as f:
                            progress_file = ProgressWriteFileWrapper(
                                f, file_size, filename, local_size,
                                manager, task_id, item
                            )
                            self.conn_manager.retrieve_file(
                                self.conn_manager.current_share, remote_path_normalized, progress_file
                            )
                        return True

                with open(local_path, "wb") as f:
                    progress_file = ProgressWriteFileWrapper(
                        f, file_size, filename,
                        manager=manager, task_id=task_id, item=item
                    )
                    self.conn_manager.retrieve_file(
                        self.conn_manager.current_share, remote_path_normalized, progress_file
                    )
                return True

            except Exception as e:
                error_msg = str(e)
                if "unpack requires a buffer" in error_msg:
                    time.sleep(self._retry_delay)
                    continue
                if attempt < self._retry_count - 1:
                    time.sleep(self._retry_delay)
                else:
                    raise

        return False

    def delete_remote_items_async(
        self,
        items: List[Tuple[str, str, bool]],
        on_complete: Callable[[int], None],
        on_error: Callable[[str, str], None],
        on_log: Callable[[str], None]
    ):
        def delete_thread():
            success_count = 0

            for item_name, full_path, is_dir in items:
                try:
                    if is_dir:
                        self._delete_remote_directory_recursive(full_path, on_log)
                    else:
                        normalized_path = self._normalize_remote_path(full_path)
                        self.conn_manager.delete_files(self.conn_manager.current_share, normalized_path)
                    success_count += 1
                    on_log(f"已删除: {full_path}")
                except Exception as e:
                    on_error(item_name, str(e))

            on_complete(success_count)

        threading.Thread(target=delete_thread, daemon=True).start()

    def _delete_remote_directory_recursive(self, path: str, on_log: Callable[[str], None]):
        try:
            normalized_path = self._normalize_remote_path(path)
            contents = self.conn_manager.list_path(self.conn_manager.current_share, normalized_path)
            for file in contents:
                if file.filename in ['.', '..']:
                    continue

                item_path = self._normalize_remote_path(path + "/" + file.filename)
                if file.isDirectory:
                    self._delete_remote_directory_recursive(item_path, on_log)
                else:
                    self.conn_manager.delete_files(self.conn_manager.current_share, item_path)

            self.conn_manager.delete_directory(self.conn_manager.current_share, normalized_path)
        except Exception as e:
            on_log(f"删除目录失败: {path} - {str(e)}")
            raise

    def delete_local_items_async(
        self,
        items: List[Tuple[str, str, bool]],
        on_complete: Callable[[int], None],
        on_error: Callable[[str, str], None],
        on_log: Callable[[str], None]
    ):
        def delete_thread():
            success_count = 0

            for item_name, full_path, is_dir in items:
                try:
                    if os.path.exists(full_path):
                        if is_dir:
                            shutil.rmtree(full_path)
                        else:
                            os.remove(full_path)
                        success_count += 1
                        on_log(f"已删除: {full_path}")
                except Exception as e:
                    on_error(item_name, str(e))

            on_complete(success_count)

        threading.Thread(target=delete_thread, daemon=True).start()
