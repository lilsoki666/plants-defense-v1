[app]

title = Plant Defense
package.name = plantdefense
package.domain = org.plantdefense

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json,wav,ogg,mp3,ttf
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__

version = 0.1.2

# Dependensi aplikasi hanya Python dan Kivy.
# Jangan tambahkan requests, certifi, chardet, urllib3,
# filetype, idna, six, atau charset-normalizer.
requirements = python3,kivy==2.3.1

orientation = landscape
fullscreen = 1

# Android
android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

# Aplikasi offline; tidak memerlukan internet.
# Tidak ada permission internet yang diminta secara eksplisit.

[buildozer]

log_level = 2
warn_on_root = 1
