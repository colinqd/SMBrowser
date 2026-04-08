from PIL import Image
import os

# 检查是否有 icon.png
if os.path.exists("icon.png"):
    print("找到 icon.png，正在转换为 .ico 格式...")
    
    # 打开图片
    img = Image.open("icon.png")
    
    # 保存为 .ico，包含多种尺寸
    img.save("app.ico", format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    
    print("转换完成！已创建 app.ico")
else:
    print("错误：未找到 icon.png 文件！")
    print("请将您的图片保存为 icon.png 放在项目根目录，然后重新运行此脚本。")
