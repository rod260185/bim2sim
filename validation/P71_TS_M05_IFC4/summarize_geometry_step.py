"""Verify journal coverage and produce a human-readable geometry/STEP audit."""
import csv
import json
import math
from collections import Counter
from pathlib import Path
import ifcopenshell

base=Path(__file__).resolve().parent
out=base/'geometry_step_audit'
rows=[json.loads(line) for line in (out/'objects.jsonl').read_text().splitlines()]
summary=json.loads((out/'summary.json').read_text())
f=ifcopenshell.open('/home/ferna/digital_twin_asset_forge/assets/P71_TS_M05_IFC4.ifc')
expected={p.id() for p in f.by_type('IfcProduct') if p.Representation}
actual={r['id'] for r in rows}
counts=Counter(r['status'] for r in rows)
sewn=Counter()
for r in rows:
 d=r.get('sewing_diagnostic',{})
 if not d: sewn['not_evaluated']+=1
 elif not d['valid']: sewn['invalid']+=1
 elif d['open_shells'] or d['bad_shells'] or d['loose_faces']: sewn['open_or_bad_or_loose']+=1
 elif d['absolute_shell_volume_sum_m3'] is not None: sewn['closed_volume_candidate']+=1
 else: sewn['closed_without_volume_candidate']+=1
comparisons=[c for r in rows for c in r.get('volume_comparisons',[])]
agree=[c for c in comparisons if c['relative_difference']<=0.01]
files_missing=[r['guid'] for r in rows if r.get('step_file') and not (out/r['step_file']).is_file()]
coverage=dict(expected=len(expected),records=len(rows),unique_ids=len(actual),unique_guids=len({r['guid'] for r in rows}),missing_ids=sorted(expected-actual),unexpected_ids=sorted(actual-expected),missing_files=files_missing)
complete=summary['complete'] and actual==expected and len(rows)==len(actual) and not files_missing
if summary['complete']: assert complete and len({r['guid'] for r in rows})==len(rows),coverage
stats=dict(complete=complete,coverage=coverage,statuses=dict(counts),sewing=dict(sewn),net_volume_comparisons=len(comparisons),net_volume_within_1pct=len(agree),net_volume_outside_1pct=len(comparisons)-len(agree),topology_reorganized=sum(bool(r.get('topology_changes')) for r in rows),step_bytes=sum(r.get('step_bytes',0) for r in rows),nonpositive_or_nonfinite_dimensions=sum(any(not math.isfinite(v) or v<=0 for v in r.get('before',{}).get('dimensions_m',[]) or []) for r in rows))
(out/'verified_summary.json').write_text(json.dumps(stats,indent=2))
fields=['guid','id','name','status','valid','solids','shells','open_shells','loose_faces','closed_solid_geometry','volume_m3','area_m2','dx_m','dy_m','dz_m','sewn_valid','sewn_shells','sewn_open_shells','sewn_bad_shells','sewn_loose_faces','sewn_faces_preserved','diagnostic_shell_volume_m3','ifc_net_volume_m3','diagnostic_relative_difference','topology_reorganized','step_length_unit','step_file','error']
with (out/'geometry_by_guid.csv').open('w',newline='') as stream:
 writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
 for r in rows:
  before=r.get('before',{});d=r.get('sewing_diagnostic',{});cmp=r.get('volume_comparisons',[])
  flat={k:r.get(k) for k in fields}
  flat.update({k:before.get(k) for k in fields if k in before})
  dims=before.get('dimensions_m') or [None]*3
  flat.update(dx_m=dims[0],dy_m=dims[1],dz_m=dims[2],sewn_valid=d.get('valid'),sewn_shells=d.get('shells'),sewn_open_shells=d.get('open_shells'),sewn_bad_shells=d.get('bad_shells'),sewn_loose_faces=d.get('loose_faces'),sewn_faces_preserved=d.get('faces_preserved'),diagnostic_shell_volume_m3=d.get('absolute_shell_volume_sum_m3'),ifc_net_volume_m3=cmp[0]['reference_m3'] if cmp else None,diagnostic_relative_difference=cmp[0]['relative_difference'] if cmp else None,topology_reorganized=bool(r.get('topology_changes')))
  writer.writerow(flat)
