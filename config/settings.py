import json
import os
from typing import Dict, Optional
from .security import SecurityManager


class Settings:
    CONFIG_FILE = "smb_config.dat"
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
            
            cls.reset_security()
            cls.unlock(new_password)
            
            cls.save_servers(old_servers)
            return True
        except Exception as e:
            print(f"修改主密码失败: {str(e)}")
            return False

    @classmethod
    def load_servers(cls) -> Dict:
        try:
            if not os.path.exists(cls.CONFIG_FILE):
                return {}
            
            with open(cls.CONFIG_FILE, "rb") as f:
                encrypted_data = f.read()
            
            if not encrypted_data:
                return {}
            
            decrypted_data = cls.get_security_manager().decrypt_bytes(encrypted_data)
            return json.loads(decrypted_data)
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
            return {}

    @classmethod
    def save_servers(cls, servers: Dict) -> bool:
        try:
            if not cls.is_unlocked():
                raise ValueError("未解锁，无法保存配置")
            
            json_data = json.dumps(servers, ensure_ascii=False, indent=2)
            encrypted_data = cls.get_security_manager().encrypt_bytes(json_data.encode('utf-8'))
            
            with open(cls.CONFIG_FILE, "wb") as f:
                f.write(encrypted_data)
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

    @classmethod
    def migrate_from_json(cls) -> bool:
        old_file = "smb_config.json"
        if not os.path.exists(old_file):
            return False
        
        try:
            with open(old_file, "r", encoding="utf-8") as f:
                servers = json.load(f)
            
            if servers and cls.is_unlocked():
                cls.save_servers(servers)
                backup_file = old_file + ".bak"
                os.rename(old_file, backup_file)
                return True
        except Exception as e:
            print(f"迁移配置失败: {str(e)}")
        return False
