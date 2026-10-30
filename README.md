# Magic Bulk Backend

Base do backend da aplicação Magic Bulk. A estrutura abaixo é o ponto de partida para rotas, modelos e regras de negócio.

## Stack

- Python 3.13
- FastAPI e Pydantic
- SQLAlchemy 2 com driver assíncrono e Alembic
- PostgreSQL
- UV
- Pytest, Ruff e Mypy

## Estrutura

```text
app/
  main.py        aplicação FastAPI
  api/           rotas e dependências HTTP
  core/          configuração e sessão do banco
  models/        modelos SQLAlchemy
  schemas/       schemas Pydantic
alembic/         migrações
tests/           testes de unidade e integração
```

## Requisitos

- [UV](https://docs.astral.sh/uv/)
- Docker, para o PostgreSQL local

## Como rodar

```bash
cp .env.example .env
docker compose up -d
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

A API fica em `http://127.0.0.1:8000`. A documentação interativa fica em `http://127.0.0.1:8000/docs`.

`GET /api/v1/health` responde sem consultar o banco. `GET /api/v1/ready` confirma que o PostgreSQL aceita conexão.

## Testes e checagens

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

`uv run pytest` deixa de fora os testes que precisam do PostgreSQL. Com o banco no ar:

```bash
uv run pytest -o addopts="-q --strict-markers"
```

## Migrações

Cada modelo novo precisa ser importado em `app/models/__init__.py` para entrar no metadata do Alembic.

```bash
uv run alembic revision --autogenerate -m "descricao"
uv run alembic upgrade head
```

A dependência `DbSession` abre a sessão do request e confirma a transação se a rota terminar sem erro.

## Variáveis de ambiente

O arquivo `.env.example` lista os valores locais. `DATABASE_URL` usa o driver `postgresql+asyncpg`.

Auth fica no Supabase. O backend precisa da URL, da chave anônima, da service role e de um JWT secret ou JWKS para validar o access token. A service role só existe no processo do backend.
