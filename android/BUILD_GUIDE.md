# Android端编译指南

## 重要说明

由于Buildozer在Windows环境下编译Android应用存在较多限制，**推荐使用Linux环境或WSL2**进行编译。

## 编译环境要求

### 方案1：使用Linux/WSL2（推荐）

#### 系统要求
- Ubuntu 20.04+ 或其他主流Linux发行版
- Python 3.8+
- Git
- Java JDK 8或11
- Android SDK（Buildozer会自动下载）

#### 安装步骤

1. **更新系统包**
```bash
sudo apt update
sudo apt upgrade -y
```

2. **安装依赖**
```bash
sudo apt install -y git python3 python3-pip build-essential \
    git ccache libncurses5:i386 libstdc++6:i386 libgtk2.0-0:i386 \
    libpangox-1.0-0:i386 libpangoxft-1.0-0:i386 libidn11:i386 \
    zlib1g:i386 openjdk-11-jdk unzip
```

3. **安装Buildozer**
```bash
pip3 install --user buildozer
```

4. **配置环境变量**
```bash
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
source ~/.bashrc
```

5. **克隆项目并进入android目录**
```bash
git clone <your-repo-url>
cd pySmb/android
```

6. **编译APK**
```bash
# 首次编译会下载SDK和NDK，需要较长时间
buildozer android debug
```

7. **编译完成后**
APK文件位于 `bin/` 目录，文件名类似 `SMB文件管理器-1.0-arm64-v8a-debug.apk`

---

### 方案2：使用Docker（最简单）

1. **安装Docker**
   - Windows: 安装Docker Desktop
   - Linux: 安装Docker Engine

2. **使用Kivy官方Docker镜像**
```bash
# 创建编译目录
mkdir -p ~/buildozer_home
cd pySmb/android

# 运行Docker容器进行编译
docker run --rm \
    -v $(pwd):/home/user/hostcwd \
    -v ~/buildozer_home:/home/user/.buildozer \
    -e BUILDOZER_WARNING_ON_ROOT=0 \
    kivy/buildozer android debug
```

---

### 方案3：Windows + WSL2

1. **启用WSL2并安装Ubuntu**
   - 按照微软官方文档启用WSL2
   - 从Microsoft Store安装Ubuntu 20.04+

2. **在WSL2中按照方案1的步骤操作**

---

## 常见问题解决

### 1. 下载SDK/NDK速度慢
Buildozer配置文件中可以修改源：
```ini
# 在buildozer.spec中添加或修改
android.sdk = 24
android.ndk = 25b
```

### 2. 内存不足
在WSL2或虚拟机中增加内存分配，建议至少8GB。

### 3. 编译超时
首次编译可能需要30分钟到2小时，请耐心等待。

### 4. Kivy安装失败
使用预编译的wheel：
```bash
pip install kivy[base] kivy_examples --pre --extra-index-url https://kivy.org/downloads/simple/
```

---

## 桌面端测试

在编译Android之前，建议先在桌面端测试：

```bash
cd android
pip install kivy kivymd pysmb pillow
python main.py
```

---

## APK安装和调试

### 安装到设备
```bash
# 使用adb安装
adb install bin/SMB文件管理器-1.0-arm64-v8a-debug.apk

# 或使用buildozer
buildozer android debug deploy run
```

### 查看日志
```bash
adb logcat | grep python
```

---

## 发布版本编译

```bash
# 发布版本（需要配置签名）
buildozer android release
```

注意：发布版本需要配置密钥签名，请参考Buildozer文档。

---

## 下一步

1. 在Linux/WSL2环境中按照上述步骤操作
2. 首次编译成功后，后续编译会快很多
3. 可以根据需要修改 `buildozer.spec` 配置文件

如有问题，请参考：
- Kivy官方文档: https://kivy.org/doc/stable/
- Buildozer文档: https://buildozer.readthedocs.io/
- python-for-android: https://python-for-android.readthedocs.io/
