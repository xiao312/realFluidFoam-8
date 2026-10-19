"""Review surfaces retain scientific status and explicit keys inside computed images."""
from html import escape
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle


def status(item, config, metrics):
    key=item["id"]
    if key=="2022-fig06": return config["methane"]["status"]+". Open blue triangles: our SRK values; original red curves and black triangles retained. PR is in numerical checks."
    if key=="2025-fig06": return config["nitrogen"]["status"]+". Open blue circles: our PR; open teal circles: our SRK density."
    if key=="2022-fig12":
        cfg=config["premixed"]
        keytext="Open blue squares: OH gas-relative estimates; open teal circles: temperature-front estimates." if cfg.get("include_temperature") else "Open squares: OH gas-relative estimates."
        return cfg["status"]+". "+keytext+f" OH threshold {metrics['premixed']['primary_OH_level']:g}, final {metrics['premixed']['primary_window_s']*1e6:g} microseconds. Inlet speed is not measured flame speed."
    if key in {"2022-fig08","2022-fig09","2022-fig10","2022-fig11"}:
        cases=metrics["counterflow"]
        relevant=["oxy-1","oxy-200"] if key=="2022-fig08" else [{"09":"oxy-1","10":"oxy-200","11":"air-100"}[key[-2:]]]
        text="; ".join(f"{name}: job {cases[name]['job']}, {cases[name]['time_s']*1000:g} ms, {cases[name]['cells']:,} cells, {cases[name]['status']}" for name in relevant)
        return text+". "+("New field interiors; original axes and colour bars. Streamline seeding is approximate." if key=="2022-fig08" else "Solid blue: our T/properties; solid species colours: our species. Original curves and inset remain reference data.")
    return item["qualification"]


def build(inventory, config, metrics, output):
    cards=[];pdf=canvas.Canvas(str(output/"comparison-review.pdf"),pagesize=(1191,842))
    textstyle=ParagraphStyle("body",fontName="Helvetica",fontSize=10,leading=14)
    def paragraph(text,x,y,w):
        p=Paragraph(escape(text),textstyle);_,h=p.wrap(w,750);p.drawOn(pdf,x,y-h)
    def picture(path,x,y,w,h):
        image=ImageReader(str(path));iw,ih=image.getSize();s=min(w/iw,h/ih)
        pdf.drawImage(image,x+(w-iw*s)/2,y+(h-ih*s)/2,width=iw*s,height=ih*s,mask="auto")
    for item in inventory:
        key=item["id"];has=(output/"overlays"/(key+".png")).exists();note=status(item,config,metrics)
        original=f"originals/{key}.png";overlay=f"overlays/{key}.png"
        right=f'<img src="{overlay}" alt="Computed data on original figure frame">' if has else '<p>No computed comparison for this figure.</p>'
        links=f'<a href="layers/{key}.svg">Transparent data SVG</a>' if has else ''
        if (output/"standalone"/(key+".svg")).exists(): links+=f' | <a href="standalone/{key}.svg">Standalone computed plot</a>'
        cards.append(f'<article id="{key}"><h2>{escape(key+": "+item["title"])}</h2><p>{escape(note)}</p><div class="pair"><figure><figcaption>Original paper</figcaption><img src="{original}"><img class="caption" src="captions/{key}.png"></figure><figure><figcaption>Computed data on paper frame</figcaption>{right}</figure></div><p>{links}</p></article>')
        pdf.setFont("Helvetica-Bold",17);pdf.drawString(30,805,key+": "+item["title"])
        paragraph(note,30,780,1130)
        picture(output/original,30,205,550,510)
        if has: picture(output/overlay,610,205,550,510)
        else: paragraph("No computed comparison. Reference retained for scope and implementation context.",650,500,450)
        paragraph("Original paper and caption",30,185,550)
        picture(output/"captions"/(key+".png"),30,65,550,100)
        paragraph("Computed data on the exact source frame. Original legends identify original data; our added-data key is inside each computed image. Figure dimensions are preserved in the individual PNG/SVG files.",610,180,540)
        paragraph("Interim data and failed checks remain explicit. Figure styling does not establish replication acceptance. See provenance.json and data/metrics.json for source identities and numerical evidence.",610,110,540)
        pdf.showPage()
    pdf.save()
    (output/"index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>RealFluidFoam replication review</title><style>body{font:16px Georgia,serif;margin:2rem auto;max-width:1450px;color:#222}article{border-top:1px solid #ccc;padding:1rem 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}figure{margin:0}img{width:100%;height:auto}.caption{margin-top:1rem}figcaption{font-weight:bold;margin-bottom:.8rem}p{line-height:1.5}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><h1>RealFluidFoam replication review</h1><p>Original frames, computed data and explicit run status. No numerical alignment or fitted scaling. <a href="comparison-review.pdf">PDF review</a> | <a href="data/metrics.json">Numerical checks</a> | <a href="provenance.json">Provenance</a></p>'+''.join(cards)+'</html>',encoding="utf-8")
    rendered=[i for i in inventory if (output/"overlays"/(i["id"]+".png")).exists()]
    sheet=Image.new("RGB",(1400,len(rendered)*440),"white");draw=ImageDraw.Draw(sheet)
    for n,item in enumerate(rendered):
        draw.text((20,n*440+8),item["id"]+" | original (left), computed overlay (right)",fill="black")
        for col,kind in enumerate(["originals","overlays"]):
            img=Image.open(output/kind/(item["id"]+".png")).convert("RGB");img.thumbnail((680,405))
            sheet.paste(img,(col*700+(700-img.width)//2,n*440+30))
    sheet.save(output/"style-contact-sheet.png")
