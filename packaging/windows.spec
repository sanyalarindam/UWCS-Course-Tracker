from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
wv_data, wv_binaries, wv_hidden = collect_all('webview')
a = Analysis([str(root / 'desktop.py')], pathex=[str(root)],
    binaries=wv_binaries,
    datas=[(str(root / 'web'), 'web'), (str(root / 'data'), 'data')] + wv_data,
    hiddenimports=wv_hidden + ['webview.platforms.edgechromium', 'tzdata'],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'tkinter', 'webview.platforms.gtk', 'webview.platforms.cocoa', 'webview.platforms.qt'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='CS Tracker',
    debug=False, strip=False, upx=False, console=False, icon=str(root / '.local-data/build-tools/app.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='CS Tracker')
