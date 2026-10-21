import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
wv_data, wv_binaries, wv_hidden = collect_all('webview')
a = Analysis([str(root / 'desktop.py')], pathex=[str(root)],
    binaries=wv_binaries,
    datas=[(str(root / 'web'), 'web'), (str(root / 'data'), 'data')] + wv_data,
    hiddenimports=wv_hidden + ['webview.platforms.cocoa', 'tzdata'],
    excludes=['PyQt5','PyQt6','PySide2','PySide6','tkinter','webview.platforms.gtk','webview.platforms.qt','webview.platforms.winforms','webview.platforms.edgechromium','clr','pythonnet'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='CS Tracker',
    debug=False, strip=False, upx=False, console=False,
    target_arch=os.environ.get('MAC_ARCH'), codesign_identity=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='CS Tracker')
app = BUNDLE(coll, name='CS Tracker.app',
    icon=str(root / '.local-data/build-tools/app.icns'),
    bundle_identifier='io.github.sanyalarindam.cstracker',
    info_plist={
        'CFBundleName':'CS Tracker',
        'CFBundleDisplayName':'CS Tracker',
        'CFBundleShortVersionString':os.environ.get('APP_VERSION','0.3.0'),
        'CFBundleVersion':os.environ.get('APP_VERSION','0.3.0'),
        'NSHighResolutionCapable':True,
        'LSMinimumSystemVersion':'15.0',
        'NSAppTransportSecurity':{'NSAllowsLocalNetworking':True},
    })
