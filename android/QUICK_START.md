# 快速获取APK文件

## 方法1：使用GitHub Actions自动编译（推荐）

### 步骤
1. 将代码推送到GitCode/GitHub
2. 在仓库中启用GitHub Actions
3. 触发工作流，等待编译完成
4. 下载生成的APK文件

### 详细操作
1. **推送代码到远程仓库**
```bash
git add .
git commit -m "准备编译Android"
git push
```

2. **在GitCode仓库中**
   - 进入您的仓库页面
   - 点击 "CI/CD" 或 "Actions" 选项卡
   - 找到 "Build Android APK" 工作流
   - 点击 "Run workflow" 手动触发

3. **等待编译完成**
   - 首次编译约需30-60分钟
   - 后续编译会更快（使用缓存）

4. **下载APK**
   - 编译成功后，在工作流页面找到 "Artifacts"
   - 下载 "SMB文件管理器-APK"
   - 解压得到APK文件

---

## 方法2：使用在线构建服务

### 使用Buildozer的Docker镜像

如果您有Docker环境：
```bash
cd android
docker run --rm -v $(pwd):/home/user/hostcwd kivy/buildozer android debug
```

---

## 方法3：本地Linux/WSL2编译

### 1. 启用WSL2（Windows用户）
以管理员身份打开PowerShell：
```powershell
wsl --install
```
重启后，从Microsoft Store安装Ubuntu 20.04+

### 2. 在Ubuntu中编译
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装依赖
sudo apt install -y git python3 python3-pip build-essential \
    git ccache libncurses5:i386 libstdc++6:i386 libgtk2.0-0:i386 \
    libpangox-1.0-0:i386 libpangoxft-1.0-0:i386 libidn11:i386 \
    zlib1g:i386 openjdk-11-jdk unzip

# 安装Buildozer
pip3 install --user buildozer
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
source ~/.bashrc

# 克隆项目并编译
cd ~
git clone <your-repo-url>
cd pySmb/android
buildozer android debug
```

### 3. 获取APK
编译完成后，APK位于 `bin/` 目录。

---

## 验证APK

安装到Android设备：
```bash
adb install SMB文件管理器-1.0-arm64-v8a-debug.apk
```

或直接将APK文件复制到设备并点击安装。

---

## 注意事项

1. **首次编译时间较长**（30-60分钟），需要下载SDK/NDK
2. **确保有足够的磁盘空间**（至少10GB）
3. **GitHub Actions免费版有使用限制**，注意配额
4. **APK文件较大**（约30-50MB），这是正常的

---

## 常见问题

### Q: GitHub Actions没有显示？
A: 确保 `.github/workflows/build-android.yml` 文件已推送到仓库。

### Q: 编译失败？
A: 查看Actions日志，通常是网络问题或依赖下载失败，重新运行工作流即可。

### Q: APK无法安装？
A: 确保设备允许"未知来源"应用安装。
