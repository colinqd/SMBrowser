def test_imports():
    results = []
    
    results.append("测试Python环境...")
    
    try:
        import sys
        results.append(f"✓ Python版本: {sys.version}")
    except Exception as e:
        results.append(f"✗ sys导入失败: {e}")
    
    try:
        import socket
        results.append("✓ socket导入成功")
    except Exception as e:
        results.append(f"✗ socket导入失败: {e}")
    
    try:
        import threading
        results.append("✓ threading导入成功")
    except Exception as e:
        results.append(f"✗ threading导入失败: {e}")
    
    try:
        from typing import Optional, List, Dict, Any
        results.append("✓ typing导入成功")
    except Exception as e:
        results.append(f"✗ typing导入失败: {e}")
    
    try:
        import json
        results.append("✓ json导入成功")
    except Exception as e:
        results.append(f"✗ json导入失败: {e}")
    
    try:
        import os
        results.append("✓ os导入成功")
    except Exception as e:
        results.append(f"✗ os导入失败: {e}")
    
    results.append("\n测试pysmb库...")
    
    try:
        import smb
        results.append(f"✓ smb包导入成功")
    except Exception as e:
        results.append(f"✗ smb包导入失败: {e}")
        return "\n".join(results)
    
    try:
        from smb.SMBConnection import SMBConnection
        results.append("✓ SMBConnection导入成功")
    except Exception as e:
        results.append(f"✗ SMBConnection导入失败: {e}")
    
    try:
        from smb.base import NotConnectedError
        results.append("✓ NotConnectedError导入成功")
    except Exception as e:
        results.append(f"✗ NotConnectedError导入失败: {e}")
    
    results.append("\n测试项目模块...")
    
    try:
        from connection import SMBConnectionManager
        results.append("✓ connection模块导入成功")
    except Exception as e:
        results.append(f"✗ connection模块导入失败: {e}")
    
    try:
        from file_browser import FileBrowser
        results.append("✓ file_browser模块导入成功")
    except Exception as e:
        results.append(f"✗ file_browser模块导入失败: {e}")
    
    try:
        from settings import Settings
        results.append("✓ settings模块导入成功")
    except Exception as e:
        results.append(f"✗ settings模块导入失败: {e}")
    
    results.append("\n所有测试完成!")
    return "\n".join(results)


if __name__ == "__main__":
    print(test_imports())
