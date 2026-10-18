# Resultado após instalação — 16/10/2026

## Conclusão
A função existente no bim2sim consegue gerar BReps topologicamente válidos para todos os 26.239 produtos com representação do IFC P71_TS_M05_IFC4.ifc. O pipeline completo IFC → BRep → STEP não existe no checkout examinado: falta a tarefa de escrita STEP. Nenhum arquivo STEP completo foi gerado nesta execução.

## Ambiente
Python 3.11.17, IfcOpenShell 0.8.4, pythonocc-core 7.9.0, ambiente /home/ferna/miniforge3/envs/bim2sim. Imports da biblioteca e ativação USE_PYTHON_OPENCASCADE passaram. Commit 270cd0a36fa9cd0181503702dcb50f8e7f4bbf39, branch fernanda.

## Teste integral da etapa geométrica
Arquivo original aberto diretamente com ifcopenshell.open. Para cada IfcProduct com Representation, foi chamada a função original ProductBased.calc_product_shape usando um objeto mínimo com atributo ifc (SimpleNamespace), pois o método usa apenas esse atributo. A função foi importada do código real; não foi copiada ou substituída.
A configuração original usa USE_PYTHON_OPENCASCADE=True, USE_WORLD_COORDS=True e PRECISION=1e-6. Cada shape foi verificado com IsNull() e BRepCheck_Analyzer(shape).IsValid().

Foram processados 26.239 objetos: 26.239 BReps não nulos, 26.239 válidos, zero inválidos e zero falhas. Uma comparação independente de IDs com o IFC confirmou cobertura exata, sem duplicatas nem objetos faltantes. Ver all_breps.coverage.json e all_breps.objects.jsonl.

O teste começou sequencialmente e foi retomado preservando registros por ID em quatro processos locais. A versão final renova processos a cada 250 objetos para liberar memória nativa. Não houve retenção de todos os shapes nem escrita STEP. Os scripts e logs estão nesta pasta.

## Limites e próxima etapa
Este teste isola a função de geometria. Não executa Project.run, a classificação semântica dos plugins nem seus filtros, portanto não valida esses pipelines completos. Validade topológica não comprova que todos os BReps sejam sólidos fechados ou que volumes e dimensões estejam corretos.
A busca nos fontes e listas de tarefas dos plugins não encontrou exportação STEP. SerializeElements escreve pickle. Para produzir e validar um STEP completo, é necessário implementar a tarefa de escrita, contabilizar objetos transferidos, verificar os retornos do escritor e reabrir a saída em um leitor STEP.

Este resultado substitui o bloqueio de ambiente descrito na auditoria anterior. A tentativa anterior via binário IfcConvert foi independente e não integra este teste.
