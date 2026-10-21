"""Reject app bundles whose native binaries require a newer macOS release."""
import argparse
from pathlib import Path
import plistlib
import re
import subprocess

MACHO_MAGIC = {bytes.fromhex(value) for value in (
    'feedface', 'cefaedfe', 'feedfacf', 'cffaedfe',
    'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca')}


def version(value):
    parts = tuple(int(part) for part in value.split('.'))
    return (parts + (0, 0, 0))[:3]


def check(bundle, arch, maximum='14.0'):
    limit = version(maximum)
    metadata = plistlib.loads((bundle / 'Contents/Info.plist').read_bytes())
    declared = metadata.get('LSMinimumSystemVersion')
    if not declared or version(declared) > limit:
        raise RuntimeError(f'App minimum is {declared!r}; expected at most {maximum}.')
    checked = 0
    for path in bundle.rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open('rb') as source:
            if source.read(4) not in MACHO_MAGIC:
                continue
        output = subprocess.check_output(
            ['otool', '-arch', arch, '-l', str(path)], text=True)
        minimums = re.findall(
            r'\bcmd LC_BUILD_VERSION\b(?:(?!\bcmd\b).)*?\bminos ([\d.]+)'
            r'|\bcmd LC_VERSION_MIN_MACOSX\b(?:(?!\bcmd\b).)*?\bversion ([\d.]+)',
            output, re.S)
        values = [modern or legacy for modern, legacy in minimums]
        if not values:
            raise RuntimeError(f'Cannot verify macOS minimum for {path}.')
        if any(version(value) > limit for value in values):
            raise RuntimeError(f'{path} requires macOS {values}; maximum is {maximum}.')
        checked += 1
    if not checked:
        raise RuntimeError('No native binaries found in app bundle.')
    print(f'Checked {checked} native binaries ({arch}): minimum macOS <= {maximum}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--arch', required=True, choices=['arm64', 'x86_64'])
    check(**vars(parser.parse_args()))
