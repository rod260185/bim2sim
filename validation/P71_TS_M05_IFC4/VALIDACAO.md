# Validação IFC para STEP — 16/10/2026

Origem: `/home/ferna/digital_twin_asset_forge/assets/P71_TS_M05_IFC4.ifc` (118 MiB).
IFC4: 26.242 IfcProduct, sendo 26.239 com representação. Todos os produtos representados são IfcBuildingElementProxy com MappedRepresentation.

## bim2sim

Branch fernanda, commit 270cd0a36fa9cd0181503702dcb50f8e7f4bbf39.
A inspeção do código não encontrou exportador STEP. A biblioteca se destina à geração de modelos de simulação. O pyproject exige Python >=3.10,<3.12; o ambiente examinado possui Python 3.12 e não possui OCC. Não foi instalada nem executada a biblioteca bim2sim.

## Conversão alternativa testada

Executável local: `/home/ferna/digital_twin_asset_forge/bin/IfcConvert`.
Versão reportada: 0.9.0post1+b5e509b. Saída STEP usa extensão .stp.

A tentativa com o arquivo completo foi interrompida manualmente (SIGTERM, código 143) após aproximadamente 7 minutos devido à pressão de memória: cerca de 5,2 GB RSS, 318 MB de RAM disponível e swap crescente. Nenhum STEP completo foi gerado. Isso não demonstra um erro geométrico no arquivo.

A amostra dos primeiros 100 produtos representados (GUIDs em sample_guids.json) converteu em 5 segundos, com código 0, usando --fail-on-error. O conversor reportou 100 objetos e o log de erros ficou vazio. Artefato: sample_100.stp. Verificações estruturais em sample.structure.json.

Limites: amostra sequencial, sem garantia de representatividade; sem reabertura em aplicativo CAD ou validação de fechamento/volume dos sólidos. A conversão completa e a fidelidade geométrica do modelo inteiro não estão validadas. Não se deve presumir preservação de propriedades semânticas IFC no STEP.

O script reproduce.sh reproduz a tentativa completa; executá-lo requer recursos adicionais ou uma estratégia de divisão do modelo.
