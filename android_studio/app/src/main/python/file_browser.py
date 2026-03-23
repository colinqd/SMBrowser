from typing import Optional, List, Dict, Any
from connection import SMBConnectionManager
import json
import datetime


class FileBrowser:
    def __init__(self):
        self.conn_manager: Optional[SMBConnectionManager] = None
        self.current_path: str = "/"
        self.current_files: List[Dict[str, Any]] = []
        self.clipboard: Dict[str, Any] = {}

    def set_connection(self, conn_manager: SMBConnectionManager):
        self.conn_manager = conn_manager
    
    def _format_size(self, size: int) -> str:
        try:
            size = int(size)
        except:
            return ""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def _format_time(self, timestamp: float) -> str:
        try:
            if timestamp <= 0:
                return ""
            dt = datetime.datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return ""

    def load_path(self, path: str):
        if not self.conn_manager:
            print("错误: 连接管理器未设置")
            return []
        
        if not self.conn_manager.conn:
            print("错误: SMB连接未建立")
            return []

        self.current_path = path
        try:
            print(f"正在加载目录: {path}, 共享: {self.conn_manager.current_share}")
            files = self.conn_manager.list_path(
                self.conn_manager.current_share,
                path
            )
            print(f"获取到 {len(files) if files else 0} 个文件/目录")
            
            self.current_files = []
            if files:
                for f in files:
                    try:
                        filename = str(f.filename) if f.filename else ""
                        if filename in (".", ".."):
                            continue
                        
                        is_dir = bool(f.isDirectory)
                        file_size = int(f.file_size) if hasattr(f, 'file_size') else 0
                        size_str = self._format_size(file_size) if not is_dir else ""
                        
                        last_write_time = 0
                        if hasattr(f, 'last_write_time'):
                            try:
                                last_write_time = float(f.last_write_time)
                            except:
                                pass
                        time_str = self._format_time(last_write_time)
                        
                        self.current_files.append({
                            'filename': filename,
                            'isDirectory': is_dir,
                            'file_size': file_size,
                            'file_size_str': size_str,
                            'create_time': float(f.create_time) if hasattr(f, 'create_time') else 0,
                            'last_write_time': last_write_time,
                            'last_write_time_str': time_str,
                        })
                    except Exception as e:
                        print(f"处理文件条目失败: {e}")
                        continue
            
            self.current_files.sort(key=lambda x: (not x['isDirectory'], x['filename'].lower()))
            print(f"成功加载 {len(self.current_files)} 个文件/目录")
            return self.current_files
            
        except Exception as e:
            print(f"加载目录失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_current_files_json(self) -> str:
        return json.dumps(self.current_files, ensure_ascii=False)
    
    def get_current_path(self) -> str:
        return str(self.current_path)

    def navigate_up(self):
        if self.current_path == "/":
            return "/"
        parts = self.current_path.strip("/").split("/")
        if len(parts) <= 1:
            self.current_path = "/"
        else:
            self.current_path = "/" + "/".join(parts[:-1])
        return self.load_path(self.current_path)

    def navigate_to(self, path: str):
        return self.load_path(path)

    def refresh(self):
        return self.load_path(self.current_path)

    def get_current_files(self) -> List[Dict[str, Any]]:
        return self.current_files

    def is_connected(self) -> bool:
        return (
            self.conn_manager is not None
            and self.conn_manager.conn is not None
            and self.conn_manager.is_connected
        )

    def get_full_path(self, filename: str) -> str:
        if self.current_path == "/":
            return "/" + filename
        return self.current_path + "/" + filename

    def create_directory(self, dir_name: str) -> str:
        if not self.conn_manager:
            return json.dumps([False, "未连接"])
        full_path = self.get_full_path(dir_name)
        return self.conn_manager.create_directory(
            self.conn_manager.current_share,
            full_path
        )

    def delete_item(self, filename: str, is_dir: bool) -> str:
        if not self.conn_manager:
            return json.dumps([False, "未连接"])
        full_path = self.get_full_path(filename)
        if is_dir:
            return self.conn_manager.delete_directory(
                self.conn_manager.current_share,
                full_path
            )
        else:
            return self.conn_manager.delete_file(
                self.conn_manager.current_share,
                full_path
            )

    def rename_item(self, old_name: str, new_name: str) -> str:
        if not self.conn_manager:
            return json.dumps([False, "未连接"])
        full_path = self.get_full_path(old_name)
        return self.conn_manager.rename(
            self.conn_manager.current_share,
            full_path,
            new_name
        )

    def copy_to_clipboard(self, filename: str, is_dir: bool) -> str:
        full_path = self.get_full_path(filename)
        self.clipboard = {
            'operation': 'copy',
            'filename': filename,
            'path': full_path,
            'is_dir': is_dir,
            'share': self.conn_manager.current_share if self.conn_manager else ''
        }
        return json.dumps([True, f"已复制 {filename} 到剪贴板"])

    def cut_to_clipboard(self, filename: str, is_dir: bool) -> str:
        full_path = self.get_full_path(filename)
        self.clipboard = {
            'operation': 'cut',
            'filename': filename,
            'path': full_path,
            'is_dir': is_dir,
            'share': self.conn_manager.current_share if self.conn_manager else ''
        }
        return json.dumps([True, f"已剪切 {filename} 到剪贴板"])

    def paste_from_clipboard(self) -> str:
        if not self.clipboard:
            return json.dumps([False, "剪贴板为空"])
        
        if not self.conn_manager:
            return json.dumps([False, "未连接"])
        
        operation = self.clipboard.get('operation', '')
        src_path = self.clipboard.get('path', '')
        filename = self.clipboard.get('filename', '')
        src_share = self.clipboard.get('share', '')
        
        if src_share != self.conn_manager.current_share:
            return json.dumps([False, "不支持跨共享操作"])
        
        dst_path = self.get_full_path(filename)
        
        if src_path == dst_path:
            return json.dumps([False, "源和目标相同"])
        
        if operation == 'copy':
            result = self.conn_manager.copy_file(
                self.conn_manager.current_share,
                src_path,
                dst_path
            )
        elif operation == 'cut':
            result = self.conn_manager.move_file(
                self.conn_manager.current_share,
                src_path,
                dst_path
            )
            if json.loads(result)[0]:
                self.clipboard = {}
        else:
            return json.dumps([False, "未知操作"])
        
        return result

    def has_clipboard(self) -> bool:
        return bool(self.clipboard)

    def get_clipboard_info(self) -> str:
        return json.dumps(self.clipboard, ensure_ascii=False)

    def clear_clipboard(self):
        self.clipboard = {}

    def download_file(self, filename: str, local_dir: str) -> str:
        if not self.conn_manager:
            return json.dumps([False, "未连接"])
        
        full_path = self.get_full_path(filename)
        local_path = local_dir.rstrip("/\\") + "/" + filename
        
        return self.conn_manager.download_file(
            self.conn_manager.current_share,
            full_path,
            local_path
        )

    def download_file_resume(self, filename: str, local_path: str, start_offset: int = 0) -> str:
        if not self.conn_manager:
            return json.dumps({"success": False, "message": "未连接"})
        
        full_path = self.get_full_path(filename)
        
        return self.conn_manager.download_file_resume(
            self.conn_manager.current_share,
            full_path,
            local_path,
            start_offset
        )

    def upload_file(self, filename: str, local_path: str) -> str:
        if not self.conn_manager:
            return json.dumps([False, "未连接"])
        
        remote_path = self.get_full_path(filename)
        
        return self.conn_manager.upload_file(
            self.conn_manager.current_share,
            local_path,
            remote_path
        )
