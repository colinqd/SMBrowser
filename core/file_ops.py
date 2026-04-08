import os
import threading
import shutil
import time
from typing import Callable, List, Tuple
from smb.base import NotConnectedError


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

    def upload_files_async(
        self,
        local_files: List[Tuple[str, str]],
        remote_base: str,
        on_progress: Callable[[str, int, int], None],
        on_complete: Callable[[int, int], None],
        on_error: Callable[[str, str], None],
        on_log: Callable[[str], None]
    ):
        def upload_thread():
            success_count = 0
            total_files = len(local_files)

            for i, (filename, local_path) in enumerate(local_files):
                on_progress(filename, i + 1, total_files)

                try:
                    if os.path.isfile(local_path):
                        remote_path = self._normalize_remote_path(
                            remote_base.rstrip("/") + "/" + filename
                        )
                        
                        if self._upload_file_with_retry(local_path, remote_path, on_log):
                            success_count += 1
                            on_log(f"上传成功: {filename}")
                        
                    elif os.path.isdir(local_path):
                        self._upload_directory_recursive(local_path, remote_base, on_log)
                        success_count += 1
                except Exception as e:
                    on_error(filename, str(e))

            on_complete(success_count, total_files)

        threading.Thread(target=upload_thread, daemon=True).start()

    def _upload_file_with_retry(self, local_path: str, remote_path: str, on_log: Callable[[str], None]) -> bool:
        local_file_size = os.path.getsize(local_path)
        
        for attempt in range(self._retry_count):
            try:
                remote_file_info = self.conn_manager.get_file_info(
                    self.conn_manager.current_share, remote_path
                )
                
                if remote_file_info and not remote_file_info['is_directory']:
                    if remote_file_info['size'] >= local_file_size:
                        on_log(f"跳过（已存在且完整）: {os.path.basename(local_path)}")
                        return True
                    on_log(f"文件已存在但大小不同，将覆盖: {os.path.basename(local_path)}")
                
                with open(local_path, "rb") as f:
                    self.conn_manager.store_file(
                        self.conn_manager.current_share, remote_path, f
                    )
                return True
                
            except Exception as e:
                error_msg = str(e)
                if "unpack requires a buffer" in error_msg:
                    on_log(f"服务器协议错误，尝试重试: {os.path.basename(local_path)}")
                    time.sleep(self._retry_delay)
                    continue
                if attempt < self._retry_count - 1:
                    on_log(f"上传失败，重试中 ({attempt + 1}/{self._retry_count}): {os.path.basename(local_path)}")
                    time.sleep(self._retry_delay)
                else:
                    raise
        
        return False

    def _upload_directory_recursive(self, local_dir: str, remote_base: str, on_log: Callable[[str], None]):
        dir_name = os.path.basename(local_dir)
        remote_dir = self._normalize_remote_path(remote_base.rstrip("/") + "/" + dir_name)

        try:
            self.conn_manager.create_directory(self.conn_manager.current_share, remote_dir)
        except:
            pass

        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = self._normalize_remote_path(remote_dir + "/" + item)

            if os.path.isdir(local_path):
                self._upload_directory_recursive(local_path, remote_dir, on_log)
            else:
                try:
                    self._upload_file_with_retry(local_path, remote_path, on_log)
                except Exception as e:
                    on_log(f"上传失败: {item} - {str(e)}")

    def download_files_async(
        self,
        remote_files: List[Tuple[str, str, str, bool]],
        local_base: str,
        on_progress: Callable[[str, int, int], None],
        on_complete: Callable[[int, int], None],
        on_error: Callable[[str, str], None],
        on_log: Callable[[str], None]
    ):
        def download_thread():
            success_count = 0
            total_files = len(remote_files)

            for i, (filename, remote_path, local_path, is_dir) in enumerate(remote_files):
                on_progress(filename, i + 1, total_files)

                try:
                    if not is_dir:
                        if self._download_file_with_retry(remote_path, local_path, on_log):
                            success_count += 1
                            on_log(f"下载成功: {filename}")
                    else:
                        self._download_directory_recursive(remote_path, local_path, on_log)
                        success_count += 1
                except Exception as e:
                    on_error(filename, str(e))

            on_complete(success_count, total_files)

        threading.Thread(target=download_thread, daemon=True).start()

    def _download_file_with_retry(self, remote_path: str, local_path: str, on_log: Callable[[str], None]) -> bool:
        remote_path_normalized = self._normalize_remote_path(remote_path)
        
        for attempt in range(self._retry_count):
            try:
                remote_file_info = self.conn_manager.get_file_info(
                    self.conn_manager.current_share, remote_path_normalized
                )
                
                if os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    if remote_file_info and local_size >= remote_file_info['size']:
                        on_log(f"跳过（已存在且完整）: {os.path.basename(local_path)}")
                        return True
                    if remote_file_info and local_size > 0 and local_size < remote_file_info['size']:
                        on_log(f"断点续传: {os.path.basename(local_path)} (从 {local_size} 字节开始)")
                        with open(local_path, "ab") as f:
                            self.conn_manager.retrieve_file(
                                self.conn_manager.current_share, remote_path_normalized, f
                            )
                        return True
                
                with open(local_path, "wb") as f:
                    self.conn_manager.retrieve_file(
                        self.conn_manager.current_share, remote_path_normalized, f
                    )
                return True
                
            except Exception as e:
                error_msg = str(e)
                if "unpack requires a buffer" in error_msg:
                    on_log(f"服务器协议错误，尝试重试: {os.path.basename(local_path)}")
                    time.sleep(self._retry_delay)
                    continue
                if attempt < self._retry_count - 1:
                    on_log(f"下载失败，重试中 ({attempt + 1}/{self._retry_count}): {os.path.basename(local_path)}")
                    time.sleep(self._retry_delay)
                else:
                    raise
        
        return False

    def _download_directory_recursive(self, remote_dir: str, local_base: str, on_log: Callable[[str], None]):
        if not os.path.exists(local_base):
            os.makedirs(local_base)

        try:
            remote_dir_normalized = self._normalize_remote_path(remote_dir)
            items = self.conn_manager.list_path(self.conn_manager.current_share, remote_dir_normalized)
            for item in items:
                if item.filename in [".", ".."]:
                    continue

                remote_path = self._normalize_remote_path(remote_dir + "/" + item.filename)
                local_path = os.path.join(local_base, item.filename)

                if item.isDirectory:
                    self._download_directory_recursive(remote_path, local_path, on_log)
                else:
                    try:
                        self._download_file_with_retry(remote_path, local_path, on_log)
                    except Exception as e:
                        on_log(f"下载失败: {item.filename} - {str(e)}")
        except Exception as e:
            on_log(f"下载目录失败: {remote_dir} - {str(e)}")

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
