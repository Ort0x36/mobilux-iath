"""Cut the web images for the "I nostri bus" section out of imagem_onibus.jpeg.

Run once from the project root:  python tools/make_bus_images.py
Writes to static/img/. Needs Pillow (pip install pillow); the site itself does not.
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "imagem_onibus.jpeg"
OUT = ROOT / "static" / "img"

# Regions of the 1600x900 source sheet (left, top, right, bottom).
EXTERIOR = (236, 20, 942, 416)
INTERIORS = {
    "bedroom": (2, 420, 410, 608),
    "living": (416, 420, 812, 608),
    "kitchen": (818, 420, 1218, 608),
    "bathroom": (1224, 420, 1600, 608),
}
PLAN = (28, 700, 660, 862)

# Rough outline of the coach inside the EXTERIOR crop, used for the line drawing.
BUS_OUTLINE = [(4, 168), (40, 128), (160, 92), (290, 58), (420, 30), (545, 36), (630, 62),
               (668, 112), (684, 250), (680, 334), (560, 344), (430, 356), (300, 330),
               (110, 320), (4, 306)]
# The source has the MOBILUX logo in this corner; it is painted over with sky.
# The logo itself ends around x=96, y=68; the box leaves room for a soft edge
# and stays above the coach roof so the mirrored patch only contains sky.
LOGO_BOX = (0, 0, 120, 84)

SCALE = 1.6
GOLD = (226, 196, 127)


def upscale(img, factor=SCALE):
    size = (round(img.width * factor), round(img.height * factor))
    return img.resize(size, Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))


def remove_logo(img):
    """Cover the logo corner with a mirror image of the landscape just to its right."""
    left, top, right, bottom = LOGO_BOX
    width = right - left
    patch = ImageOps.mirror(img.crop((right, top, right + width, bottom)))
    # Fade the patch in along its right and bottom edges so there is no visible seam.
    fade = Image.new("L", patch.size, 255)
    draw = ImageDraw.Draw(fade)
    for i in range(20):
        draw.line([(width - 1 - i, 0), (width - 1 - i, patch.height)], fill=int(255 * i / 20))
    for i in range(14):
        draw.line([(0, patch.height - 1 - i), (width - 1 - i, patch.height - 1 - i)], fill=int(255 * i / 14))
    patched = img.copy()
    patched.paste(patch, (left, top), fade)
    return patched


def line_drawing(img):
    """Gold 'blueprint' lines of the coach on a transparent background."""
    grey = ImageOps.grayscale(img).filter(ImageFilter.GaussianBlur(1.1))
    edges = ImageOps.autocontrast(grey.filter(ImageFilter.FIND_EDGES), cutoff=2)
    edges = edges.point(lambda v: 0 if v < 38 else min(255, int((v - 38) * 2.2)))

    mask = Image.new("L", img.size, 0)
    scale_x, scale_y = img.width / (EXTERIOR[2] - EXTERIOR[0]), img.height / (EXTERIOR[3] - EXTERIOR[1])
    ImageDraw.Draw(mask).polygon([(x * scale_x, y * scale_y) for x, y in BUS_OUTLINE], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(10))

    alpha = ImageChops.multiply(edges, mask)
    drawing = Image.new("RGBA", img.size, GOLD + (0,))
    drawing.putalpha(alpha)
    return drawing


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(SOURCE).convert("RGB")

    exterior = upscale(remove_logo(sheet.crop(EXTERIOR)))
    exterior.save(OUT / "bus-exterior.jpg", quality=86, optimize=True, progressive=True)
    line_drawing(exterior).save(OUT / "bus-lines.png", optimize=True)

    for name, box in INTERIORS.items():
        upscale(sheet.crop(box), 1.4).save(OUT / f"bus-{name}.jpg", quality=84, optimize=True, progressive=True)

    upscale(sheet.crop(PLAN)).save(OUT / "bus-plan.jpg", quality=86, optimize=True, progressive=True)
    print("Images written to", OUT)


if __name__ == "__main__":
    main()
