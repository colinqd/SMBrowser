# SMB文件管理器 - Android端

基于Kivy/KivyMD框架开发的跨平台SMB文件管理器Android客户端。

## 功能特性

- SMB服务器连接管理
- 文件浏览和导航
- 多种文件类型图标支持
- Material Design界面
- 连接配置保存

## 项目结构

```
android/
├── __init__.py
├── main.py              # 主入口文件
├── connection.py        # SMB连接管理
├── file_browser.py      # 文件浏览器组件
├── requirements.txt     # Python依赖
├── buildozer.spec       # Buildozer配置
└── README.md           # 说明文档
```

## 环境要求

- Python 3.8+
- Kivy 2.3.0+
- KivyMD 1.2.0+
- pysmb 1.2.9+
- Buildozer (用于Android打包)

## 安装依赖

```bash
cd android
pip install -r requirements.txt
```

## 桌面端运行

```bash
cd android
python main.py
```

## Android打包

### 安装Buildozer

```bash
pip install buildozer
```

### 编译APK

```bash
cd android
buildozer android debug
```

编译完成后，APK文件位于 `bin/` 目录。

### 安装到设备

```bash
buildozer android debug deploy run
```

## 主要模块说明

### connection.py
SMB连接管理模块，负责：
- 连接配置的保存和加载
- SMB服务器连接管理
- 目录列表获取

### file_browser.py
文件浏览器组件，负责：
- 文件列表显示
- 目录导航
- 文件类型图标识别

### main.py
主应用入口，包含：
- 主界面布局
- 连接管理对话框
- 导航抽屉

## 注意事项

1. Android版本需要适当的存储权限
2. 首次运行需要配置SMB服务器连接
3. 大文件操作可能需要异步处理

## 后续开发计划

- [ ] 文件上传/下载功能
- [ ] 批量操作
- [ ] 文件搜索
- [ ] 离线缓存
- [ ] 暗黑模式
