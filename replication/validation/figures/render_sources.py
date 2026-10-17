"""Render the inspected figure crops and a contact sheet for every paper figure."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import pymupdf
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root", type=Path)
parser.add_argument("pdf2022", type=Path)
parser.add_argument("pdf2025", type=Path)
args = parser.parse_args()
root = args.root.resolve(strict=True)
out = root/"output/figure-comparison-20261017"
(out/"originals").mkdir(parents=True, exist_ok=True)
(out/"plots").mkdir(exist_ok=True)
(out/"captions").mkdir(exist_ok=True)
inventory = json.loads(Path(__file__).with_name("inventory.json").read_text())
sources = {2022: args.pdf2022, 2025: args.pdf2025}
documents = {year: pymupdf.open(path) for year, path in sources.items()}
for item in inventory:
    page = documents[item["year"]][item["page"]-1]
    page.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), clip=pymupdf.Rect(item["crop"])).save(
        out/"originals"/(item["id"]+".png"))
    matches = [b for b in page.get_text("blocks")
               if re.match(r"Fig\.\s*"+str(item["figure"])+r"\.", b[4])]
    if len(matches) != 1:
        raise ValueError("Caption is missing or ambiguous: "+item["id"])
    bounds = pymupdf.Rect(matches[0][:4])
    # This caption's superscript/subscript splits it across three PDF text blocks.
    if item["id"] == "2022-fig12":
        bounds = pymupdf.Rect(306.63, 203.97, 560.50, 231.08)
    bounds = bounds + (-2, -2, 2, 2)
    page.get_pixmap(matrix=pymupdf.Matrix(4, 4), clip=bounds).save(
        out/"captions"/(item["id"]+".png"))
    item["caption_crop"] = list(bounds)
for year in (2022, 2025):
    items = [item for item in inventory if item["year"] == year]
    sheet = Image.new("RGB", (1200, ((len(items)+2)//3)*340), "#e9edf0")
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(items):
        picture = Image.open(out/"originals"/(item["id"]+".png")).convert("RGB")
        picture.thumbnail((380, 300))
        x, y = (index%3)*400, (index//3)*340
        sheet.paste(picture, (x+(400-picture.width)//2, y+28))
        draw.text((x+12, y+8), f'{item["id"]}: {item["status"]}', fill="black")
    sheet.save(out/f"contact-sheet-{year}.png")
manifest = {str(year): dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          pages=len(documents[year])) for year, path in sources.items()}
(out/"source-provenance.json").write_text(json.dumps(manifest, indent=2)+"\n")
(out/"inventory.json").write_text(json.dumps(inventory, indent=2)+"\n")
print(f"Rendered {len(inventory)} figures into {out}")
