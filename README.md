# Comunidade Leitora

Site simples para encontrar livros, conhecer categorias e compartilhar resenhas.

## O que o site faz

- Busca livros por título ou autor.
- Mostra recomendações por categoria.
- Exibe detalhes de cada livro.
- Permite publicar resenhas com nome, nota e comentário.

## Tecnologias usadas

- Python e Flask.
- PostgreSQL no Supabase para as resenhas.
- Google Books API para os livros.

## Como executar no computador

1. Crie o ambiente virtual:

```powershell
python -m venv .venv
```

2. Instale as dependências:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

3. Preencha o arquivo `.env`:

```env
GOOGLE_BOOKS_API_KEY=SUA_CHAVE_AQUI
DATABASE_URL=URL_DO_BANCO_SUPABASE_AQUI
```

4. Inicie o site:

```powershell
& ".\.venv\Scripts\python.exe" app.py
```

5. Abra no navegador:

```text
http://127.0.0.1:5000
```

## Banco de resenhas

1. Crie uma conta gratuita no Supabase.
2. Crie um projeto novo.
3. Em `Connect`, copie a URL de conexão do banco.
4. Cole a URL no valor de `DATABASE_URL` do arquivo `.env`.

A tabela de resenhas é criada automaticamente quando o site inicia.

## Publicação no Render

1. Crie uma conta gratuita no Render.
2. Escolha `New` e depois `Web Service`.
3. Conecte o repositório `Comunidade-Leitora`.
4. Use estes comandos:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

5. Em `Environment`, cadastre estes segredos:

```text
GOOGLE_BOOKS_API_KEY
DATABASE_URL
```

O arquivo `.env` não vai para o GitHub. No Render, os valores são cadastrados diretamente como segredos.
