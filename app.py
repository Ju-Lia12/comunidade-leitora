import sqlite3

import requests
from flask import Flask, redirect, render_template, request, url_for

# Cria a aplicação Flask.
app = Flask(__name__)

# Configurações usadas em todo o projeto.
BANCO_DE_DADOS = "database.db"
URL_GOOGLE_BOOKS = "https://www.googleapis.com/books/v1/volumes"
CATEGORIAS = [
    "Romance",
    "Fantasia",
    "Ficção científica",
    "Mistério",
    "Biografia",
    "Poesia",
    "História",
]


# Cria a tabela de resenhas quando o programa é iniciado.
def criar_banco():
    conexao = sqlite3.connect(BANCO_DE_DADOS)
    cursor = conexao.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            reader_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conexao.commit()
    conexao.close()


# Faz uma consulta na API e devolve os dados ou uma mensagem de erro.
def consultar_google_books(url, parametros=None):
    try:
        resposta = requests.get(url, params=parametros, timeout=10)
        resposta.raise_for_status()
        return resposta.json(), None
    except requests.HTTPError as erro:
        if erro.response.status_code == 429:
            return None, "O catálogo do Google Books está temporariamente ocupado. Tente novamente em alguns minutos."
        return None, "Não foi possível consultar o catálogo de livros agora."
    except requests.RequestException:
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


# Busca livros pelo título, autor ou assunto digitado.
def buscar_livros(termo):
    dados, erro = consultar_google_books(
        URL_GOOGLE_BOOKS,
        {"q": termo, "maxResults": 18, "printType": "books"},
    )
    if erro:
        return [], erro

    livros = []
    for livro in dados.get("items", []):
        livros.append(organizar_livro(livro))
    return livros, None


# Busca somente um livro para a página de detalhes.
def buscar_livro(book_id):
    dados, erro = consultar_google_books(f"{URL_GOOGLE_BOOKS}/{book_id}")
    if erro:
        return None, erro
    return organizar_livro(dados), None


# Busca todas as resenhas salvas para um livro.
def buscar_resenhas(book_id):
    conexao = sqlite3.connect(BANCO_DE_DADOS)
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT reader_name, rating, comment, created_at
        FROM reviews
        WHERE book_id = ?
        ORDER BY id DESC
        """,
        (book_id,),
    )
    resenhas = cursor.fetchall()
    conexao.close()
    return resenhas


# Rotas que mostram as páginas da plataforma.
@app.route("/")
def index():
    # Mostra a página inicial e as categorias sugeridas.
    return render_template("index.html", categories=CATEGORIAS)


@app.route("/buscar")
def search():
    # Pega o texto digitado no campo de busca.
    query = request.args.get("q", "").strip()
    if not query:
        return render_template(
            "results.html",
            books=[],
            categories=CATEGORIAS,
            error="Digite um título, autor ou assunto para fazer uma busca.",
            heading="Encontre sua próxima leitura",
            query="",
        )

    books, error = buscar_livros(query)
    return render_template(
        "results.html",
        books=books,
        categories=CATEGORIAS,
        error=error,
        heading=f'Resultados para "{query}"',
        query=query,
    )


@app.route("/categoria/<category>")
def category_recommendations(category):
    # Usa a categoria selecionada como busca na API.
    books, error = buscar_livros(f"subject:{category}")
    return render_template(
        "results.html",
        books=books,
        categories=CATEGORIAS,
        error=error,
        heading=f"Recomendações de {category}",
        query="",
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

    # Salva a resenha no banco de dados SQLite.
    conexao = sqlite3.connect(BANCO_DE_DADOS)
    cursor = conexao.cursor()
    cursor.execute(
        """
        INSERT INTO reviews (book_id, reader_name, rating, comment)
        VALUES (?, ?, ?, ?)
        """,
        (book_id, reader_name[:60], rating, comment[:1000]),
    )
    conexao.commit()
    conexao.close()

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
    app.run(debug=True)
