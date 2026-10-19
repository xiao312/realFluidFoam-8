"""Paper-coordinate rendering; keep source frames and computed layers separate."""
import re
import numpy as np
import pymupdf
from PIL import Image
from common import affine, digest, write_json


def source_crops(papers, inventory, output, dpi):
    records = []
    for item in inventory:
        doc = papers[str(item["year"])]
        page = doc[item["page"]-1]
        crop = pymupdf.Rect(item["crop"])
        # Integer crops and dpi=360 give exact, reproducible pixel extents.
        page.get_pixmap(matrix=pymupdf.Matrix(dpi/72,dpi/72),clip=crop).save(output/"originals"/(item["id"]+".png"))
        blocks = [b for b in page.get_text("blocks") if re.match(r"Fig\.\s*"+str(item["figure"])+r"\.",b[4])]
        if len(blocks)!=1: raise ValueError(f"Ambiguous caption: {item['id']}")
        bounds = pymupdf.Rect(blocks[0][:4])
        if item["id"]=="2022-fig12": bounds=pymupdf.Rect(306.63,203.97,560.50,231.08)
        bounds += (-2,-2,2,2)
        page.get_pixmap(matrix=pymupdf.Matrix(4,4),clip=bounds).save(output/"captions"/(item["id"]+".png"))
        records.append(dict(item,caption_crop=list(bounds)))
    return records


def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from pathlib import Path
    for font in Path("C:/Windows/Fonts").glob("times*.ttf"):
        font_manager.fontManager.addfont(str(font))
    family = "Times New Roman" if any(f.name=="Times New Roman" for f in font_manager.fontManager.ttflist) else "DejaVu Serif"
    plt.rcParams.update({"font.family":family,"font.size":6,"axes.labelsize":6.5,"axes.labelweight":"bold",
                        "axes.linewidth":.55,"xtick.direction":"in","ytick.direction":"in",
                        "xtick.major.size":2.5,"ytick.major.size":2.5,"xtick.major.width":.5,"ytick.major.width":.5,
                        "xtick.major.pad":1.5,"ytick.major.pad":1.5,"axes.labelpad":1.8,
                        "mathtext.fontset":"stix","svg.fonttype":"path"})
    return plt, family


def canvas(plt, crop):
    l,t,r,b = crop
    fig = plt.figure(figsize=((r-l)/72,(b-t)/72))
    ax = fig.add_axes((0,0,1,1))
    ax.set(xlim=(l,r),ylim=(b,t))
    ax.set_axis_off()
    return fig, ax


def curves(ax, layers, style):
    from matplotlib.patches import Rectangle
    from matplotlib.path import Path
    clipped = []
    for row in layers:
        panel = style["panels"][row["panel"]]
        x = affine(np.asarray(row["x"]),panel["x"])
        scale = panel.get("display_scale",{}).get(row["field"],1)
        y = affine(np.asarray(row["y"])*scale,panel["y"][row["field"]])
        l,t,r,b = panel["rect"]
        line, = ax.plot(x,y,color=row["color"],linestyle="none" if row["marker"] else "-",
                        lw=style["line_width_pt"],marker=row["marker"],ms=style["marker_size_pt"],
                        mfc="none",mew=.5,solid_capstyle="butt")
        holes=panel.get("reference_insets",[])
        if holes:
            vertices=[(l,t),(r,t),(r,b),(l,b),(l,t)]
            codes=[Path.MOVETO,Path.LINETO,Path.LINETO,Path.LINETO,Path.CLOSEPOLY]
            for il,it,ir,ib in holes:
                vertices += [(il,it),(il,ib),(ir,ib),(ir,it),(il,it)]
                codes += [Path.MOVETO,Path.LINETO,Path.LINETO,Path.LINETO,Path.CLOSEPOLY]
            line.set_clip_path(Path(vertices,codes),ax.transData)
        else:
            line.set_clip_path(Rectangle((l,t),r-l,b-t,transform=ax.transData))
        visible = (x>=l)&(x<=r)
        clipped.append({"label":row["label"],"samples":len(x),"outside_x":int((~visible).sum()),
                        "outside_y_in_visible_x":int(np.sum(visible&((y<t)|(y>b))))})
    return clipped


