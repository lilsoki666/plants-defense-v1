
[app]

title = Plant Defense
package.name = plantdefense
package.domain = org.plantdefense

source.dir = .
source.include_exts = py,png,jpg,jpeg,atlas,json,kv,wav,ogg,mp3,ttf
version = 0.1.0

requirements = python3,kivy==2.3.1

orientation = landscape
fullscreen = 1

android.api = 35
android.minapi = 23
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
