import json
import os
from smb.SMBConnection import SMBConnection
from typing import Optional, Dict, List


class SMBConnectionManager:
    def __init__(self):
        self.conn: Optional[SMBConnection] = None
        self.current_share: str = ""
        self.current_path: str = "/"
        self.connections: Dict = self._load_connections()
    
    def _load_connections(self) -> Dict:
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_connections(self):
        config_path = self._get_config_path()
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.connections, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _get_config_path(self) -> str:
        if os.name == 'posix':
            if 'ANDROID_ARGUMENT' in os.environ:
                from jnius import autoclass
                Environment = autoclass('android.os.Environment')
                storage = Environment.getExternalStorageDirectory().getAbsolutePath()
                return os.path.join(storage, 'SMBClient', 'connections.json')
            else:
                return os.path.expanduser('~/.smbclient/connections.json')
        else:
            return os.path.join(os.path.expanduser('~'), '.smbclient', 'connections.json')
    
    def get_saved_connections(self) -> List[str]:
        return list(self.connections.keys())
    
    def get_connection(self, name: str) -> Optional[Dict]:
        return self.connections.get(name)
    
    def save_connection(self, conn_data: Dict):
        name = conn_data.pop('name')
        self.connections[name] = conn_data
        self._save_connections()
    
    def delete_connection(self, name: str):
        if name in self.connections:
            del self.connections[name]
            self._save_connections()
    
    def connect(self, conn_data: Dict) -> bool:
        try:
            server_ip = conn_data.get('server_ip', '')
            port = int(conn_data.get('port', 445))
            username = conn_data.get('username', '')
            password = conn_data.get('password', '')
            share_name = conn_data.get('share_name', '')
            
            self.conn = SMBConnection(
                username,
                password,
                'SMBClientAndroid',
                server_ip,
                use_ntlm_v2=True
            )
            
            if self.conn.connect(server_ip, port):
                self.current_share = share_name
                self.current_path = "/"
                return True
            else:
                self.conn = None
                return False
        except Exception as e:
            print(f"连接失败: {e}")
            self.conn = None
            return False
    
    def disconnect(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
            self.current_share = ""
            self.current_path = "/"
    
    def list_path(self, path: str) -> List:
        if not self.conn or not self.current_share:
            return []
        
        try:
            files = self.conn.listPath(self.current_share, path)
            return [f for f in files if f.filename not in ('.', '..')]
        except Exception as e:
            print(f"列出目录失败: {e}")
            return []
    
    def is_connected(self) -> bool:
        return self.conn is not None
