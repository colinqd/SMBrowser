# Android Studio编译指南

## 项目概述

本项目使用 **Chaquopy** 框架，允许在Android Studio中编译包含Python代码的Android应用。

### 技术栈
- **Android Studio** - IDE
- **Gradle** - 构建工具
- **Chaquopy** - Python for Android框架
- **Kivy/KivyMD** - UI框架
- **pysmb** - SMB协议支持

---

## 环境要求

1. **Android Studio** (最新稳定版)
2. **JDK 8 或 11**
3. **Android SDK** (API 24+)
4. **Android NDK** (Chaquopy会自动下载)
5. **Python 3.8+** (仅用于本地开发)

---

## 快速开始

### 1. 打开项目

1. 启动Android Studio
2. 选择 `File` → `Open`
3. 导航到 `pySmb/android_studio` 目录
4. 点击 `OK`
5. 等待Gradle同步完成（首次可能需要几分钟）

### 2. 配置Chaquopy

Chaquopy需要许可证才能使用所有功能：

#### 免费版（有功能限制）
- 自动应用，无需配置
- APK文件较大
- 有启动提示

#### 完整版（推荐）
1. 访问 https://chaquo.com/chaquopy/
2. 获取许可证密钥
3. 在 `app/build.gradle` 中添加：
```gradle
android {
    defaultConfig {
        python {
            license "你的许可证密钥"
        }
    }
}
```

### 3. 同步依赖

1. 点击Android Studio顶部的 `Sync Project with Gradle Files` 按钮
2. 或选择 `File` → `Sync Project with Gradle Files`
3. 等待所有依赖下载完成

### 4. 编译APK

#### Debug版本（测试用）
1. 选择 `Build` → `Build Bundle(s) / APK(s)` → `Build APK(s)`
2. 或点击工具栏的绿色播放按钮（Run）
3. 编译完成后会显示APK位置通知

#### Release版本（发布用）
1. 选择 `Build` → `Generate Signed Bundle / APK`
2. 选择 `APK`
3. 配置签名密钥
4. 选择 `release` build variant
5. 点击 `Finish`

---

## Python依赖配置

在 `app/build.gradle` 中添加Python依赖：

```gradle
android {
    defaultConfig {
        python {
            pip {
                install "kivy>=2.3.0"
                install "kivymd>=1.2.0"
                install "pysmb>=1.2.9"
                install "pillow"
            }
        }
    }
}
```

注意：Chaquopy会自动处理这些依赖，无需手动pip install。

---

## 项目结构

```
android_studio/
├── gradle/                          # Gradle wrapper
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/org/smbclient/app/
│   │   │   │   └── MainActivity.java    # Java入口
│   │   │   ├── python/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py               # Python主入口
│   │   │   │   ├── connection.py         # SMB连接管理
│   │   │   │   └── file_browser.py       # 文件浏览器
│   │   │   ├── res/                      # Android资源
│   │   │   │   └── values/
│   │   │   │       ├── strings.xml
│   │   │   │       └── themes.xml
│   │   │   └── AndroidManifest.xml
│   ├── build.gradle                      # App模块配置
│   └── proguard-rules.pro
├── build.gradle                          # 项目配置
├── settings.gradle                       # 项目设置
├── gradle.properties                     # Gradle属性
└── ANDROID_STUDIO_GUIDE.md              # 本文件
```

---

## 常见问题

### 1. Gradle同步失败
- 检查网络连接
- 尝试 `File` → `Invalidate Caches / Restart`
- 删除 `.gradle` 文件夹重新同步

### 2. Python依赖下载失败
- 配置镜像源（在 `gradle.properties` 中添加代理）
- 或手动下载whl文件放到 `app/libs`

### 3. Chaquopy相关错误
- 确保使用的是Chaquopy 14.0.2或更高版本
- 检查NDK是否正确配置
- 查看详细日志：`View` → `Tool Windows` → `Gradle Console`

### 4. Kivy在Android上不显示
- 确保有 `android:configChanges` 在 `AndroidManifest.xml`
- 检查Kivy日志：`adb logcat | grep python`

---

## 调试

### 查看Python日志
```bash
adb logcat | grep -i python
```

### 查看完整日志
```bash
adb logcat
```

### 在Android Studio中调试
1. 连接设备或启动模拟器
2. 点击工具栏的调试按钮（虫子图标）
3. 断点可以设置在Java代码中
4. Python代码使用print语句调试

---

## APK输出位置

- **Debug APK**: `app/build/outputs/apk/debug/app-debug.apk`
- **Release APK**: `app/build/outputs/apk/release/app-release.apk`

---

## 性能优化

1. **减小APK大小**
   - 在 `app/build.gradle` 中只保留需要的ABI：
     ```gradle
     ndk {
         abiFilters 'arm64-v8a'  // 只保留64位ARM
     }
     ```

2. **启用代码压缩**
   ```gradle
   buildTypes {
       release {
           minifyEnabled true
           shrinkResources true
       }
   }
   ```

---

## 参考资源

- [Chaquopy官方文档](https://chaquo.com/chaquopy/doc/latest/)
- [Kivy Android文档](https://kivy.org/doc/stable/guide/packaging-android.html)
- [Android开发者文档](https://developer.android.com/docs)
