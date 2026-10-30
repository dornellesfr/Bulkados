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
- Docker, para o PostgreSQL local ou para a stack da raiz

## Como rodar

Na raiz do repositório, `docker compose up` sobe o Postgres, esta API e o frontend.

Para trabalhar só nesta pasta, suba o banco a partir da raiz e rode a API aqui:

```bash
cp .env.example .env
docker compose -f ../compose.yaml up db -d
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

## Administração

Cada usuário tem um `level`: `0` é admin e `1` é usuário comum (o padrão do cadastro público). As rotas em `/api/v1/admin` exigem nível 0, ficam fora do `/docs` e o frontend não as chama.

`POST /api/v1/admin/users` cria um usuário com `email`, `password`, `nick` e, opcionalmente, `level` (`0` ou `1`). Use o access token de um admin (`POST /api/v1/auth/login`).

Ao subir, o backend cria em segundo plano o admin `bulkados`, se ele ainda não existir. Isso nunca atrasa nem derruba a subida: se falhar, o motivo vai para o log. Ele nunca promove um usuário que já exista com esse nick ou e-mail.

| Variável | Para que serve |
|---|---|
| `ADMIN_EMAIL` | E-mail do admin. Sem ele, o admin não é criado |
| `ADMIN_PASSWORD` | Senha do admin. Sem ela, só em `ENVIRONMENT=development` vale `@bulkados1234` |

Em produção, defina `ENVIRONMENT=production` e `ADMIN_PASSWORD`. Se o `ENVIRONMENT` ficar de fora, o backend assume `development` e o admin nasce com a senha padrão. A senha precisa ter pelo menos o mínimo do Supabase (6 caracteres, o padrão). Se o admin já existir no Supabase mas o banco local foi recriado, o backend reaproveita a conta quando a senha confere. O nick `bulkados` é reservado: o cadastro público o recusa.

## Acervo de cartas

`GET /api/v1/catalog/cards?q=` sugere até 20 cartas do acervo local, por prefixo do nome em inglês ou português, sem diferenciar acento nem maiúscula. O acervo é uma cópia do catálogo do Scryfall (cerca de 34 mil cartas, uns 40 MB no banco).

**Primeira carga.** O backend carrega o acervo sozinho na primeira subida, em segundo plano, sem atrasar a subida. Ela lê o arquivo `oracle_cards` (25 MB) e ~145 páginas de nomes em português. O Scryfall costuma devolver 429 no meio do caminho, e o backend espera o `Retry-After`, então a carga leva uns 7 minutos ou mais. Enquanto o acervo nunca foi carregado, a busca ainda consulta o Scryfall ao vivo.

**Atualização.** Depois da primeira carga, o backend confere a cada 6 horas se o intervalo venceu (90 dias, por padrão). Repetir a carga só atualiza: nunca troca o `id` nem apaga carta, então as cópias cadastradas seguem apontando para a carta certa. Uma carga que ficou "em andamento" por mais de 1 hora é dada como morta e pode ser refeita. Não edite arquivos `.py` enquanto ela roda no Compose: o `--reload` reinicia o backend e a carga recomeça.

Rotas de admin (use o token do admin; veja a seção acima):

| Rota | O que faz |
|---|---|
| `GET /api/v1/admin/catalog/sync` | Intervalo, data da última atualização, se está rodando e o último erro |
| `POST /api/v1/admin/catalog/sync-interval` com `{"days": 30}` | Muda o intervalo, de 1 a 3650 dias |
| `POST /api/v1/admin/catalog/sync` | Força uma atualização agora (202, ou 409 se já houver uma rodando) |

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"identifier":"bulkados","password":"..."}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s http://127.0.0.1:8000/api/v1/admin/catalog/sync -H "Authorization: Bearer $TOKEN"
```
