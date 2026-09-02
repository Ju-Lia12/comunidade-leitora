# Comunidade Leitora

Site simples para encontrar livros, conhecer categorias e compartilhar resenhas.

# O que o site faz

- Busca livros por título ou autor.
- Mostra recomendações por categoria.
- Exibe detalhes de cada livro.
- Permite publicar resenhas com nome, nota e comentário.

# Tecnologias usadas

- Python
- Flask
- SQLite
- Google Books API

# Como executar

1. Crie o ambiente virtual:

```powershell
python -m venv .venv
```

2. Instale as dependências:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

3. No arquivo `.env`, informe a sua chave da Google Books API:

```env
GOOGLE_BOOKS_API_KEY=SUA_CHAVE_AQUI
```

4. Inicie o site:

```powershell
& ".\.venv\Scripts\python.exe" app.py
```

5. Abra no navegador:

```text
http://127.0.0.1:5000
```

# Importante

O arquivo `.env` guarda a chave da API e não é enviado ao GitHub.