def field_layer(fig, style, crop, contours, original):
    """Use true mesh edges; interpolate velocities only for streamline display."""
    from matplotlib.colors import ListedColormap
    import sys
    from common import REPLICATION
    sys.path.insert(0,str(REPLICATION/"validation/figures"))
    from foam_fields import list_body
    l,t,r,b=crop
    rgb=np.asarray(original.convert("RGB"))
    # Sample the unlabelled middle row of the original upper colour bar.
    y=int((61.2-t)/(b-t)*rgb.shape[0])
    x0=int((151.8-l)/(r-l)*rgb.shape[1]);x1=int((234.5-l)/(r-l)*rgb.shape[1])
    cmap=ListedColormap(rgb[y,x0:x1,:3]/255)
    for key, data in contours.items():
        panel=style["panels"][key];left,top,right,bottom=panel["rect"]
        ax=fig.add_axes(((left-l)/(r-l),(b-bottom)/(b-t),(right-left)/(r-l),(bottom-top)/(b-t)))
        xyz,f,radius=data["xyz"],data["fields"],data["radius"]
        # Polyhedral centroid summation introduces sub-nanometre roundoff.
        # Quantize only the structured-grid lookup, never the plotted field values.
        rr=np.unique(np.round(radius,10));zz=np.unique(np.round(xyz[:,2],10))
        if len(rr)*len(zz)!=len(xyz): raise ValueError("Contour requires a structured wedge")
        order=np.lexsort((np.round(xyz[:,2],10),np.round(radius,10)))
        shape=(len(rr),len(zz))
        _,text=list_body(data["case"]/"constant/polyMesh/points")
        points=np.fromstring(text.replace("("," ").replace(")"," "),sep=" ").reshape(-1,3)
        re=np.unique(np.round(np.hypot(points[:,0],points[:,1]),10));ze=np.unique(np.round(points[:,2],10))
        if len(re)!=len(rr)+1 or len(ze)!=len(zz)+1: raise ValueError("Contour edge count mismatch")
        temp=f["T"][order].reshape(shape).T
        ax.pcolormesh(re,ze,temp,cmap=cmap,vmin=panel["temperature_limits_K"][0],vmax=panel["temperature_limits_K"][1],shading="flat",rasterized=True)
        # Radial velocity is projected onto the local radial unit vector.
        ur=(f["U"][:,0]*xyz[:,0]+f["U"][:,1]*xyz[:,1])/radius
        ur=ur[order].reshape(shape);uz=f["U"][order,2].reshape(shape)
        rg=np.linspace(rr[0],rr[-1],len(rr));zg=np.linspace(zz[0],zz[-1],len(zz))
        def regular(v):
            rows=np.array([np.interp(rg,rr,v[:,j]) for j in range(len(zz))])
            return np.array([np.interp(zg,zz,rows[:,j]) for j in range(len(rg))]).T
        seeds=np.array([(x,z) for z in (zg[0],zg[-1]) for x in np.linspace(rg[0],rg[-1],10)])
        ax.streamplot(rg,zg,regular(ur),regular(uz),color="#a1eded",density=1,
                      start_points=seeds,broken_streamlines=False,linewidth=.4,arrowsize=.48,arrowstyle="->")
        ax.set(xlim=(re[0],re[-1]),ylim=(ze[0],ze[-1]));ax.set_axis_off()


def standalone(plt, crop, style, layers):
    from matplotlib.ticker import AutoMinorLocator, MaxNLocator
    fig=plt.figure(figsize=((crop[2]-crop[0])/72,(crop[3]-crop[1])/72))
    for index,(name,panel) in enumerate(style["panels"].items()):
        left,top,right,bottom=panel["rect"];l,t,r,b=crop
        ax=fig.add_axes(((left-l)/(r-l),(b-bottom)/(b-t),(right-left)/(r-l),(bottom-top)/(b-t)))
        def inverse(value, calibration):
            p0,v0,p1,v1=calibration
            return v0+(value-p0)*(v1-v0)/(p1-p0)
        ax.set_xlim(inverse(left,panel["x"]),inverse(right,panel["x"]))
        selected=[s for s in layers if s["panel"]==name]
        if not selected: continue
        calibrations=[]
        for row in selected:
            cal=panel["y"][row["field"]]
            if cal not in calibrations: calibrations.append(cal)
        axes=[ax]+[ax.twinx() for _ in calibrations[1:]]
        for axis,cal in zip(axes,calibrations):
            axis.set_ylim(inverse(bottom,cal),inverse(top,cal))
            axis.yaxis.set_major_locator(MaxNLocator(4))
            axis.yaxis.set_minor_locator(AutoMinorLocator())
        ax.xaxis.set_major_locator(MaxNLocator(4));ax.xaxis.set_minor_locator(AutoMinorLocator())
        for row in selected:
            axis=axes[calibrations.index(panel["y"][row["field"]])]
            scale=panel.get("display_scale",{}).get(row["field"],1)
            linestyle="none" if row["marker"] else "-"
            label=row["field"]+(f" x{scale}" if scale!=1 else "")
            if row["figure"]=="2022-fig06":
                pressure=int(row["label"].split()[-2]);label=f"{pressure} atm"
                linestyle={1:"-.",50:(0,(4,1,1,1)),100:(0,(2,2)),200:(0,(5,2)),300:"-"}[pressure]
            elif row["figure"]=="2025-fig06":label=row["label"].replace("Computed ","")
            elif row["figure"]=="2022-fig12":label=row["label"]
            axis.plot(row["x"],np.asarray(row["y"])*scale,color=row["color"],ls="none" if row["marker"] else "-",
                      marker=row["marker"],ms=style["marker_size_pt"],mfc="none",mew=.5,lw=style["line_width_pt"],label=label)
            axis.lines[-1].set_linestyle(linestyle)
        ax.set_xlabel("T [K]" if "fig06" in layers[0]["figure"] else ("Equivalence ratio" if name=="speed" else "z [m]"))
        units={"T":"Temperature [K]","rho":"Density [kg/m³]","Cp":"Cp [J/kg-K]","mu":"Viscosity [kg/m-s]","kappa":"Conductivity [W/m-K]","speed":"Speed [cm/s]"}
        for axis,cal in zip(axes,calibrations):
            fields=[k for k,v in panel["y"].items() if v==cal]
            axis.set_ylabel("Mass fraction" if name=="species" else units.get(fields[0],fields[0]))
        ax.text(-.12,1.01,chr(97+index)+")",transform=ax.transAxes,fontweight="bold",fontsize=8)
        if name in {"species","rho","a","b"}:
            ax.legend(fontsize=4.8,frameon=False,loc="best",handlelength=2)
    return fig


