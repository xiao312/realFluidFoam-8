"""Assemble exactly one current comparison for each Liang Figure 1–8 panel."""
import argparse
import hashlib
import json
from pathlib import Path

import pymupdf as fitz

IDS = ["1", "2", "3", "4", "5", "6", "7", "8a", "8b"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path leaves project root: {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    for field in ["project", "manifest", "output"]:
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    root = args.project.resolve()
    manifest = contained(root, args.manifest)
    output = contained(root, args.output)
    if output.exists():
        raise ValueError("Choose a new output directory")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if [row["id"] for row in data["figures"]] != IDS:
        raise ValueError("Expected ordered figures 1–7, 8a, 8b, exactly once")
    sources = []
    for row in data["figures"]:
        pdf, evidence = contained(root, row["pdf"]), contained(root, row["evidence"])
        with fitz.open(pdf) as document:
            if not isinstance(row["page"], int) or not 0 <= row["page"] < len(document):
                raise ValueError(f"Invalid source page: {row}")
            size = list(document[row["page"]].rect)
        sources.append(dict(**row, pdf_sha256=digest(pdf), evidence_sha256=digest(evidence),
                            source_page_rect=size))
    print(json.dumps(dict(figures=len(sources), pages=10, output=str(output),
                          captured_at=data["captured_at"], remote_writes=False)))
    if args.action == "plan":
        return
    document = fitz.open()
    cover = document.new_page(width=595, height=842)
    def text(rect, value, size=10):
        if cover.insert_textbox(fitz.Rect(rect), value, fontname="helv", fontsize=size,
                                lineheight=1.2) < 0:
            raise ValueError("Cover text overflow")
    text((38, 35, 557, 91), "Liang Figures 1-8\nReplication comparison register", 18)
    text((38, 105, 557, 142), data["captured_at"]+"\nSource checkpoint: "+data["source_revision"], 9)
    text((38, 157, 557, 225), data["summary"], 10)
    y = 237
    for row in sources:
        cover.draw_line((38, y-5), (557, y-5), color=(.82, .82, .82), width=.5)
        text((38, y, 80, y+44), row["id"], 11)
        text((86, y, 557, y+18), row["title"], 10)
        text((86, y+19, 557, y+52), row["status"], 8.5)
        y += 57
    text((38, 771, 557, 820),
         "Original paper crops and captions accompany each calculation. Figure pages retain "
         "their original dimensions. Image-reading bounds are not experimental error bars. "
         "A completed solve does not establish paper agreement.", 9)
    bookmarks = [[1, "Comparison register", 1]]
    for row in sources:
        with fitz.open(contained(root, row["pdf"])) as source:
            document.insert_pdf(source, from_page=row["page"], to_page=row["page"])
        bookmarks.append([1, "Figure "+row["id"]+": "+row["title"], len(document)])
    document.set_toc(bookmarks)
    document.set_metadata({"title": "Liang Figures 1-8 replication comparisons",
                           "subject": "Qualified calculations and unresolved comparisons",
                           "author": "realFluidFoam replication project"})
    output.mkdir(parents=True)
    target = output/"liang-figures-1-8.pdf"
    document.save(target, garbage=4, deflate=True)
    with fitz.open(target) as check:
        if len(check) != 10:
            raise ValueError("Unexpected assembled page count")
        for i, row in enumerate(sources, 1):
            if list(check[i].rect) != row["source_page_rect"]:
                raise ValueError("Source page dimensions changed")
        check[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(output/"cover.png")
    record = dict(manifest_sha256=digest(manifest), script_sha256=digest(Path(__file__)),
                  output_sha256=digest(target), captured_at=data["captured_at"],
                  source_revision=data["source_revision"], figures=sources,
                  scientific_acceptance=False)
    (output/"evidence.json").write_text(json.dumps(record, indent=2)+"\n",
                                       encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
