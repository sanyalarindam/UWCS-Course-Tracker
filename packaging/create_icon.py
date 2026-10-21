"""Build Windows and macOS icons from the original shared calendar-and-checkmark logo."""
import argparse
from pathlib import Path
from PIL import Image


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / 'web/assets/logo.png'
    image = Image.open(source).convert('RGBA').resize((1024,1024), Image.Resampling.LANCZOS)
    image.save(output / 'app.png')
    image.save(output / 'app.icns')
    image.save(output / 'app.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('.local-data/build-tools'))
    build(parser.parse_args().output)
