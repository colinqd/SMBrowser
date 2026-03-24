import json
import os
from typing import Dict, Optional
from .security import SecurityManager


class Settings:
    CONFIG_FILE = "smb_config.json"
    _security_manager: Optional[SecurityManager] = None

    @classmethod
    def get_security_manager(cls) -> SecurityManager:
        if cls._security_manager is None:
            cls._security_manager = SecurityManager()
        return cls._security_manager

    @classmethod
    def is_unlocked(cls) -> bool:
        return cls.get_security_manager().is_unlocked()

    @classmethod
    def is_using_default_password(cls) -> bool:
        return cls.get_security_manager().is_using_default_password()

    @classmethod
    def unlock(cls, master_password: str) -> bool:
        try:
            cls.get_security_manager().set_master_password(master_password)
            return True
        except:
            return False

    @classmethod
    def lock(cls):
        cls.get_security_manager().lock()

    @classmethod
    def has_config(cls) -> bool:
        return os.path.exists(cls.CONFIG_FILE)

    @classmethod
    def reset_security(cls):
        cls.get_security_manager().reset_to_default()

    @classmethod
    def clear_all_settings(cls) -> bool:
        try:
            if os.path.exists(cls.CONFIG_FILE):
                os.remove(cls.CONFIG_FILE)
            cls.reset_security()
            cls._security_manager = None
            return True
        except Exception as e:
            print(f"清空设置失败: {str(e)}")
            return False

    @classmethod
    def change_master_password(cls, new_password: str) -> bool:
        try:
            old_servers = cls.load_servers()
            decrypted_servers = {}
            for name, config in old_servers.items():
                cfg = config.copy()
                if "password" in cfg and cfg["password"]:
                    try:
                        cfg["password"] = cls.decrypt_password(cfg["password"])
                    except:
                        pass
                decrypted_servers[name] = cfg
            
            cls.reset_security()
            cls.unlock(new_password)
            
            encrypted_servers = {}
            for name, config in decrypted_servers.items():
                cfg = config.copy()
                if "password" in cfg and cfg["password"]:
                    cfg["password"] = cls.encrypt_password(cfg["password"])
                encrypted_servers[name] = cfg
            
            cls.save_servers(encrypted_servers)
            return True
        except Exception as e:
            print(f"修改主密码失败: {str(e)}")
            return False

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

    @classmethod
    def encrypt_password(cls, password: str) -> str:
        if not password:
            return ""
        try:
            return cls.get_security_manager().encrypt(password)
        except:
            return password

    @classmethod
    def decrypt_password(cls, encrypted_password: str) -> str:
        if not encrypted_password:
            return ""
        try:
            return cls.get_security_manager().decrypt(encrypted_password)
        except:
            return encrypted_password
