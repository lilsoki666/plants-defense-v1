# Plant Defense

Offline Android tower-defense prototype built with Python and Kivy.

## Build
1. Push the project to the `main` branch or run the GitHub Actions workflow manually.
2. Open **Actions** and select **Build Plant Defense APK**.
3. Download the `plant-defense-debug-apk` artifact after the workflow succeeds.

## Dependency policy
- Runtime dependencies are declared only in `buildozer.spec`.
- `requirements.txt` is intentionally empty.
- Python 3.14 is not pinned. The previous build log showed an Android `cp314` wheel being rejected by pip.
- The workflow intentionally does not run `buildozer android clean` before initialization.

## Current gameplay
- Five lanes and nine columns.
- Pea Shooter and Ice Plant.
- Sun energy, projectile attacks, zombie waves, win/loss states, restart.
- Graphics are currently canvas-drawn placeholders; custom sprite animations are future work.
