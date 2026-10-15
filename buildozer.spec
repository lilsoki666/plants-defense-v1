[app]

title = Plant Defense
package.name = plantdefense
package.domain = org.plantdefense
version = 0.1.3

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json,wav,ogg,mp3,ttf
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__

# Python 3.11 is a conservative compatible target for Kivy 2.3.1.
# Do not pin Python 3.14: the previous log shows an Android cp314 wheel
# being rejected during the python-for-android install stage.
requirements = python3==3.11.5,kivy==2.3.1

orientation = landscape
fullscreen = 1

android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
