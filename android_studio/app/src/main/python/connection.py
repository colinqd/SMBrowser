import socket
import threading
from typing import Optional, List, Callable
from smb.SMBConnection import SMBConnection
from smb.base import NotConnectedError

try:
    from smb.smb_exceptions import SMBException
except ImportError:
    SMBException = Exception


class SMBConnectionManager:
    def __init__(self):
        self.conn: Optional[SMBConnection] = None
        self.current_server_ip: str = ""
        self.current_share: str = ""
        self.available_shares: List[str] = []
        self.is_connected: bool = False
        self._lock = threading.Lock()

    def connect(
        self,
        server_ip: str,
        port: str,
        username: str,
        password: str,
        share_name: str,
        smb_version: str = "SMBv2"
    ) -> str:
        import json
        with self._lock:
            try:
                self.current_server_ip = server_ip
                port_num = int(port) if port and port.isdigit() else 445

                use_ntlm_v2 = smb_version in ("SMBv2", "SMBv3", "自动协商")

                socket.setdefaulttimeout(30)

                self.conn = SMBConnection(
                    username,
                    password,
                    "SMBClient",
                    server_ip,
                    use_ntlm_v2=use_ntlm_v2,
                    is_direct_tcp=True
                )

                connected = self.conn.connect(server_ip, port_num, timeout=30)

                if connected:
                    self.available_shares = [s.name for s in self.conn.listShares()]
                    self.is_connected = True
                    if share_name and share_name in self.available_shares:
                        self.current_share = share_name
                    return json.dumps([True, "连接成功"])
                else:
                    self.conn = None
                    return json.dumps([False, "连接失败: 服务器无响应"])

            except socket.timeout:
                self.conn = None
                return json.dumps([False, "连接超时: 请检查网络和服务器地址"])
            except socket.gaierror as e:
                self.conn = None
                return json.dumps([False, "DNS解析失败: 无法解析服务器地址"])
            except ConnectionRefusedError:
                self.conn = None
                return json.dumps([False, "连接被拒绝: 请检查端口是否正确"])
            except SMBException as e:
                self.conn = None
                return json.dumps([False, f"SMB错误: {str(e)}"])
            except Exception as e:
                self.conn = None
                return json.dumps([False, f"连接失败: {str(e)}"])
            finally:
                socket.setdefaulttimeout(None)

    def disconnect(self):
        with self._lock:
            if self.conn:
                try:
                    self.conn.close()
                except Exception as e:
                    print(f"关闭连接时出错: {str(e)}")
                self.conn = None
            self.is_connected = False
            self.current_share = ""
            self.available_shares = []

    def _normalize_path(self, path: str) -> str:
        if not path or path == "/":
            return "\\"
        path = path.replace("/", "\\")
        if not path.startswith("\\"):
            path = "\\" + path
        if not path.endswith("\\"):
            path = path + "\\"
        return path

    def _normalize_file_path(self, path: str) -> str:
        if not path or path == "/":
            return "\\"
        path = path.replace("/", "\\")
        if not path.startswith("\\"):
            path = "\\" + path
        return path

    def list_path(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接到服务器")
        
        smb_path = self._normalize_path(path)
        print(f"列出目录: share={share}, path={smb_path}")
        
        try:
            files = self.conn.listPath(share, smb_path + "*")
            print(f"listPath返回 {len(files) if files else 0} 个条目")
            return files
        except Exception as e:
            print(f"listPath错误: {e}")
            try:
                files = self.conn.listPath(share, smb_path)
                print(f"备用listPath返回 {len(files) if files else 0} 个条目")
                return files
            except Exception as e2:
                print(f"备用listPath也失败: {e2}")
                raise

    def create_directory(self, share: str, path: str) -> str:
        import json
        try:
            if not self.conn:
                return json.dumps([False, "未连接到服务器"])
            smb_path = self._normalize_file_path(path).rstrip("\\")
            self.conn.createDirectory(share, smb_path)
            return json.dumps([True, "目录创建成功"])
        except Exception as e:
            return json.dumps([False, f"创建目录失败: {str(e)}"])

    def delete_directory(self, share: str, path: str) -> str:
        import json
        try:
            if not self.conn:
                return json.dumps([False, "未连接到服务器"])
            smb_path = self._normalize_file_path(path).rstrip("\\")
            self.conn.deleteDirectory(share, smb_path)
            return json.dumps([True, "目录删除成功"])
        except Exception as e:
            return json.dumps([False, f"删除目录失败: {str(e)}"])

    def delete_file(self, share: str, path: str) -> str:
        import json
        try:
            if not self.conn:
                return json.dumps([False, "未连接到服务器"])
            smb_path = self._normalize_file_path(path)
            self.conn.deleteFiles(share, smb_path)
            return json.dumps([True, "文件删除成功"])
        except Exception as e:
            return json.dumps([False, f"删除文件失败: {str(e)}"])

    def rename(self, share: str, old_path: str, new_name: str) -> str:
        import json
        try:
            if not self.conn:
                return json.dumps([False, "未连接到服务器"])
            old_smb_path = self._normalize_file_path(old_path)
            parent_path = old_smb_path.rsplit("\\", 1)[0]
            new_smb_path = parent_path + "\\" + new_name
            self.conn.rename(share, old_smb_path, new_smb_path)
            return json.dumps([True, "重命名成功"])
        except Exception as e:
            return json.dumps([False, f"重命名失败: {str(e)}"])

    def copy_file(self, share: str, src_path: str, dst_path: str) -> str:
        import json
        try:
            if not self.conn:
                return json.dumps([False, "未连接到服务器"])
            src_smb = self._normalize_file_path(src_path)
            dst_smb = self._normalize_file_path(dst_path)
            
            with self.conn.retrieveFile(share, src_smb) as src_file:
                content = src_file.read()
            with self.conn.storeFile(share, dst_smb) as dst_file:
                dst_file.write(content)
            
            return json.dumps([True, "复制成功"])
        except Exception as e:
            return json.dumps([False, f"复制失败: {str(e)}"])

    def move_file(self, share: str, src_path: str, dst_path: str) -> str:
        import json
        try:
            if not self.conn:
                return json.dumps([False, "未连接到服务器"])
            src_smb = self._normalize_file_path(src_path)
            dst_smb = self._normalize_file_path(dst_path)
            self.conn.rename(share, src_smb, dst_smb)
            return json.dumps([True, "移动成功"])
        except Exception as e:
            return json.dumps([False, f"移动失败: {str(e)}"])

    def get_saved_connections(self) -> List[str]:
        from settings import Settings
        servers = Settings.load_servers()
        return list(servers.keys())
    
    def get_all_connections_json(self) -> str:
        from settings import Settings
        import json
        servers = Settings.load_servers()
        return json.dumps(servers)

    def save_connection(self, conn_data: dict):
        from settings import Settings
        servers = Settings.load_servers()
        name = conn_data.get('name', '')
        if name:
            servers[name] = {
                'server_ip': str(conn_data.get('server_ip', '')),
                'port': str(conn_data.get('port', '445')),
                'username': str(conn_data.get('username', '')),
                'password': str(conn_data.get('password', '')),
                'share_name': str(conn_data.get('share_name', '')),
            }
            Settings.save_servers(servers)

    def delete_connection(self, name: str) -> str:
        import json
        from settings import Settings
        try:
            servers = Settings.load_servers()
            if name in servers:
                del servers[name]
                Settings.save_servers(servers)
                return json.dumps([True, "连接已删除"])
            return json.dumps([False, "连接不存在"])
        except Exception as e:
            return json.dumps([False, f"删除失败: {str(e)}"])

    def get_connection(self, name: str) -> Optional[dict]:
        from settings import Settings
        servers = Settings.load_servers()
        conn_data = servers.get(name)
        if conn_data:
            return {
                'server_ip': str(conn_data.get('server_ip', '')),
                'port': str(conn_data.get('port', '445')),
                'username': str(conn_data.get('username', '')),
                'password': str(conn_data.get('password', '')),
                'share_name': str(conn_data.get('share_name', '')),
            }
        return None

    def get_available_shares_json(self) -> str:
        import json
        return json.dumps(self.available_shares)

    def set_current_share(self, share_name: str):
        if share_name in self.available_shares:
            self.current_share = share_name
            return True
        return False

    def download_file(self, share: str, remote_path: str, local_path: str) -> str:
        import json
        try:
            if not self.conn:
                return json.dumps([False, "未连接到服务器"])
            
            smb_path = self._normalize_file_path(remote_path)
            print(f"下载文件: share={share}, remote={smb_path}, local={local_path}")
            
            import os
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as local_file:
                self.conn.retrieveFile(share, smb_path, local_file)
            
            file_size = os.path.getsize(local_path)
            print(f"下载完成: {file_size} bytes")
            return json.dumps([True, f"下载成功 ({file_size} bytes)", local_path])
        except Exception as e:
            print(f"下载失败: {str(e)}")
            return json.dumps([False, f"下载失败: {str(e)}"])

    def download_file_resume(self, share: str, remote_path: str, local_path: str, start_offset: int = 0) -> str:
        import json
        try:
            if not self.conn:
                return json.dumps({"success": False, "message": "未连接到服务器"})
            
            smb_path = self._normalize_file_path(remote_path)
            print(f"断点续传下载: share={share}, remote={smb_path}, local={local_path}, offset={start_offset}")
            
            import os
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            file_info = self.conn.getAttributes(share, smb_path)
            total_size = file_info.file_size
            
            mode = 'ab' if start_offset > 0 else 'wb'
            with open(local_path, mode) as local_file:
                if start_offset > 0:
                    local_file.seek(start_offset)
                
                self.conn.retrieveFileFromOffset(share, smb_path, local_file, start_offset)
            
            final_size = os.path.getsize(local_path)
            print(f"下载完成: {final_size}/{total_size} bytes")
            
            return json.dumps({
                "success": True,
                "message": "下载成功",
                "total_bytes": total_size,
                "transferred_bytes": final_size
            })
        except Exception as e:
            print(f"断点续传失败: {str(e)}")
            return json.dumps({
                "success": False,
                "message": f"下载失败: {str(e)}",
                "transferred_bytes": start_offset
            })

    def upload_file(self, share: str, local_path: str, remote_path: str) -> str:
        import json
        try:
            if not self.conn:
                return json.dumps([False, "未连接到服务器"])
            
            import os
            if not os.path.exists(local_path):
                return json.dumps([False, "本地文件不存在"])
            
            smb_path = self._normalize_file_path(remote_path)
            print(f"上传文件: share={share}, local={local_path}, remote={smb_path}")
            
            file_size = os.path.getsize(local_path)
            
            with open(local_path, 'rb') as local_file:
                self.conn.storeFile(share, smb_path, local_file)
            
            print(f"上传完成: {file_size} bytes")
            return json.dumps([True, f"上传成功 ({file_size} bytes)"])
        except Exception as e:
            print(f"上传失败: {str(e)}")
            return json.dumps([False, f"上传失败: {str(e)}"])
