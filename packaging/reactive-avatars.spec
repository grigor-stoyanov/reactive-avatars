# PyInstaller spec: one self-contained executable for the OS it is built on.
import os

from PyInstaller.utils.hooks import collect_all

root = os.path.abspath(os.path.join(SPECPATH, ".."))
datas = [(os.path.join(root, "src", "reactive_avatars", "static"), "reactive_avatars/static")]
binaries, hiddenimports = [], []

# uvicorn/websockets load pieces by name at runtime; sounddevice ships PortAudio
# on Windows/macOS in _sounddevice_data.
for pkg in ("uvicorn", "websockets", "sounddevice", "_sounddevice_data"):
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        continue
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    pathex=[os.path.join(root, "src")],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="reactive-avatars",
    console=True,  # shows the URLs and lets you close the app by closing the window
    upx=False,
)
