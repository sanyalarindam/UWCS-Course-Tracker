"""Build a native macOS app and drag-to-Applications DMG on a Mac runner."""
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def run(*args, **kwargs):
    subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def main():
    if sys.platform != 'darwin': raise SystemExit('Build macOS installers on macOS.')
    os.chdir(ROOT)
    version = os.environ.get('APP_VERSION','0.3.0')
    arch = os.environ.get('MAC_ARCH', platform.machine())
    if arch != platform.machine(): raise SystemExit('Build on a runner matching the target architecture.')
    run(sys.executable, 'packaging/create_icon.py')
    run(sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--distpath','dist','--workpath','.local-data/pyinstaller','packaging/macos.spec')
    bundle = ROOT / 'dist/CS Tracker.app'
    binary = bundle / 'Contents/MacOS/CS Tracker'
    run(sys.executable, 'packaging/check_macos_compatibility.py', str(bundle), '--arch', arch)
    run(str(binary), '--smoke-test', timeout=120)
    run('codesign','--verify','--deep','--strict','--verbose=2',str(bundle))
    installer = ROOT / 'dist/installer'
    installer.mkdir(parents=True, exist_ok=True)
    staging = ROOT / '.local-data/dmg-staging'
    staging.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=staging) as directory:
        destination = Path(directory)
        run('ditto', str(bundle), str(destination / bundle.name))
        (destination / 'Applications').symlink_to('/Applications', target_is_directory=True)
        (destination / 'READ ME.txt').write_text('CS Tracker\n\nDrag CS Tracker.app to Applications, then eject this disk image.\nChoose the arm64 installer for Apple Silicon or x86_64 for Intel.\nRequires macOS 14 (Sonoma) or later, including Sonoma 14.7.3.\n\nThis build is ad-hoc signed, not Apple Developer ID signed or notarized.\nmacOS may block the first launch. See Apple guidance: https://support.apple.com/102445\n\nData is stored in ~/Library/Application Support/UWCS Tracker. Updating or deleting the app does not delete this folder.\nSource: https://github.com/sanyalarindam/UWCS-Course-Tracker\n', encoding='utf-8')
        output = installer / f'CS-Tracker-{version}-macOS-{arch}.dmg'
        run('hdiutil','create','-volname','CS Tracker','-srcfolder',str(destination),'-format','UDZO','-ov',str(output))
        run('hdiutil','verify',str(output))
    print(output, flush=True)

if __name__ == '__main__': main()