report=f'''# Auditoria de fechamento, medidas e STEP

Estado: **{'concluída com cobertura exata do IFC' if complete else 'EM EXECUÇÃO — resultados parciais'}**.

## Resultados

| Verificação | Objetos |
|---|---:|
| Esperados no IFC | {len(expected):,} |
| Auditados | {len(rows):,} |
| Ida e volta STEP sem divergências nas medidas e contagens essenciais | {counts['ok']:,} |
| Erros de processamento | {counts['error']:,} |
| Divergências após reabertura STEP | {counts['roundtrip_difference']:,} |
| Geometria original composta exclusivamente de sólidos fechados e válidos | {sum(r.get('before',{}).get('closed_solid_geometry',False) for r in rows):,} |
| Costura diagnóstica com candidato a volume de cascas fechadas | {sewn['closed_volume_candidate']:,} |
| Costura com abertura, borda problemática ou face solta | {sewn['open_or_bad_or_loose']:,} |
| NetVolume comparável ao candidato geométrico | {len(comparisons):,} |
| Comparações dentro de 1% | {len(agree):,} |
| Comparações acima de 1% | {len(comparisons)-len(agree):,} |
| Mudança na organização topológica do STEP | {stats['topology_reorganized']:,} |

Os arquivos STEP ocupam {stats['step_bytes']/1024**3:.2f} GiB. Há um arquivo por GUID, em `geometry_step_audit/step_by_guid/`. **Não foi produzido um único STEP consolidado**. O manifesto `objects.jsonl` relaciona os GUIDs aos arquivos e aos resultados antes/depois. `geometry_by_guid.csv` é o relatório tabular; `verified_summary.json` documenta cobertura e agregações.

## Método e tolerâncias

A geometria de origem foi criada pela função original `ProductBased.calc_product_shape()` do bim2sim, chamada diretamente por produto. Não foram executados os filtros semânticos nem `Project.run()`. Ambiente Python 3.11, IfcOpenShell 0.8.4, pythonocc-core 7.9.0.

Foram contados sólidos, cascas, faces soltas e cascas fora de sólidos. Validade: `BRepCheck_Analyzer`; bordas livres e orientação das cascas: `ShapeAnalysis_Shell`. Caixa envolvente: `BRepBndLib.AddOptimal` sem triangulação e sem ampliar por tolerâncias. Área: `BRepGProp.SurfaceProperties`. Volume de sólidos só é apresentado se toda a geometria é válida, fechada e com volumes positivos.

A costura (`BRepBuilderAPI_Sewing`, 1e-6 m) é exclusivamente diagnóstica. **A geometria costurada não substitui a geometria exportada e não é convertida automaticamente em sólido.** Conta de faces preservadas é registrada por objeto. Quando cascas fechadas válidas são obtidas, a soma dos módulos dos volumes das cascas é um candidato diagnóstico; não resolve aninhamento e cavidades e não certifica volume líquido. A comparação com `NetVolume` de quantidades IFC é exploratória: diferenças acima de 1% são sinalizadas, não declaradas erros de projeto. Unidades explícitas de volume fora de IfcSIUnit CUBIC_METRE não foram convertidas automaticamente.

O ensaio STEP usa `STEPControl_Writer` em modo AsIs. Retornos de Transfer, Write e ReadFile são verificados, assim como transferência de todas as raízes. Parâmetros do tradutor e declaração física do arquivo são verificados em **metros**. Após reabertura com `STEPControl_Reader`, são comparados validade, número de faces, número de sólidos e condição de sólido fechado. Reorganizações de faces/cascas são registradas à parte e não são tratadas automaticamente como perda geométrica.

Tolerâncias da ida e volta: coordenadas dos seis limites da caixa até 1e-6 m; área com tolerância absoluta 1e-8 m² ou relativa 1e-5; volume (quando definido) com absoluta 1e-9 m³ ou relativa 1e-5. Não é um teste de distância de Hausdorff ou equivalência exata das superfícies.

## Interpretação

BRep topologicamente válido pode ser somente uma coleção de faces. Uma exportação STEP que preserva medidas também não transforma essas faces em sólidos. As dimensões registradas são de uma caixa alinhada aos eixos globais; não equivalem automaticamente a comprimento, largura ou altura de projeto de um objeto girado. A concordância antes/depois demonstra preservação dessas medidas pelo ensaio, não exatidão em relação ao projeto físico. Essa exatidão requer medidas e referências de projeto com significado e tolerâncias compatíveis.

Os testes de controle usaram uma caixa 2 × 3 × 4 m (24 m³) e uma face aberta, além da ida e volta dos três primeiros objetos. Scripts: `audit_geometry_step.py` e `summarize_geometry_step.py`. Para executar, ativar o ambiente bim2sim, entrar na raiz do repositório e executar os scripts com Python, nessa ordem. A auditoria retoma os objetos já aprovados no manifesto; a origem e o código devem permanecer os mesmos para uma retomada válida.
'''
(base/'AUDITORIA_GEOMETRIA_STEP.md').write_text(report)
print(json.dumps({k:v for k,v in stats.items() if k!='coverage'},indent=2))
