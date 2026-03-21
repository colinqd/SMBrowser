import socket
import threading
from typing import Optional, List, Callable
from smb.SMBConnection import SMBConnection
from smb.base import NotConnectedError


class SMBConnectionManager:
    def __init__(self):
        self.conn: Optional[SMBConnection] = None
        self.current_server_ip: str = ""
        self.current_share: str = ""
        self.available_shares: List[str] = []
        self.is_connected: bool = False

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
                    on_connected(share_name)
                else:
                    on_failed("连接失败")

            except Exception as e:
                on_failed(f"发生异常: {str(e)}")
            finally:
                socket.setdefaulttimeout(None)

        threading.Thread(target=connect_thread, daemon=True).start()

    def disconnect(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
        self.is_connected = False
        self.current_share = ""
        self.available_shares = []

    def list_path(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接")
        return self.conn.listPath(share, path)

    def create_directory(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接")
        self.conn.createDirectory(share, path)

    def delete_directory(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接")
        self.conn.deleteDirectory(share, path)

    def delete_files(self, share: str, path: str):
        if not self.conn:
            raise NotConnectedError("未连接")
        self.conn.deleteFiles(share, path)

    def store_file(self, share: str, path: str, file_obj):
        if not self.conn:
            raise NotConnectedError("未连接")
        self.conn.storeFile(share, path, file_obj)

    def retrieve_file(self, share: str, path: str, file_obj):
        if not self.conn:
            raise NotConnectedError("未连接")
        self.conn.retrieveFile(share, path, file_obj)
