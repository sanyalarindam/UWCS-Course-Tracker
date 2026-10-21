"""Generate the app's original purple W mark at Windows icon sizes."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGBA', (1024,1024), (0,0,0,0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24,24,1000,1000), radius=220, fill='#633F91')
    # Geometric W; defined as a vector polygon so no fonts are required.
    points = [(155,270),(295,270),(386,652),(467,340),(564,340),(646,652),(734,270),(870,270),(704,765),(584,765),(515,509),(443,765),(324,765)]
    draw.polygon(points, fill='#FFFFFF')
    image.save(output / 'app.png')
    image.save(output / 'app.icns')
    image.save(output / 'app.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('.local-data/build-tools'))
    build(parser.parse_args().output)
