
[app]

title = Plant Defense
package.name = plantdefense
package.domain = org.plantdefense
version = 0.2.0

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json,wav,ogg,mp3,ttf
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__

requirements = python3,kivy==2.3.1

orientation = landscape
fullscreen = 1

android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.fork = Krozark
p4a.branch = upstream-contribution
p4a.commit = 71dba8a

[buildozer]

log_level = 2
warn_on_root = 1
