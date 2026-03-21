import os
import threading
import shutil
from typing import Callable, List, Tuple
from smb.base import NotConnectedError


class FileOperations:
    def __init__(self, conn_manager):
        self.conn_manager = conn_manager

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
                        remote_path = os.path.join(remote_base, filename).replace("\\", "/")
                        with open(local_path, "rb") as f:
                            self.conn_manager.store_file(
                                self.conn_manager.current_share, remote_path, f
                            )
                        success_count += 1
                        on_log(f"上传成功: {filename}")
                    elif os.path.isdir(local_path):
                        self._upload_directory_recursive(local_path, remote_base, on_log)
                        success_count += 1
                except Exception as e:
                    on_error(filename, str(e))

            on_complete(success_count, total_files)

        threading.Thread(target=upload_thread, daemon=True).start()

    def _upload_directory_recursive(self, local_dir: str, remote_base: str, on_log: Callable[[str], None]):
        dir_name = os.path.basename(local_dir)
        remote_dir = os.path.join(remote_base, dir_name).replace("\\", "/")

        try:
            self.conn_manager.create_directory(self.conn_manager.current_share, remote_dir)
        except:
            pass

        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = os.path.join(remote_dir, item).replace("\\", "/")

            if os.path.isdir(local_path):
                self._upload_directory_recursive(local_path, remote_dir, on_log)
            else:
                with open(local_path, "rb") as f:
                    self.conn_manager.store_file(self.conn_manager.current_share, remote_path, f)

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
                        with open(local_path, "wb") as f:
                            self.conn_manager.retrieve_file(
                                self.conn_manager.current_share, remote_path, f
                            )
                        success_count += 1
                        on_log(f"下载成功: {filename}")
                    else:
                        self._download_directory_recursive(remote_path, local_path, on_log)
                        success_count += 1
                except Exception as e:
                    on_error(filename, str(e))

            on_complete(success_count, total_files)

        threading.Thread(target=download_thread, daemon=True).start()

    def _download_directory_recursive(self, remote_dir: str, local_base: str, on_log: Callable[[str], None]):
        if not os.path.exists(local_base):
            os.makedirs(local_base)

        try:
            items = self.conn_manager.list_path(self.conn_manager.current_share, remote_dir)
            for item in items:
                if item.filename in [".", ".."]:
                    continue

                remote_path = os.path.join(remote_dir, item.filename).replace("\\", "/")
                local_path = os.path.join(local_base, item.filename)

                if item.isDirectory:
                    self._download_directory_recursive(remote_path, local_path, on_log)
                else:
                    with open(local_path, "wb") as f:
                        self.conn_manager.retrieve_file(self.conn_manager.current_share, remote_path, f)
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
                        self.conn_manager.delete_files(self.conn_manager.current_share, full_path)
                    success_count += 1
                    on_log(f"已删除: {full_path}")
                except Exception as e:
                    on_error(item_name, str(e))

            on_complete(success_count)

        threading.Thread(target=delete_thread, daemon=True).start()

    def _delete_remote_directory_recursive(self, path: str, on_log: Callable[[str], None]):
        try:
            contents = self.conn_manager.list_path(self.conn_manager.current_share, path)
            for file in contents:
                if file.filename in ['.', '..']:
                    continue

                item_path = os.path.join(path, file.filename).replace("\\", "/")
                if file.isDirectory:
                    self._delete_remote_directory_recursive(item_path, on_log)
                else:
                    self.conn_manager.delete_files(self.conn_manager.current_share, item_path)

            self.conn_manager.delete_directory(self.conn_manager.current_share, path)
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
