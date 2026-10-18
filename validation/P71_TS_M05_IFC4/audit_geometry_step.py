"""Full geometry audit using bim2sim's shape method; STEP roundtrip per GUID.
Run with the bim2sim conda environment. Results are resumable by IFC entity ID.
STEP files are validation artifacts, not a new bim2sim plugin or merged model.
"""
import argparse
import csv
import json
import math
import multiprocessing as mp
import os
import time
from pathlib import Path
from types import SimpleNamespace

import ifcopenshell
import ifcopenshell.util.unit as units
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.Interface import Interface_Static
from OCC.Core.ShapeAnalysis import ShapeAnalysis_Shell
from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCC.Core.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from bim2sim.elements.base_elements import ProductBased

BASE = Path(__file__).resolve().parent
SOURCE = Path('/home/ferna/digital_twin_asset_forge/assets/P71_TS_M05_IFC4.ifc')
f = None
output = None

def parts(shape, kind, avoid=None):
    exp = TopExp_Explorer(shape, kind) if avoid is None else TopExp_Explorer(shape, kind, avoid)
    while exp.More():
        yield exp.Current()
        exp.Next()

def metrics(shape):
    shells = list(parts(shape, TopAbs_SHELL))
    solids = list(parts(shape, TopAbs_SOLID))
    open_shells = bad_shells = 0
    for shell in shells:
        check = ShapeAnalysis_Shell()
        check.CheckOrientedShells(shell, True, True)
        open_shells += int(check.HasFreeEdges())
        bad_shells += int(check.HasBadEdges())
    loose_faces = sum(1 for _ in parts(shape, TopAbs_FACE, TopAbs_SHELL))
    loose_shells = sum(1 for _ in parts(shape, TopAbs_SHELL, TopAbs_SOLID))
    valid = bool(BRepCheck_Analyzer(shape).IsValid())
    box = Bnd_Box()
    brepbndlib.AddOptimal(shape, box, False, False)
    bbox = list(box.Get()) if not box.IsVoid() else None
    area = GProp_GProps()
    brepgprop.SurfaceProperties(shape, area)
    volumes = []
    if valid and not open_shells and not bad_shells:
        for solid in solids:
            props = GProp_GProps()
            brepgprop.VolumeProperties(solid, props, True, False, False)
            volumes.append(props.Mass())
    closed_solid_geometry = bool(solids) and valid and not (open_shells or bad_shells or loose_faces or loose_shells) and len(volumes)==len(solids) and all(v>0 for v in volumes)
    return dict(valid=valid, faces=sum(1 for _ in parts(shape,TopAbs_FACE)), solids=len(solids), shells=len(shells), open_shells=open_shells,
                bad_shells=bad_shells, loose_faces=loose_faces, loose_shells=loose_shells,
                closed_solid_geometry=closed_solid_geometry,
                volume_m3=sum(volumes) if closed_solid_geometry else None,
                area_m2=area.Mass(), bbox_m=bbox,
                dimensions_m=[bbox[i+3]-bbox[i] for i in range(3)] if bbox else None)

def worker_init():
    # Suppress verbose native STEP transfer banners in workers only.
    fd=os.open(os.devnull,os.O_WRONLY)
    os.dup2(fd,1)
    os.close(fd)
    STEPControl_Writer()  # Initialize translator parameters before setting units.
    assert Interface_Static.SetCVal('write.step.unit','M')
    assert Interface_Static.SetCVal('xstep.cascade.unit','M')

