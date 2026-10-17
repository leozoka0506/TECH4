# Roteiro de apresentação — meta 6min30s

Prepare a aplicação e modelos antes de gravar. Use respostas realmente obtidas; não apresente exemplos hipotéticos como resultados. Aguarde consultas antes de gravar ou faça cortes transparentes de espera. Confira duração final menor que 7 minutos.

## 0:00–0:40 — Problema
“Este projeto ajuda uma equipe de e-commerce a investigar avaliações dos clientes Olist. As notas mostram satisfação geral; os textos permitem entender relatos de entrega, qualidade e atendimento. Construímos uma solução RAG que busca evidências e gera sínteses rastreáveis.”

## 0:40–1:35 — Base e preparação
Mostre as contagens reais da interface e do manifest. Explique título + comentário, ausências e preservação dos IDs. Diferencie data da compra e da avaliação. Mostre que itens são agregados por pedido antes da junção para não duplicar avaliações.

## 1:35–2:25 — Arquitetura
Mostre o diagrama do README: dados → embeddings → PostgreSQL/pgvector; pergunta → busca híbrida → contexto → Qwen → validação. Explique o modo extrativo: a IA seleciona evidências e a resposta apresenta textos originais para evitar detalhes inventados em paráfrases. O modelo recebe os comentários recuperados em contexto; não houve treinamento sobre a base.

## 2:25–4:40 — Demonstração
Pergunte sobre atrasos e filtre entrega atrasada. Mostre resposta, datas e IDs de duas evidências. Depois filtre notas 1–2 e investigue produtos quebrados. Demonstre categoria e período da compra. Explique que recuperar poucas avaliações não mede frequência global. Baixe a investigação em JSON.

## 4:40–5:30 — Limitações e abstenção
Faça uma pergunta fora da base e outra com data a partir de 2030. Mostre a abstenção. Explique validação dos IDs e anexação dos textos originais pelo programa, reconhecendo que isso não verifica toda a semântica de cada conclusão.

## 5:30–6:15 — Testes e decisões
Mostre os testes e o resultado real da avaliação operacional. Cite filtros antes do ranking, contexto sem textos duplicados, limiar heurístico e possibilidade de falsos positivos/negativos. Explique custo local e tradeoff de um modelo pequeno.

## 6:15–6:30 — Reprodução
Mostre README e endereço do repositório público. Explique os comandos de download, construção e execução. Encerre.

## Checklist final
- [ ] Repositório público acessível sem login.
- [ ] Nome(s) e identificação acadêmica adicionados pelo(s) estudante(s).
- [ ] Instalação e exemplos conferidos.
- [ ] Dados, pesos e segredos fora do Git.
- [ ] Vídeo com demonstração e raciocínio técnico, até 7 minutos.
- [ ] Links enviados no ambiente da faculdade.
