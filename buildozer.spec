[app]

title = Plant Defense
package.name = plantdefense
package.domain = org.plantdefense
version = 0.1.4

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json,wav,ogg,mp3,ttf
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__

# Do not pin python3 to 3.11.5: current python-for-android hostpython3
# recipe is 3.14.2, and target python3 must match hostpython3.
# Leave python3 unpinned so python-for-android selects its matching recipe.
requirements = python3,kivy==2.3.1

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
