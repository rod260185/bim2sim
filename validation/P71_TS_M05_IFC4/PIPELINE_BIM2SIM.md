# Auditoria do pipeline existente — 16/10/2026

## Resultado
O checkout atual não implementa um pipeline completo IFC → OpenCascade/BRep → STEP. Não foi possível executar essa conversão com a biblioteca tal como está. Nenhum STEP completo foi gerado nesta auditoria.

## Evidências no código
- `bim2sim/elements/base_elements.py:24-27`: configura IfcOpenShell com USE_PYTHON_OPENCASCADE=True, USE_WORLD_COORDS=True e precisão 1e-6.
- `bim2sim/elements/base_elements.py:550-559`: calc_product_shape chama ifcopenshell.geom.create_shape(settings_products, self.ifc).geometry. Essa é a ponte para a geometria OpenCascade. Exceções são capturadas e geram apenas um warning; um elemento pode ficar sem shape.
- `bim2sim/tasks/common/create_elements.py:39-90`: criação seleciona elementos relevantes à simulação, valida e classifica; não é uma passagem garantida de todos os produtos geométricos do IFC. Proxies entram na classificação e podem exigir decisão do usuário.
- `bim2sim/plugins/PluginTemplate/bim2sim_template/__init__.py:13`: pipeline padrão carrega IFC, cria elementos e fronteiras espaciais, enriquece condições e relações, e trata clima. Não exporta STEP.
- Inspeção das listas default_tasks dos demais plugins e busca em todos os fontes Python não localizaram escritor/exportador STEP.
- `bim2sim/tasks/common/serialize_elements.py:35-40`: SerializeElements escreve pickle com dados de elementos, não um arquivo CAD STEP.

## Tentativas de execução
`/home/ferna/venvs/default/bin/python -c "import bim2sim"` falhou com ModuleNotFoundError: No module named 'pint'. O ambiente é Python 3.12, enquanto pyproject.toml declara >=3.10,<3.12. O teste isolado de USE_PYTHON_OPENCASCADE também falhou por ausência de Python OpenCascade (ver logs).
A documentação local recomenda Python 3.11, pythonocc-core=7.9.0 via conda-forge e instalação das dependências da biblioteca. Corrigir o ambiente não adiciona a etapa STEP ausente.

## Alcance da conclusão
É uma auditoria do pipeline existente, com tentativas de inicialização; não é validação dinâmica dos 26.239 BReps. O teste anterior via binário IfcConvert é independente do pipeline bim2sim e não comprova seu funcionamento.
Para atender à conversão completa é necessário implementar uma tarefa de exportação STEP, definir cobertura de todos os produtos, contabilizar shapes ausentes e falhas, e validar a saída por reabertura e comparação de cobertura. Só então executar com memória suficiente ou estratégia de processamento apropriada.