def data_legend(fig, ax, style, crop):
    """Place explicit data keys in inspected blank space; measure the painted bounds."""
    from matplotlib.transforms import Bbox
    artists=[]
    for entry in style["legend"]:
        x,y=entry["x"],entry["y"]
        marker=entry["marker"]
        line,=ax.plot([x,x+10] if not marker else [x+5], [y,y] if not marker else [y],
                     color=entry["color"],ls="none" if marker else "-",lw=style["line_width_pt"],
                     marker=marker,ms=style["marker_size_pt"],mfc="none",mew=.5,zorder=20)
        label=ax.text(x+13,y,entry["label"],fontsize=5.5,va="center",color="#222222",zorder=20)
        artists.extend([line,label])
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    bounds=Bbox.union([a.get_window_extent(renderer) for a in artists])
    (l,b),(r,t)=ax.transData.inverted().transform(bounds.get_points())
    # Include antialiasing and line caps in the frame-verification exclusion.
    rect=[float(l-1),float(t-1),float(r+1),float(b+1)]
    if not (crop[0]<=rect[0]<rect[2]<=crop[2] and crop[1]<=rect[1]<rect[3]<=crop[3]):
        raise ValueError(f"Legend leaves figure canvas: {rect}, crop {crop}")
    return rect


def render_all(inventory, styles, layers, contours, output, dpi):
    plt, family=setup_matplotlib()
    records={}
    for item in inventory:
        key=item["id"]
        if key not in styles: continue
        style=styles[key];crop=item["crop"]
        selected=[s for s in layers if s["figure"]==key]
        original=Image.open(output/"originals"/(key+".png"))
        fig,ax=canvas(plt,crop)
        clipped=curves(ax,selected,style)
        if key=="2022-fig08": field_layer(fig,style,crop,contours,original)
        legend_rect=data_legend(fig,ax,style,crop)
        for suffix in ("png","svg"):
            fig.savefig(output/"layers"/(key+"."+suffix),dpi=dpi,transparent=True)
        ax.imshow(original,extent=(crop[0],crop[2],crop[3],crop[1]),zorder=-10,aspect="auto")
        for suffix in ("png","svg"):
            fig.savefig(output/"overlays"/(key+"."+suffix),dpi=dpi)
        plt.close(fig)
        if selected:
            fig=standalone(plt,crop,style,selected)
            legend_ax=fig.add_axes((0,0,1,1),zorder=99,frameon=False)
            legend_ax.set(xlim=(crop[0],crop[2]),ylim=(crop[3],crop[1]));legend_ax.set_axis_off()
            data_legend(fig,legend_ax,style,crop)
            for suffix in ("png","svg"): fig.savefig(output/"standalone"/(key+"."+suffix),dpi=dpi)
            plt.close(fig)
        expected=(round((crop[2]-crop[0])*dpi/72),round((crop[3]-crop[1])*dpi/72))
        actual=Image.open(output/"overlays"/(key+".png")).size
        if actual!=expected: raise ValueError(f"Canvas changed: {key}: {actual} != {expected}")
        source_pixels=np.asarray(original.convert("RGB"))
        overlay_pixels=np.asarray(Image.open(output/"overlays"/(key+".png")).convert("RGB"))
        mask=np.ones(source_pixels.shape[:2],dtype=bool)
        for rect in [p["rect"] for p in style["panels"].values()]+[legend_rect]:
            l,t,r,b=rect
            x0=int((l-crop[0])*dpi/72)-3;x1=int((r-crop[0])*dpi/72)+4
            y0=int((t-crop[1])*dpi/72)-3;y1=int((b-crop[1])*dpi/72)+4
            mask[y0:y1,x0:x1]=False
        unchanged=float(np.mean(np.all(source_pixels[mask]==overlay_pixels[mask],axis=1)))
        if unchanged!=1: raise ValueError(f"Original frame changed outside data panels and legend: {key}")
        records[key]={"size_pt":[crop[2]-crop[0],crop[3]-crop[1]],"pixels":list(actual),"standalone_font":family,
                      "unchanged_frame_pixel_fraction":unchanged,
                      "legend":style["legend"],"legend_bounds_pt":legend_rect,
                      "frame":"original PDF outside data panels and added legend; published legends label published data only","clipping":clipped,
                      "overlay_sha256":digest(output/"overlays"/(key+".png"))}
    write_json(output/"data/rendering.json",records)
    return records
