import json
import os
from typing import Dict


class Settings:
    CONFIG_FILE = "smb_config.json"

    @staticmethod
    def load_servers() -> Dict:
        try:
            if os.path.exists(Settings.CONFIG_FILE):
                with open(Settings.CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
        return {}

    @staticmethod
    def save_servers(servers: Dict) -> bool:
        try:
            with open(Settings.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(servers, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
            return False
