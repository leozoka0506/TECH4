# Aqui criamos uma lista, com varios dicionarios, cada dicionario começa com { e termina com } e cada dicionario tem 3 chaves, id, nota e comentario.
avaliacoes = [
    {"id": "av_001", "nota": 2, "comentario": "  Entrega atrasada.  "},
    {"id": "av_002", "nota": 1, "comentario": None},
    {"id": "av_003", "nota": 3, "comentario": "   "},
    {"id": "av_004", "nota": 5, "comentario": "Produto excelente!"}
]
# Aqui criamos uma função que recebe o nome de limpar_comentario
def limpar_comentario(comentario):
    # a função verifica se o comentario é None, se for None, retorna uma string vazia
    if comentario is None:
        return ""
    #Cado nao seja none, a função retorna o comentario sem espaços em branco no inicio e no final

    return comentario.strip()
# aqui criamos uma lista vazia, que vai recerber as avaliaçãoes que não estão vazias, ou seja, que tem algum comentario valido

avaliacoes_validas = []
#aqui vamos passar por cada avaliação da lista de avaliações, no python o for pula sozinho sem necessidade de somar a variavel avaliacao, ele vai pegar cada avaliação da lista de avaliações e colocar na variavel avaliacao, e assim por diante até acabar a lista de avaliações

for avaliacao in avaliacoes:
    # aqui criamos a variavel texto, que vai receber o resultado da função limpar_comentario, passando como parametro o comentario da avaliação
    
    texto = limpar_comentario(avaliacao["comentario"])
    #aqui após o loop, verificamos se o texto não é uma string vazia, se não for, adicionamos a avaliação na lista de avaliações válidas, criando um novo dicionario com as mesmas chaves id e nota, e a chave comentario com o valor do texto
    
    if texto != "":
        avaliacoes_validas.append({
            "id": avaliacao["id"],
            "nota": avaliacao["nota"],
            "comentario": texto
        })
#aqui vamos imprimir cada avaliação válida, percorrendo a lista de avaliações válidas e imprimindo cada avaliação
for avaliacao in avaliacoes_validas:
    print(avaliacao)
    
#total de avaliações, total de avaliações válidas e total de avaliações descartada
total = len(avaliacoes)
validas = len(avaliacoes_validas)
descartadas = total - validas

print("Total:", total)
print("Válidas:", validas)
print("Descartadas:", descartadas)

# Aqui criamos uma função que recebe o nome de buscar_avaliacoes, que recebe como parametro a lista de avaliações e o termo a ser buscado
def buscar_avaliacoes(avaliacoes, termo):

    #aqui criamos uma lista vazia, que vai receber as avaliações que contém o termo buscado
    resultados = []
    #aqui vamos limpar o termo, removendo espaços em branco no inicio e no final e transformando em minusculo
    termo = termo.strip().lower()
    #aqui verificamos se o termo é uma string vazia, se for, retornamos a lista de resultados vazia
    if termo == "":
        return resultados

    #aqui vamos percorrer a lista de avaliações, e para cada avaliação, vamos pegar o comentario e verificar se o termo está presente no comentario, se estiver, adicionamos a avaliação na lista de resultados
    for avaliacao in avaliacoes:
        #aqui criamos a variavel comentario, que vai receber o comentario da avaliação
        comentario = avaliacao["comentario"]
        # e aqui verificamos se o termo está presente no comentario todo minúsculo, se estiver, adicionamos a avaliação na lista de resultados
        if termo in comentario.lower():
            resultados.append(avaliacao)

    return resultados


encontradas = buscar_avaliacoes(avaliacoes_validas, "entrega")

for avaliacao in encontradas:
    print(avaliacao["id"], avaliacao["comentario"])

print("Quantidade encontrada:", len(encontradas))