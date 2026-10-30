"""Offline physical manifold review with exact input identities and no acceptance."""
import argparse
import hashlib
import html
import json
from pathlib import Path

import numpy as np

C,T,H,RHO,SC,Q = range(6)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--physical-input',type=Path,help='Original branches for a separately derived table')
    parser.add_argument('--plan',action='store_true')
    args = parser.parse_args()
    receipt = read(args.input/'receipt.json')
    assert receipt['status'] == 'diagnostic_table_exported_not_accepted', receipt['status']
    assert receipt['progress_species'] == ['CO2','CO','H2O']
    inputs = {'receipt.json':sha(args.input/'receipt.json')}
    physical_input = args.physical_input or args.input
    if args.physical_input:
        inputs['physical-receipt.json'] = sha(physical_input/'receipt.json')
        assert inputs['physical-receipt.json'] == receipt['original_receipt_sha256']
    for name in ['table.npz','diagnostics.json','heldout.json']:
        inputs[name] = sha(args.input/name)
        assert inputs[name] == receipt['artifacts'][name], name+' identity mismatch'
    diagnostics,heldout = read(args.input/'diagnostics.json'),read(args.input/'heldout.json')
    with np.load(args.input/'table.npz') as archive:
        data = {name:archive[name] for name in archive.files}
    z,eta,states = data['Z'],data['eta'],data['states']
    assert states.shape[:2] == (len(z),len(eta)) and np.isfinite(states).all()
    case_by_index = {row['Z_index']:row for row in receipt['cases']}
    selected = []
    for target in [.1,.2,.2865,.6]:
        index = min(case_by_index,key=lambda j:abs(case_by_index[j]['Z']-target))
        case = case_by_index[index]
        branch_root=args.input if case.get('retained_original_branch') is False else physical_input
        path = branch_root/f'z-{index:03d}'
        if not (path/'branch.npz').exists():
            continue
        assert sha(path/'branch.npz') == case['branch_sha256']
        assert sha(path/'tail-receipt.json') == case['receipt_sha256']
        with np.load(path/'branch.npz') as archive:
            branch = archive['states'].copy()
        tail = None
        if (path/'chemical-tail.npz').exists():
            with np.load(path/'chemical-tail.npz') as archive:
                tail = archive['states'].copy()
        for name in ['branch.npz','tail-receipt.json','chemical-tail.npz']:
            if (path/name).exists(): inputs[f'z-{index:03d}/'+name] = sha(path/name)
        selected.append((index,case,branch,tail))
    physical_source=receipt.get('physical_source_commit',receipt['source_commit'])
    physical_job=receipt.get('physical_job_id',receipt['job_id'])
    plan = {'job_id':receipt['job_id'],'derivation_source':receipt['source_commit'],
            'physical_source':physical_source,'physical_job_id':physical_job,
            'inputs_sha256':inputs,'selected_Z_indices':[r[0] for r in selected],
            'selected_physical_sources':[{'Z_index':index,'source':case.get('physical_source_commit',physical_source),
                'job_id':case.get('physical_job_id',physical_job),'retained_original_branch':case.get('retained_original_branch')}
                for index,case,branch,tail in selected],
            'scientific_acceptance':False}
    if args.plan:
        print(json.dumps(plan,indent=2));return
    assert not args.out.exists(), 'Use a fresh output directory'
    args.out.mkdir(parents=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import SymLogNorm
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.labelsize':12,
        'axes.titlesize':12,'legend.fontsize':9,'lines.linewidth':1.8,'axes.spines.top':False,
        'axes.spines.right':False,'savefig.dpi':180})
    figures = []

    def save(fig,name,title,caption):
        fig.tight_layout()
        for extension in ['png','svg']: fig.savefig(args.out/(name+'.'+extension),bbox_inches='tight')
        plt.close(fig)
        figures.append({'name':name,'title':title,'caption':caption})

    fig,axes = plt.subplots(1,2,figsize=(11,4))
    axes[0].plot(z,data['Cmax'],'o-',ms=3,label='Measured selected upper cap')
    axes[0].plot(z,data['Cmin'],'--',label='Measured lower cap')
    axes[0].set(xlabel='Mixture fraction Z',ylabel=r'Raw $C_w=Y_{CO_2}+Y_{CO}+Y_{H_2O}$')
    axes[0].legend()
    for key,label,marker in [('upper_source_bounds','Upper cap','o'),('lower_source_bounds','Lower cap','x')]:
        rows = diagnostics[key]
        axes[1].plot([r['Z'] for r in rows],[r['Scwater'] for r in rows],marker,ms=4,label=label)
    axes[1].axhline(0,color='.4',lw=.8)
    axes[1].set(xlabel='Mixture fraction Z',ylabel=r'$S_{C_w}$ [kg m$^{-3}$ s$^{-1}$]',yscale='symlog')
    all_caps=[row['Scwater'] for key in ['upper_source_bounds','lower_source_bounds'] for row in diagnostics[key]]
    axes[1].set_ylim(min(min(all_caps)*1.8,-2),max(max(all_caps)*1.8,2))
    axes[1].legend()
    save(fig,'bounds','Physical coverage and source bounds',
        f"Upper outward nodes: {len(diagnostics['outward_upper_nodes'])}; lower outward nodes: {len(diagnostics['outward_lower_nodes'])}. Positive upper source is retained. A written table is not proof that reactions remain inside its bounds.")

    fig,axes = plt.subplots(1,2,figsize=(11,4))
    image = axes[0].pcolormesh(z,eta,states[:,:,T].T,shading='nearest',cmap='inferno')
    fig.colorbar(image,ax=axes[0],label='Temperature [K]')
    source = states[:,:,SC]
    peak = max(float(np.max(np.abs(source))),1)
    image = axes[1].pcolormesh(z,eta,source.T,shading='nearest',cmap='coolwarm',
        norm=SymLogNorm(linthresh=max(peak*1e-5,1),vmin=-peak,vmax=peak))
    fig.colorbar(image,ax=axes[1],label=r'$S_{C_w}$ [kg m$^{-3}$ s$^{-1}$]',
                 ticks=[-1e7,-1e5,-1e3,0,1e3,1e5,1e7])
    for axis in axes: axis.set(xlabel='Mixture fraction Z',ylabel='Local table coordinate η')
    save(fig,'surface','Actual table temperature and chemistry',
        'η maps local measured Cmin to Cmax. It is not Sharma’s equilibrium-normalized CO₂+CO coordinate. Sources were recomputed from the unchanged GRI mechanism; this is an approximate hybrid manifold.')

    if selected:
        fig,axes = plt.subplots(2,2,figsize=(11,7))
        fields = [(T,'Temperature [K]'),(SC,r'$S_{C_w}$ [kg m$^{-3}$ s$^{-1}$]'),
                  (Q,r'$Q_f$ [W m$^{-3}$]'),(H,'Specific total enthalpy [J kg⁻¹]')]
        for axis,(field,label) in zip(axes.flat,fields):
            for index,case,branch,tail in selected:
                line, = axis.plot(branch[:,C],branch[:,field],label=f"Z={case['Z']:.4f} selected")
                if tail is not None:
                    axis.plot(tail[:,C],tail[:,field],':',lw=1,color=line.get_color(),alpha=.7)
            axis.set(xlabel=r'Raw $C_w$',ylabel=label)
            if field in (SC,Q): axis.set_yscale('symlog',linthresh=1)
            if field==SC: axis.set_yticks([-1e4,-1e2,0,1e2,1e4,1e6,1e8])
            if field==Q: axis.set_yticks([-1e12,-1e8,-1e4,0,1e4,1e8,1e12,1e14])
        axes[0,0].legend(ncol=2)
        save(fig,'branches','Retained physical branches',
            'Solid: selected cold-quench plus chemical branch. Dotted: every accepted state of the fresh homogeneous chemical tail, including states omitted from the one-coordinate branch. No trajectory is smoothed or forced to zero source.')

    fig,axes = plt.subplots(1,2,figsize=(11,4))
    fields = ['T_K','rho_kg_m3','h_J_kg','Scwater_kg_m3_s','Qformation_W_m3','Y_CH4','Y_O2','Y_CO2','Y_CO','Y_H2O','Y_OH']
    values = [heldout['fields'][name]['rms_over_true_global_peak'] for name in fields]
    labels=['Temperature','Density','Enthalpy','Progress source','Formation Q','Y(CH₄)','Y(O₂)','Y(CO₂)','Y(CO)','Y(H₂O)','Y(OH)']
    axes[0].barh(labels,values,color='#286f91')
    axes[0].set(xlabel='RMS error / actual held-out global peak')
    for region,marker,color in [('cold','o','#286f91'),('chemical','s','#e58532')]:
        rows = [r for r in diagnostics['source_projection'] if r['region']==region]
        for sparse in [False,True]:
            group=[r for r in rows if (r['nodes']<3)==sparse]
            if not group: continue
            axes[1].scatter([r['Z'] for r in group],[r['Q_error_rms_over_region_peak'] for r in group],
                marker=marker,s=24,edgecolors=color,facecolors='none' if sparse else color,
                label=region+(' (1–2 nodes)' if sparse else ' (≥3 nodes)'))
    axes[1].set(xlabel='Mixture fraction Z',ylabel='Projected Q RMS error / region peak',yscale='log')
    axes[1].legend()
    save(fig,'errors','Independent-Z and energy-projection diagnostics',
        f"{heldout['count']} covered held-out observations; {len(heldout['coverage_failures'])} outside the training envelope; {len(heldout['missing_heldout_Z_indices'])} missing held-out branches. Energy projection compares −Σhf(dY/dCw)Scw with full mechanism Qf. Different denominators are explicitly labelled; no automatic pass threshold.")
    body = ''.join(f'<section id="{r["name"]}"><h2>{html.escape(r["title"])}</h2><img src="{r["name"]}.png" alt="{html.escape(r["title"])}"><p>{html.escape(r["caption"])}</p></section>' for r in figures)
    source = html.escape(receipt['source_commit'])
    retained_note=''
    if receipt.get('previous_physical_source_commit'):
        retained_note=f" Retained branches also use physical job {html.escape(receipt['previous_physical_job_id'])}, source {html.escape(receipt['previous_physical_source_commit'])}; the manifest identifies every displayed branch."
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Physical water-progress manifold review</title><style>body{{font:17px/1.6 system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;color:#16242c}}img{{max-width:100%}}section{{margin:45px 0}}.note{{background:#fff3d6;padding:18px}}code{{overflow-wrap:anywhere}}</style><h1>Physical water-progress manifold review</h1><p class="note">Diagnostic only. This is an ideal-gas GRI, 5.61 MPa quench/chemistry hybrid using CO₂+CO+H₂O. It is neither a paper-replication verdict nor a qualified reacting CFD closure.</p><p>Table job {html.escape(receipt['job_id'])}, source <code>{source}</code>; physical job {html.escape(physical_job)}, source <code>{html.escape(physical_source)}</code>. Original table and failed CFD remain unchanged. <a href="manifest.json">Exact input and rendering record</a>.</p>{body}</html>'''
    page=page.replace('Original table and failed CFD remain unchanged.', 'Original table and failed CFD remain unchanged.'+retained_note)
    (args.out/'index.html').write_text(page,encoding='utf8')
    plan.update(figures=figures,renderer_sha256=sha(Path(__file__)),artifacts_sha256={p.name:sha(p) for p in args.out.iterdir() if p.is_file()})
    (args.out/'manifest.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
    print(json.dumps({'output':str(args.out),'figures':len(figures),'scientific_acceptance':False}))


if __name__ == '__main__':
    main()
