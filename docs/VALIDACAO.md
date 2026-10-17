# Validação e limites observados

## Verificações automatizadas

Na retomada de 17/10/2026, 36 testes passaram, incluindo integração PostgreSQL/pgvector em schema isolado. Cobrem limpeza e negações, cardinalidade de junções, datas de compra e avaliação, atraso e dados ausentes, retomada da ingestão, parâmetros SQL, referências inválidas, bloqueio de chamadas pagas, autenticação, origem, rate limit, métricas e substituição de paráfrases inventadas pelo texto original no modo extrativo.

Um backup real foi restaurado em um banco temporário, com conferência da coleção ativa de 2.000 documentos e execução de consulta vetorial. O backup também continha a coleção completa ainda em construção. O banco temporário foi removido ao fim do ensaio. Foi necessário ignorar comentários na restauração para não alterar o comentário da extensão `vector`, que pertence ao administrador.

A suíte emite um aviso de depreciação da combinação Starlette/TestClient/httpx. Os testes passaram com as versões fixadas; o aviso não foi suprimido. Docker não estava instalado na máquina de validação: a execução nativa foi testada, e o workflow de CI inclui o build do container. Consulte o resultado real da CI antes de afirmar que o caminho Docker foi validado.

## Qualidade das respostas

Os nove casos de aceitação verificam resultado esperado, filtros e transcrições. Passar nesses critérios **não prova fidelidade semântica**. Na revisão manual do modo de síntese, observou-se, por exemplo, a inclusão de “sem desculpas” em um comentário que não mencionava desculpas. O verificador, que usa o mesmo modelo, não detectou todos os acréscimos.

Por isso, o modo padrão passou a ser `extractive`: Qwen seleciona referências relevantes e o código apresenta o texto original dessas referências. A saída continua dependendo da recuperação e da seleção da IA, mas não exibe as paráfrases não verificadas. `summary` permanece uma opção experimental, nunca recomendada como equivalente em confiabilidade.

O arquivo `evaluation_postgres.json` registra a última execução do avaliador, com coleção, filtros, referências, modelos, modo da resposta e duração. `evaluation_results.json` registra o protótipo NumPy anterior e não é evidência de validação da versão PostgreSQL. Os casos foram usados no desenvolvimento; não são um conjunto independente.

## O que ainda precisa de avaliação para uso real

Relevância anotada por humanos, recall da recuperação sob filtros seletivos, perguntas adversariais, desempenho concorrente, proteção de dados, política de retenção e disponibilidade. A autenticação atual usa token compartilhado; não há isolamento por organização, SSO, autoscaling ou alta disponibilidade. A interface deve ser revisada visualmente no navegador; testes HTTP/JavaScript não substituem essa revisão.

Não há garantia de ausência de alucinação no modo de síntese, nem de relevância perfeita no modo extrativo. O corpus é histórico, contém opiniões subjetivas e não representa todos os clientes atuais.