def audit(identifier):
    product=f.by_id(identifier)
    row=dict(id=identifier,guid=product.GlobalId,name=product.Name,status='error')
    try:
        shape=ProductBased.calc_product_shape(SimpleNamespace(ifc=product))
        if shape is None or shape.IsNull(): raise ValueError('bim2sim returned no shape')
        before=metrics(shape)
        row['before']=before
        # Diagnostic sewing does not change the exported shape.
        sew=BRepBuilderAPI_Sewing(1e-6)
        sew.Add(shape)
        sew.Perform()
        sewn=sew.SewedShape()
        diagnostic=metrics(sewn)
        enclosed=[]
        if diagnostic['valid'] and not (diagnostic['open_shells'] or diagnostic['bad_shells'] or diagnostic['loose_faces']):
            for shell in parts(sewn,TopAbs_SHELL):
                props=GProp_GProps()
                brepgprop.VolumeProperties(shell,props,True,False,False)
                enclosed.append(props.Mass())
        diagnostic['absolute_shell_volume_sum_m3']=sum(abs(v) for v in enclosed) if enclosed and all(abs(v)>1e-12 for v in enclosed) else None
        diagnostic['volume_note']='Diagnostic sum of absolute closed-shell volumes; nesting/cavities not resolved, not certified net volume.'
        diagnostic['faces_preserved']=diagnostic['faces']==before['faces']
        row['sewing_diagnostic']=diagnostic
        # Read quantity values without modifying the shared source model.
        refs=[]
        for rel in getattr(product,'IsDefinedBy',[]):
            if not rel.is_a('IfcRelDefinesByProperties'): continue
            d=rel.RelatingPropertyDefinition
            if not d.is_a('IfcElementQuantity'): continue
            for q in d.Quantities:
                if not q.is_a('IfcQuantityVolume'): continue
                unit=q.Unit or units.get_project_unit(f,'VOLUMEUNIT')
                value=None
                if unit and unit.is_a('IfcSIUnit') and unit.Name=='CUBIC_METRE':
                    value=q.VolumeValue * (units.get_prefix_multiplier(unit.Prefix)**3)
                refs.append(dict(set=d.Name,name=q.Name,raw=q.VolumeValue,value_m3=value,unit_supported=value is not None))
        row['ifc_volume_candidates']=refs
        candidate=diagnostic['absolute_shell_volume_sum_m3']
        row['volume_comparisons']=[dict(name=q['name'],reference_m3=q['value_m3'],diagnostic_m3=candidate,relative_difference=abs(candidate-q['value_m3'])/abs(q['value_m3'])) for q in refs if candidate is not None and q['value_m3'] and q['name']=='NetVolume']
        row['quantity_reference_note']='Candidates only: Net/Gross meanings must be matched; no automatic correctness claim.'
        writer=STEPControl_Writer()
        transferred=writer.Transfer(shape,STEPControl_AsIs)
        row['transfer_status']=int(transferred)
        if transferred != IFSelect_RetDone: raise ValueError('STEP transfer failed')
        target=output/'step_by_guid'/f'{product.GlobalId}.stp'
        status=writer.Write(str(target))
        row['write_status']=int(status)
        if status != IFSelect_RetDone: raise ValueError('STEP write failed')
        text=target.read_text()
        if 'SI_UNIT($,.METRE.)' not in text or 'SI_UNIT(.MILLI.,.METRE.)' in text: raise ValueError('STEP length unit is not metre')
        row['step_length_unit']='metre'
        reader=STEPControl_Reader()
        status=reader.ReadFile(str(target))
        row['read_status']=int(status)
        if status != IFSelect_RetDone: raise ValueError('STEP read failed')
        row['step_roots']=reader.NbRootsForTransfer()
        row['transferred_roots']=reader.TransferRoots()
        restored=reader.OneShape()
        if restored.IsNull() or row['transferred_roots'] != row['step_roots'] or not row['step_roots']: raise ValueError('STEP roots incomplete')
        after=metrics(restored)
        row['after']=after
        differences={}
        topology_changes={}
        for key in ['valid','solids','shells','open_shells','bad_shells','loose_faces','loose_shells','closed_solid_geometry']:
            if before[key]!=after[key]: topology_changes[key]=[before[key],after[key]]
        for key in ['valid','solids','faces','closed_solid_geometry']:
            if before[key]!=after[key]: differences[key]=[before[key],after[key]]
        for key,abs_tol,rel_tol in [('area_m2',1e-8,1e-5),('volume_m3',1e-9,1e-5)]:
            a,b=before[key],after[key]
            if (a is None)!=(b is None) or (a is not None and not math.isclose(a,b,abs_tol=abs_tol,rel_tol=rel_tol)):
                differences[key]=[a,b]
        a,b=before['bbox_m'],after['bbox_m']
        if a is None or b is None or any(abs(x-y)>1e-6 for x,y in zip(a,b)):
            differences['bbox_m']=[a,b]
        row['topology_changes']=topology_changes
        row.update(status='roundtrip_difference' if differences else 'ok',differences=differences,step_file=str(target.relative_to(output)),step_bytes=target.stat().st_size)
    except Exception as exc:
        row['error']=repr(exc)
    return row

