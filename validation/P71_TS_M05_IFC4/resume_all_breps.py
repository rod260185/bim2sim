"""Resume full BRep audit using four local processes; no STEP export added."""
import concurrent.futures
import json
import multiprocessing
import time
from pathlib import Path
from types import SimpleNamespace
import ifcopenshell
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from bim2sim.elements.base_elements import ProductBased

out = Path(__file__).resolve().parent
f = None

def check(identifier):
    product = f.by_id(identifier)
    row = dict(id=identifier, guid=product.GlobalId, type=product.is_a())
    try:
        shape = ProductBased.calc_product_shape(SimpleNamespace(ifc=product))
        if shape is None or shape.IsNull():
            row['status'] = 'missing_or_null'
        else:
            row['status'] = 'valid' if BRepCheck_Analyzer(shape).IsValid() else 'invalid'
    except Exception as exc:
        row.update(status='exception', error=repr(exc))
    return row

def main():
    global f
    start = time.monotonic()
    f = ifcopenshell.open('/home/ferna/digital_twin_asset_forge/assets/P71_TS_M05_IFC4.ifc')
    products = [p.id() for p in f.by_type('IfcProduct') if p.Representation]
    records = {}
    for line in (out / 'all_breps.objects.jsonl').read_text().splitlines():
        try:
            row=json.loads(line)
            records[row['id']] = row
        except json.JSONDecodeError:
            pass
    result = dict(total=len(products), processed=0, non_null=0, valid=0, invalid=0, failed=0, complete=False, workers=4)
    def count(row):
        result['processed'] += 1
        if row['status'] in ('valid','invalid'):
            result['non_null'] += 1
            result[row['status']] += 1
        else:
            result['failed'] += 1
    for row in records.values(): count(row)
    result['resumed_after'] = len(records)
    def save():
        result['resume_elapsed_seconds'] = round(time.monotonic()-start,2)
        (out/'all_breps.progress.json').write_text(json.dumps(result,indent=2))
    with (out/'all_breps.objects.jsonl').open('w') as stream:
        for row in records.values(): stream.write(json.dumps(row)+'\n')
        stream.flush()
        with multiprocessing.get_context('fork').Pool(processes=4, maxtasksperchild=25) as pool:
            for row in pool.imap(check,[i for i in products if i not in records],chunksize=10):
                count(row)
                stream.write(json.dumps(row)+'\n')
                if result['processed'] % 100 == 0:
                    stream.flush()
                    save()
        stream.flush()
    result['complete'] = True
    save()
    print(json.dumps(result))

if __name__ == '__main__': main()
