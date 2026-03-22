[app]

title = SMB文件管理器
package.name = smbclient
package.domain = org.smbclient
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,pysmb==1.2.9,pillow

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 33
android.apptheme = @android:style/Theme.NoTitleBar
android.ndk = 25b
android.sdk = 24
android.ndk_api = 21
android.arch = arm64-v8a

android.buildtools = 33.0.0
android.gradle_dependencies = 
android.add_aars = 
android.add_jars = 
android.add_src = 

android.meta_data = 

p4a.source_dir = 
p4a.bootstrap = sdl2
p4a.local_recipes = 
p4a.recipes = 

p4a.libSDL2_ttf = True
p4a.libSDL2_image = True

fullscreen = 0
orientation = landscape

[buildozer]

log_level = 2

warn_on_root = 1
