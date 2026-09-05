import math
import os
import time

import psycopg
import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for
from psycopg.rows import dict_row

# Carrega a chave local antes de iniciar a aplicação.
load_dotenv()

# Cria a aplicação Flask.
app = Flask(__name__)

# Configurações usadas em todo o projeto.
URL_BANCO_DE_DADOS = os.getenv("DATABASE_URL")
URL_GOOGLE_BOOKS = "https://www.googleapis.com/books/v1/volumes"
CHAVE_GOOGLE_BOOKS = os.getenv("GOOGLE_BOOKS_API_KEY")
# Dezoito completa linhas de 6, 3 ou 2 livros em cada tamanho de tela.
LIVROS_POR_PAGINA = 18
CATEGORIAS = [
    "Romance",
    "Fantasia",
    "Ficção científica",
    "Mistério",
    "Biografia",
    "Poesia",
    "História",
]
CATEGORIAS_API = {
    "Romance": "romance",
    "Fantasia": "fantasy",
    "Ficção científica": "science fiction",
    "Mistério": "mystery",
    "Biografia": "biography",
    "Poesia": "poetry",
    "História": "history",
}


# Abre a conexão com o banco de resenhas online.
def conectar_banco():
    if not URL_BANCO_DE_DADOS:
        return None
    return psycopg.connect(URL_BANCO_DE_DADOS, row_factory=dict_row)


# Cria a tabela de resenhas quando o programa é iniciado.
def criar_banco():
    conexao = conectar_banco()
    if not conexao:
        return

    with conexao, conexao.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id BIGSERIAL PRIMARY KEY,
                book_id TEXT NOT NULL,
                reader_name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


# Faz uma consulta na API e devolve os dados ou uma mensagem de erro.
def consultar_google_books(url, parametros=None):
    # Adiciona a chave da API sem deixá-la salva no código.
    if parametros is None:
        parametros = {}

    if not CHAVE_GOOGLE_BOOKS:
        return None, "A chave da Google Books API não foi configurada."

    parametros["key"] = CHAVE_GOOGLE_BOOKS

    # Repete uma vez quando a falha pode ser temporária.
    for tentativa in range(2):
        try:
            resposta = requests.get(url, params=parametros, timeout=10)
            resposta.raise_for_status()
            return resposta.json(), None
        except requests.HTTPError as erro:
            codigo = erro.response.status_code if erro.response is not None else 0

            if codigo == 403:
                return None, "A Google Books API recusou a busca. Verifique se a chave está ativa e restrita à Books API."
            if codigo == 400:
                return None, "A busca não pôde ser processada. Tente usar outro termo."
            if codigo == 429 or codigo >= 500:
                if tentativa == 0:
                    time.sleep(1)
                    continue
                return None, "O catálogo do Google Books está temporariamente ocupado. Tente novamente em alguns minutos."

            return None, "Não foi possível consultar o catálogo de livros agora."
        except requests.RequestException:
            if tentativa == 0:
                time.sleep(1)
                continue
            return None, "Verifique sua conexão com a internet e tente novamente."


# Organiza os dados recebidos da API para usar nas páginas HTML.
def organizar_livro(dados):
    informacoes = dados.get("volumeInfo", {})
    imagens = informacoes.get("imageLinks", {})
    capa = imagens.get("thumbnail") or imagens.get("smallThumbnail")

    if capa:
        capa = capa.replace("http://", "https://")

    return {
        "id": dados.get("id"),
        "title": informacoes.get("title", "Título indisponível"),
        "authors": ", ".join(informacoes.get("authors", ["Autor desconhecido"])),
        "description": informacoes.get("description", "A sinopse deste livro não está disponível no catálogo."),
        "categories": informacoes.get("categories", []),
        "cover": capa,
        "publisher": informacoes.get("publisher"),
        "published_date": informacoes.get("publishedDate"),
        "page_count": informacoes.get("pageCount"),
        "average_rating": informacoes.get("averageRating"),
        "ratings_count": informacoes.get("ratingsCount"),
        "preview_link": informacoes.get("previewLink"),
    }


# Busca uma página de livros na Google Books API.
def buscar_livros(termo, pagina):
    dados, erro = consultar_google_books(
        URL_GOOGLE_BOOKS,
        {
            "q": termo,
            "maxResults": LIVROS_POR_PAGINA,
            "startIndex": (pagina - 1) * LIVROS_POR_PAGINA,
            "printType": "books",
            "langRestrict": "pt",
            "orderBy": "relevance",
        },
    )
    if erro:
        return [], 0, erro

    livros = []
    for livro in dados.get("items", []):
        livros.append(organizar_livro(livro))
    return livros, dados.get("totalItems", 0), None


# Lê a página atual sem aceitar números menores que um.
def pagina_atual():
    try:
        return max(1, int(request.args.get("pagina", 1)))
    except ValueError:
        return 1


