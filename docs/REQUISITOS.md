# Rastreio do enunciado — fase 4

| Requisito | Implementação / evidência |
|---|---|
| Seleção, limpeza, ausências e documentos | `voice_customer/data.py`, `escuta/ingestion.py`, manifest e testes |
| Embeddings e indexação | EmbeddingGemma, `providers.py`, PostgreSQL/pgvector, `schema.sql` |
| Tratamento da pergunta | `schemas.Query`, validação, prefixo específico de consulta |
| Recuperação semântica | Cosseno, HNSW, busca textual e RRF em `repository.py` |
| Contexto e geração | `service.py`, contexto identificado, Qwen local |
| Fundamentação e rastreabilidade | IDs de evidência, transcrição original, IDs de avaliação/pedido, verificador |
| Evidência insuficiente e fora do escopo | Abstenção, limiar, checagem estruturada, testes reais e unitários |
| Adicional: nota | Filtro mínimo/máximo antes da recuperação |
| Adicional: período de compra | `purchase_date` obtida do cadastro de pedidos, independente da data da avaliação |
| Adicional: informações do pedido | Status, IDs, número de itens e produtos |
| Adicional: entrega | Datas, atraso em dias, filtro atrasada/no prazo/desconhecida |
| Adicional: categoria | Junção de itens e produtos, lista de categorias por pedido e filtro |
| Justificativa dos metadados | `ARQUITETURA.md`, seção de recuperação |
| Código público e reprodução | README, dependências fixadas, Compose, scripts e CI |
| Exemplos de perguntas e respostas | `scripts/evaluate_professional.py`, `evaluation_postgres.json` |
| Vídeo de até 7 minutos | Roteiro preparado; gravação e envio pelo aluno pendentes |
| Bônus de 10 pontos Databricks | Depende da conclusão pessoal da trilha Generative AI Engineering Pathway e comprovante; pendente |

Os cinco adicionais técnicos foram implementados. O bônus Databricks é uma formação complementar, não uma exigência de hospedar a aplicação na plataforma. Não marcar vídeo ou trilha como concluídos sem os respectivos entregáveis.
