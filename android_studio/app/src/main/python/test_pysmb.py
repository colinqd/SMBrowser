def test_pysmb():
    result = []
    
    try:
        result.append("✓ 测试pysmb库")
        
        import smb
        result.append(f"✓ pysmb版本: {getattr(smb, '__version__', 'unknown')}")
        
        from smb.SMBConnection import SMBConnection
        result.append("✓ SMBConnection导入成功")
        
        from smb.base import NotConnectedError
        result.append("✓ NotConnectedError导入成功")
        
        result.append("\n✓ pysmb测试通过！")
        
    except Exception as e:
        result.append(f"\n✗ 错误: {str(e)}")
        import traceback
        result.append(traceback.format_exc())
    
    return "\n".join(result)


if __name__ == "__main__":
    print(test_pysmb())