# Define os números exibidos na navegação entre páginas.
def dados_paginacao(total_livros, pagina):
    total_paginas = max(1, math.ceil(total_livros / LIVROS_POR_PAGINA))
    primeira_pagina = max(1, pagina - 2)
    ultima_pagina = min(total_paginas, pagina + 2)
    return total_paginas, list(range(primeira_pagina, ultima_pagina + 1))


# Busca somente um livro para a página de detalhes.
def buscar_livro(book_id):
    dados, erro = consultar_google_books(f"{URL_GOOGLE_BOOKS}/{book_id}")
    if erro:
        return None, erro
    return organizar_livro(dados), None


# Busca todas as resenhas salvas para um livro.
def buscar_resenhas(book_id):
    conexao = conectar_banco()
    if not conexao:
        return []

    with conexao, conexao.cursor() as cursor:
        cursor.execute(
            """
            SELECT reader_name, rating, comment,
                TO_CHAR(created_at, 'MM/YYYY') AS created_at
            FROM reviews
            WHERE book_id = %s
            ORDER BY id DESC
            """,
            (book_id,),
        )
        return cursor.fetchall()


# Rotas que mostram as páginas da plataforma.
@app.route("/")
def index():
    # Mostra a página inicial e as categorias sugeridas.
    return render_template("index.html", categories=CATEGORIAS)


@app.route("/buscar")
def search():
    # Pega o texto digitado no campo de busca.
    query = request.args.get("q", "").strip()
    pagina = pagina_atual()

    if not query:
        return render_template(
            "results.html",
            books=[],
            categories=CATEGORIAS,
            error="Digite um título ou autor para fazer uma busca.",
            heading="Encontre sua próxima leitura",
            query="",
            page=1,
            total_pages=1,
            page_numbers=[],
            category=None,
        )

    books, total_livros, error = buscar_livros(query, pagina)
    total_paginas, numeros_paginas = dados_paginacao(total_livros, pagina)
    return render_template(
        "results.html",
        books=books,
        categories=CATEGORIAS,
        error=error,
        heading=f'Resultados para "{query}"',
        query=query,
        page=pagina,
        total_pages=total_paginas,
        page_numbers=numeros_paginas,
        category=None,
    )


@app.route("/categoria/<category>")
def category_recommendations(category):
    # Converte a categoria exibida para o termo usado pela Google Books.
    termo = CATEGORIAS_API.get(category, category)
    pagina = pagina_atual()
    books, total_livros, error = buscar_livros(f'subject:"{termo}"', pagina)

    # Tenta uma busca mais ampla se a primeira não encontrar livros.
    if not books and not error:
        books, total_livros, error = buscar_livros(termo, pagina)

    total_paginas, numeros_paginas = dados_paginacao(total_livros, pagina)
    return render_template(
        "results.html",
        books=books,
        categories=CATEGORIAS,
        error=error,
        heading=f"Recomendações de {category}",
        query="",
        page=pagina,
        total_pages=total_paginas,
        page_numbers=numeros_paginas,
        category=category,
    )


@app.route("/livro/<book_id>")
def book_detail(book_id):
    # Busca os dados do livro e suas resenhas.
    book, error = buscar_livro(book_id)
    if error:
        return render_template(
            "results.html",
            books=[],
            categories=CATEGORIAS,
            error=error,
            heading="Livro indisponivel",
            query="",
            page=1,
            total_pages=1,
            page_numbers=[],
            category=None,
        ), 503

    return render_template(
        "book.html",
        book=book,
        reviews=buscar_resenhas(book_id),
        form_error=request.args.get("form_error"),
        form_success=request.args.get("form_success"),
    )


# Rota que recebe e salva uma resenha enviada pelo formulário.
@app.post("/livro/<book_id>/resenha")
def add_review(book_id):
    # Pega os dados enviados no formulário.
    reader_name = request.form.get("reader_name", "").strip()
    comment = request.form.get("comment", "").strip()

    try:
        rating = int(request.form.get("rating", ""))
    except ValueError:
        rating = 0

    if not reader_name or not comment or rating not in range(1, 6):
        return redirect(
            url_for(
                "book_detail",
                book_id=book_id,
                form_error="Preencha seu nome, uma nota de 1 a 5 e o comentário.",
            )
        )

    conexao = conectar_banco()
    if not conexao:
        return redirect(
            url_for(
                "book_detail",
                book_id=book_id,
                form_error="O banco de resenhas ainda não foi configurado.",
            )
        )

    # Salva a resenha no banco de dados PostgreSQL.
    with conexao, conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO reviews (book_id, reader_name, rating, comment)
            VALUES (%s, %s, %s, %s)
            """,
            (book_id, reader_name[:60], rating, comment[:1000]),
        )

    return redirect(
        url_for(
            "book_detail",
            book_id=book_id,
            form_success="Sua resenha foi publicada para a comunidade.",
        )
    )


# Garante que o banco exista antes de receber acessos.
criar_banco()


if __name__ == "__main__":
    # Inicia o servidor local para abrir o projeto no navegador.
    app.run()
