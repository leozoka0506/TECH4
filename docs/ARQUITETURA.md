# Arquitetura e decisões

## Preparação

A fonte é o Brazilian E-Commerce Public Dataset by Olist. O foco textual vem de `order_reviews`, enriquecido por `orders`, `order_items` e `products`. Não são importados nomes, endereços ou pagamentos: eles não são necessários para o objetivo.

Título e comentário são concatenados, espaços em branco normalizados e texto vazio removido. Preservam-se acentos, pontuação e negações: remover “não” mudaria o sentido. Notas inválidas e IDs essenciais ausentes são descartados. Duplicatas exatas da mesma avaliação/pedido/nota/data/texto são removidas; textos iguais de pedidos diferentes são preservados. A identidade do documento é derivada desses campos com SHA-256. A linha no CSV, review_id e order_id permitem rastrear a origem.

Nesta versão da base foram lidas 99.224 avaliações e aproveitadas 42.687 com título ou comentário; 56.537 eram vazias. O manifest registra contagens e SHA-256 de cada arquivo. A política não “corrige” opinião, ortografia ou avaliação negativa.

O cadastro de pedidos e produtos deve ter chaves únicas. Itens são primeiro agregados por pedido, evitando multiplicar avaliações em uma junção 1:N. Metadados incluem nota, data da avaliação, data da compra, status do pedido, produtos, quantidade de itens, categorias, data de entrega, prazo estimado e atraso em dias. Entrega no mesmo dia prometido é considerada no prazo, independentemente do horário. Ausência de datas é “desconhecida”, nunca “no prazo”. Categoria é do pedido, não prova de qual item motivou o comentário.

## Documentos e embeddings

Uma avaliação curta constitui um documento completo; os comentários deste corpus não justificam fragmentação arbitrária. Isso preserva o contraste entre elogios e críticas no mesmo relato. EmbeddingGemma usa prefixos distintos para documento e consulta; os vetores de 768 dimensões são normalizados. As configurações padrão usam quantização e CPU para caber em hardware modesto. A dimensão, o provedor e o nome do modelo devem coincidir entre consulta e ingestão.

Uma coleção é identificada pelo hash do manifest, incluindo arquivos, política de preparação, seleção, modelo e dimensão. Cada lote é transacional e a ingestão é retomável. A ativação usa lock e transação e verifica o número esperado de documentos; uma ingestão incompleta não substitui a versão anterior. Modelos com o mesmo nome podem mudar no provedor: conserve seus artefatos/digests para reprodução rigorosa e reconstrua a coleção se trocar pesos. Uma mudança da dimensão exige outro banco.

## Recuperação

O PostgreSQL armazena corpo, metadados JSONB e embedding. Há HNSW para distância de cosseno, GIN para busca textual em português e índices de metadados. Recuperam-se até 40 candidatos semânticos e 40 textuais, combinados por Reciprocal Rank Fusion com constante 60. O limiar mínimo de cosseno vale também para candidatos textuais. Textos idênticos são deduplicados apenas na montagem do contexto; os registros continuam na base.

Filtros são parametrizados e atuam nas consultas SQL antes do `LIMIT`. HNSW é aproximado; varredura iterativa ajuda a recuperar candidatos sob filtros seletivos, mas não garante recall perfeito. O planejador pode preferir busca exata em recortes pequenos. Top-k padrão 6, máximo 10; contexto textual limitado a 10.000 caracteres. Limiar 0,35 é uma escolha experimental, não uma medida de confiança.

Os metadados melhoram a recuperação por restringir a investigação ao recorte desejado: nota delimita satisfação; compra seleciona o período correto; status e entrega distinguem experiência percebida de prazo observado; categoria segmenta pedidos. Os filtros não são inferidos automaticamente da pergunta: o usuário os seleciona na interface/API e eles aparecem no JSON exportado.

## Geração e proteção contra respostas sem suporte

O contexto separa dados e instruções e identifica cada documento como E1, E2 etc. Qwen2.5 3B recebe a pergunta e retorna uma estrutura validada. Cada afirmação precisa citar exatamente uma evidência existente. As citações literais são anexadas pelo código, copiadas do corpus, em vez de transcritas pelo modelo.

No modo padrão `extractive`, o código substitui a paráfrase pelo texto integral da evidência selecionada pelo LLM. Uma segunda chamada local verifica a relevância dos relatos selecionados para a pergunta. Se faltar suporte, o sistema se abstém. O modo `summary` mantém a paráfrase e é experimental: a avaliação manual encontrou detalhes não sustentados que passaram pelo verificador. Há também uma heurística contra pedidos explícitos de ignorar regras. Falhas de infraestrutura geram erro HTTP 503, não uma conclusão sobre os dados. A ausência de candidatos/apoio gera `insufficient`.

Essas medidas reduzem, mas não eliminam alucinação ou prompt injection. O verificador usa o mesmo modelo e pode compartilhar erros ou rejeitar respostas corretas. Não há inferência de causa, opinião global ou prevalência a partir de top-k. Para uso real, seriam necessários conjunto rotulado independente, avaliação humana e monitoramento de qualidade.

## Serviço e alternativas

FastAPI valida a entrada. Um processo atende consultas com uma geração de cada vez, evitando sobrecarga do modelo local. Token é obrigatório em `APP_ENV=production`; o limite por minuto é global e em memória. PostgreSQL não usa o superusuário na aplicação. Métricas Prometheus e auditoria estruturada permitem observar latência, resultado, coleção e evidências.

PostgreSQL + pgvector mantém vetores e metadados no mesmo sistema transacional e facilita backup e migração. Não é necessário adotar um serviço vetorial separado para este volume. NumPy, usado no protótipo, oferece busca exata simples, mas não fornece sozinho as capacidades operacionais do banco. Hospedar em nuvem agora acrescentaria custo e dependência de rede sem resolver a limitação de inferência local.

Referências: [pgvector e filtros](https://github.com/pgvector/pgvector#filtering), [Ollama](https://docs.ollama.com/), [dados Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