def main():
    global f,output
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit',type=int)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--output',type=Path,default=BASE/'geometry_step_audit')
    args=parser.parse_args()
    output=args.output.resolve()
    (output/'step_by_guid').mkdir(parents=True,exist_ok=True)
    f=ifcopenshell.open(str(SOURCE))
    identifiers=[p.id() for p in f.by_type('IfcProduct') if p.Representation]
    if args.limit: identifiers=identifiers[:args.limit]
    records={}
    journal=output/'objects.jsonl'
    if journal.exists():
        for line in journal.read_text().splitlines():
            try:
                row=json.loads(line)
                if row['id'] in identifiers and row['status']=='ok' and (output/row['step_file']).exists(): records[row['id']]=row
            except (ValueError,KeyError): pass
    start=time.monotonic()
    summary=dict(total=len(identifiers),processed=0,ok=0,error=0,roundtrip_difference=0,closed_solids=0,without_closed_solid=0,objects_with_ifc_volume=0,sewn_closed_shells=0,volume_candidates_agree_1pct=0,complete=False)
    def count(row):
        summary['processed']+=1
        summary[row['status']]+=1
        if 'before' in row:
            summary['closed_solids' if row['before']['closed_solid_geometry'] else 'without_closed_solid']+=1
        summary['objects_with_ifc_volume']+=bool(row.get('ifc_volume_candidates'))
        summary['sewn_closed_shells']+=row.get('sewing_diagnostic',{}).get('absolute_shell_volume_sum_m3') is not None
        summary['volume_candidates_agree_1pct']+=any(c['relative_difference']<=0.01 for c in row.get('volume_comparisons',[]))
    def save():
        summary['elapsed_seconds']=round(time.monotonic()-start,2)
        (output/'summary.json').write_text(json.dumps(summary,indent=2))
    for row in records.values(): count(row)
    with journal.open('w') as stream:
        for row in records.values(): stream.write(json.dumps(row)+'\n')
        stream.flush()
        with mp.get_context('fork').Pool(args.workers,initializer=worker_init,maxtasksperchild=10) as pool:
            for row in pool.imap(audit,[i for i in identifiers if i not in records],chunksize=5):
                records[row['id']]=row
                count(row)
                stream.write(json.dumps(row)+'\n')
                if summary['processed']%50==0:
                    stream.flush()
                    save()
    summary['complete']=set(records)==set(identifiers) and len(records)==len(identifiers)
    save()
    with (output/'objects.csv').open('w') as stream:
        fields=['id','guid','name','status','valid','solids','shells','open_shells','bad_shells','loose_faces','loose_shells','closed_solid_geometry','volume_m3','area_m2','dimensions_m','bbox_m','ifc_volume_candidates','sewing_diagnostic','volume_comparisons','topology_changes','step_file','error']
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        for row in records.values():
            flat={k:row.get(k) for k in fields}
            flat.update({k:v for k,v in row.get('before',{}).items() if k in fields})
            writer.writerow(flat)
    print(json.dumps(summary))

if __name__=='__main__': main()
