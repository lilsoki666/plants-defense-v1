# Plant Defense

Offline Android tower-defense prototype built with Python and Kivy.

## Build APK with GitHub Actions

1. Commit all files to the repository's `main` branch.
2. Open the **Actions** tab.
3. Select **Build Plant Defense APK** and run **Run workflow**, or push a commit to `main`.
4. When the workflow succeeds, download the `plant-defense-debug-apk` artifact.

## Dependency note

`buildozer.spec` uses `requirements = python3,kivy==2.3.1`. The Python recipe is intentionally not pinned to 3.11.5 because the current `python-for-android` checkout in the supplied logs uses `hostpython3` 3.14.2. The target `python3` recipe must match the host recipe. `requirements.txt` is intentionally empty to prevent unrelated packages from being installed.

This project has not been confirmed by a successful Android build until GitHub Actions completes successfully.
