# Auditoria de fechamento, medidas e STEP

Estado: **EM EXECUÇÃO — resultados parciais**.

## Resultados

| Verificação | Objetos |
|---|---:|
| Esperados no IFC | 26,239 |
| Auditados | 13,824 |
| Ida e volta STEP sem divergências nas medidas e contagens essenciais | 13,824 |
| Erros de processamento | 0 |
| Divergências após reabertura STEP | 0 |
| Geometria original composta exclusivamente de sólidos fechados e válidos | 0 |
| Costura diagnóstica com candidato a volume de cascas fechadas | 5,491 |
| Costura com abertura, borda problemática ou face solta | 8,333 |
| NetVolume comparável ao candidato geométrico | 5,491 |
| Comparações dentro de 1% | 5,008 |
| Comparações acima de 1% | 483 |
| Mudança na organização topológica do STEP | 13,824 |

Os arquivos STEP ocupam 18.51 GiB. Há um arquivo por GUID, em `geometry_step_audit/step_by_guid/`. **Não foi produzido um único STEP consolidado**. O manifesto `objects.jsonl` relaciona os GUIDs aos arquivos e aos resultados antes/depois. `geometry_by_guid.csv` é o relatório tabular; `verified_summary.json` documenta cobertura e agregações.

## Método e tolerâncias

A geometria de origem foi criada pela função original `ProductBased.calc_product_shape()` do bim2sim, chamada diretamente por produto. Não foram executados os filtros semânticos nem `Project.run()`. Ambiente Python 3.11, IfcOpenShell 0.8.4, pythonocc-core 7.9.0.

Foram contados sólidos, cascas, faces soltas e cascas fora de sólidos. Validade: `BRepCheck_Analyzer`; bordas livres e orientação das cascas: `ShapeAnalysis_Shell`. Caixa envolvente: `BRepBndLib.AddOptimal` sem triangulação e sem ampliar por tolerâncias. Área: `BRepGProp.SurfaceProperties`. Volume de sólidos só é apresentado se toda a geometria é válida, fechada e com volumes positivos.

A costura (`BRepBuilderAPI_Sewing`, 1e-6 m) é exclusivamente diagnóstica. **A geometria costurada não substitui a geometria exportada e não é convertida automaticamente em sólido.** Conta de faces preservadas é registrada por objeto. Quando cascas fechadas válidas são obtidas, a soma dos módulos dos volumes das cascas é um candidato diagnóstico; não resolve aninhamento e cavidades e não certifica volume líquido. A comparação com `NetVolume` de quantidades IFC é exploratória: diferenças acima de 1% são sinalizadas, não declaradas erros de projeto. Unidades explícitas de volume fora de IfcSIUnit CUBIC_METRE não foram convertidas automaticamente.

O ensaio STEP usa `STEPControl_Writer` em modo AsIs. Retornos de Transfer, Write e ReadFile são verificados, assim como transferência de todas as raízes. Parâmetros do tradutor e declaração física do arquivo são verificados em **metros**. Após reabertura com `STEPControl_Reader`, são comparados validade, número de faces, número de sólidos e condição de sólido fechado. Reorganizações de faces/cascas são registradas à parte e não são tratadas automaticamente como perda geométrica.

Tolerâncias da ida e volta: coordenadas dos seis limites da caixa até 1e-6 m; área com tolerância absoluta 1e-8 m² ou relativa 1e-5; volume (quando definido) com absoluta 1e-9 m³ ou relativa 1e-5. Não é um teste de distância de Hausdorff ou equivalência exata das superfícies.

## Interpretação

BRep topologicamente válido pode ser somente uma coleção de faces. Uma exportação STEP que preserva medidas também não transforma essas faces em sólidos. As dimensões registradas são de uma caixa alinhada aos eixos globais; não equivalem automaticamente a comprimento, largura ou altura de projeto de um objeto girado. A concordância antes/depois demonstra preservação dessas medidas pelo ensaio, não exatidão em relação ao projeto físico. Essa exatidão requer medidas e referências de projeto com significado e tolerâncias compatíveis.

Os testes de controle usaram uma caixa 2 × 3 × 4 m (24 m³) e uma face aberta, além da ida e volta dos três primeiros objetos. Scripts: `audit_geometry_step.py` e `summarize_geometry_step.py`. Para executar, ativar o ambiente bim2sim, entrar na raiz do repositório e executar os scripts com Python, nessa ordem. A auditoria retoma os objetos já aprovados no manifesto; a origem e o código devem permanecer os mesmos para uma retomada válida.
