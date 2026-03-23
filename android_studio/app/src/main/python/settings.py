import os
import json
from typing import Dict, Optional

try:
    from com.chaquo.python import Python as ChaquoPython
    HAS_CHAQUO = True
except ImportError:
    HAS_CHAQUO = False
    ChaquoPython = None

try:
    from android.os import Environment
    HAS_ANDROID = True
except ImportError:
    HAS_ANDROID = False
    Environment = None

try:
    from java.io import File
    HAS_JAVA = True
except ImportError:
    HAS_JAVA = False
    File = None


class Settings:
    CONFIG_FILE = "servers.json"
    _config_path: Optional[str] = None

    @staticmethod
    def get_config_path() -> str:
        if Settings._config_path:
            return Settings._config_path
        
        if HAS_CHAQUO:
            try:
                context = ChaquoPython.getPlatform().getApplication()
                if context:
                    files_dir = context.getFilesDir()
                    Settings._config_path = os.path.join(str(files_dir.getAbsolutePath()), Settings.CONFIG_FILE)
                    return Settings._config_path
            except Exception as e:
                print(f"获取Android路径失败: {str(e)}")
        
        if HAS_ANDROID and HAS_JAVA:
            try:
                storage = Environment.getExternalStorageDirectory().getAbsolutePath()
                config_dir = os.path.join(str(storage), "SMBClient")
                os.makedirs(config_dir, exist_ok=True)
                Settings._config_path = os.path.join(config_dir, Settings.CONFIG_FILE)
                return Settings._config_path
            except Exception as e:
                print(f"获取外部存储路径失败: {str(e)}")
        
        Settings._config_path = Settings.CONFIG_FILE
        return Settings._config_path

    @staticmethod
    def load_servers() -> Dict:
        try:
            config_path = Settings.get_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误: {str(e)}")
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
        return {}

    @staticmethod
    def save_servers(servers: Dict) -> bool:
        try:
            config_path = Settings.get_config_path()
            config_dir = os.path.dirname(config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(servers, f, ensure_ascii=False, indent=2)
            return True
        except PermissionError as e:
            print(f"权限不足，无法保存配置: {str(e)}")
            return False
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
            return False
