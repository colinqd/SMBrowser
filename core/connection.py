import socket
import threading
import time
from typing import Optional, List, Callable
from smb.SMBConnection import SMBConnection
from smb.base import NotConnectedError
from smb.smb_structs import UnsupportedFeature


class SMBConnectionManager:
    def __init__(self):
        self.conn: Optional[SMBConnection] = None
        self.transfer_conn: Optional[SMBConnection] = None
        self.current_server_ip: str = ""
        self.current_share: str = ""
        self.available_shares: List[str] = []
        self.is_connected: bool = False
        self._retry_count = 3
        self._retry_delay = 1
        self._last_connect_params = None

    def connect_async(
        self,
        server_ip: str,
        port: str,
        username: str,
        password: str,
        share_name: str,
        smb_version_choice: str,
        on_connected: Callable[[str], None],
        on_failed: Callable[[str], None]
    ):
        self.current_server_ip = server_ip
        self._last_connect_params = {
            'server_ip': server_ip,
            'port': port,
            'username': username,
            'password': password,
            'smb_version_choice': smb_version_choice
        }

        def connect_thread():
            try:
                port_num = int(port) if port and port.isdigit() else 445

                use_ntlm_v2 = {
                    "SMBv1": False,
                    "SMBv2": True,
                    "SMBv3": True,
                    "自动协商": True
                }.get(smb_version_choice, True)

                socket.setdefaulttimeout(30)

                self.conn = SMBConnection(
                    username,
                    password,
                    "SMBClient_Browse",
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
                    
                    try:
                        self.transfer_conn = SMBConnection(
                            username,
                            password,
                            "SMBClient_Transfer",
                            server_ip,
                            use_ntlm_v2=use_ntlm_v2,
                            is_direct_tcp=True
                        )
                        self.transfer_conn.connect(server_ip, port_num, timeout=30)
                    except Exception as e:
                        pass
                    
                    on_connected(share_name)
                else:
                    on_failed("连接失败")

            except Exception as e:
                on_failed(f"发生异常: {str(e)}")
            finally:
                socket.setdefaulttimeout(None)

        threading.Thread(target=connect_thread, daemon=True).start()

    def _ensure_transfer_conn(self):
        if not self.transfer_conn and self._last_connect_params:
            try:
                port_num = int(self._last_connect_params['port']) if self._last_connect_params['port'] and self._last_connect_params['port'].isdigit() else 445
                
                use_ntlm_v2 = {
                    "SMBv1": False,
                    "SMBv2": True,
                    "SMBv3": True,
                    "自动协商": True
                }.get(self._last_connect_params['smb_version_choice'], True)

                self.transfer_conn = SMBConnection(
                    self._last_connect_params['username'],
                    self._last_connect_params['password'],
                    "SMBClient_Transfer",
                    self._last_connect_params['server_ip'],
                    use_ntlm_v2=use_ntlm_v2,
                    is_direct_tcp=True
                )
                self.transfer_conn.connect(self._last_connect_params['server_ip'], port_num, timeout=30)
            except Exception as e:
                pass

    def disconnect(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
        
        if self.transfer_conn:
            try:
                self.transfer_conn.close()
            except:
                pass
            self.transfer_conn = None
        
        self.is_connected = False
        self.current_share = ""
        self.available_shares = []

    def _execute_with_retry(self, operation, *args, **kwargs):
        last_error = None
        for attempt in range(self._retry_count):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_msg = str(e)
                if "unpack requires a buffer" in error_msg:
                    raise
                if attempt < self._retry_count - 1:
                    time.sleep(self._retry_delay)
        raise last_error

    def list_path(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接")
        
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        
        def _list():
            return self.conn.listPath(share, path)
        
        try:
            return self._execute_with_retry(_list)
        except Exception as e:
            error_msg = str(e)
            if "unpack requires a buffer" in error_msg:
                try:
                    if path == "/" or path == "":
                        return self.conn.listPath(share, "/*")
                    search_pattern = path.rstrip("/") + "/*"
                    return self.conn.listPath(share, search_pattern)
                except Exception as e2:
                    try:
                        parent_path = "/".join(path.rstrip("/").split("/")[:-1]) or "/"
                        return self.conn.listPath(share, parent_path.rstrip("/") + "/*")
                    except:
                        pass
                    raise e2
            raise

    def list_directory(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接")
        
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        
        search_pattern = path.rstrip("/") + "/*"
        
        def _list():
            return self.conn.listPath(share, search_pattern)
        
        try:
            return self._execute_with_retry(_list)
        except Exception as e:
            error_msg = str(e)
            if "unpack requires a buffer" in error_msg:
                try:
                    parent_path = "/".join(path.rstrip("/").split("/")[:-1]) or "/"
                    results = self.conn.listPath(share, parent_path.rstrip("/") + "/*")
                    dir_name = path.rstrip("/").split("/")[-1] if path != "/" else ""
                    if dir_name:
                        for item in results:
                            if item.filename == dir_name and item.isDirectory:
                                return self.conn.listPath(share, search_pattern)
                    return results
                except:
                    pass
            raise

    def get_file_info(self, share: str, path: str) -> Optional[dict]:
        if not self.conn:
            raise NotConnectedError("未连接")
        
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        
        try:
            parent_path = "/".join(path.rstrip("/").split("/")[:-1]) or "/"
            filename = path.rstrip("/").split("/")[-1]
            
            results = self.list_path(share, parent_path)
            for f in results:
                if f.filename == filename:
                    return {
                        'filename': f.filename,
                        'size': f.file_size,
                        'is_directory': f.isDirectory,
                        'last_write_time': f.last_write_time
                    }
            return None
        except:
            return None

    def create_directory(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接")
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        
        def _create():
            self.conn.createDirectory(share, path)
        
        self._execute_with_retry(_create)

    def delete_directory(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接")
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        
        def _delete():
            self.conn.deleteDirectory(share, path)
        
        self._execute_with_retry(_delete)

    def delete_files(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接")
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        
        def _delete():
            self.conn.deleteFiles(share, path)
        
        self._execute_with_retry(_delete)

    def store_file(self, share: str, path: str, file_obj):
        self._ensure_transfer_conn()
        if not self.transfer_conn:
            raise NotConnectedError("传输连接未连接")
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        
        def _store():
            self.transfer_conn.storeFile(share, path, file_obj)
        
        try:
            return self._execute_with_retry(_store)
        except Exception as e:
            if self.transfer_conn:
                try:
                    self.transfer_conn.close()
                except:
                    pass
                self.transfer_conn = None
            raise

    def retrieve_file(self, share: str, path: str, file_obj):
        self._ensure_transfer_conn()
        if not self.transfer_conn:
            raise NotConnectedError("传输连接未连接")
        path = path.replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        
        def _retrieve():
            return self.transfer_conn.retrieveFile(share, path, file_obj)
        
        try:
            return self._execute_with_retry(_retrieve)
        except Exception as e:
            if self.transfer_conn:
                try:
                    self.transfer_conn.close()
                except:
                    pass
                self.transfer_conn = None
            raise
