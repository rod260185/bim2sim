"""Exercise existing ProductBased.calc_product_shape for every represented product.
This isolates the geometry method; it does not execute plugin classification or add STEP export.
"""
import gc
import json
import logging
import time
from pathlib import Path
from types import SimpleNamespace
import ifcopenshell
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from bim2sim.elements.base_elements import ProductBased

out = Path(__file__).resolve().parent
logging.basicConfig(filename=out / 'all_breps.warnings.log', level=logging.WARNING)
start = time.monotonic()
f = ifcopenshell.open('/home/ferna/digital_twin_asset_forge/assets/P71_TS_M05_IFC4.ifc')
products = [p for p in f.by_type('IfcProduct') if p.Representation]
result = dict(total=len(products), processed=0, non_null=0, valid=0, invalid=0, failed=0, complete=False)
with (out / 'all_breps.objects.jsonl').open('w') as stream:
    for i, product in enumerate(products, 1):
        row = dict(id=product.id(), guid=product.GlobalId, type=product.is_a())
        shape = None
        try:
            shape = ProductBased.calc_product_shape(SimpleNamespace(ifc=product))
            if shape is None or shape.IsNull():
                result['failed'] += 1
                row['status'] = 'missing_or_null'
            else:
                result['non_null'] += 1
                valid = BRepCheck_Analyzer(shape).IsValid()
                result['valid' if valid else 'invalid'] += 1
                row['status'] = 'valid' if valid else 'invalid'
        except Exception as exc:
            result['failed'] += 1
            row.update(status='exception', error=repr(exc))
        finally:
            del shape
        stream.write(json.dumps(row) + '\n')
        result['processed'] = i
        if i % 100 == 0 or i == len(products):
            stream.flush()
            result['elapsed_seconds'] = round(time.monotonic() - start, 2)
            (out / 'all_breps.progress.json').write_text(json.dumps(result, indent=2))
            gc.collect()
    result['complete'] = True
    result['elapsed_seconds'] = round(time.monotonic() - start, 2)
    (out / 'all_breps.progress.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
