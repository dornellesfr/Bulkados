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

Na raiz do repositório, `docker compose up` sobe esta API e o frontend. O banco vem da `DATABASE_URL` em `.env`.

Para trabalhar só nesta pasta, suba o Postgres local a partir da raiz (se não for usar o remoto) e rode a API aqui:

```bash
cp .env.example .env
docker compose -f ../compose.yaml --profile local up db -d
uv sync --all-groups
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload
```

A API fica em `http://127.0.0.1:8000`. A documentação interativa fica em `http://127.0.0.1:8000/docs`.

`GET /api/v1/health` responde sem consultar o banco. `GET /api/v1/ready` confirma que o PostgreSQL aceita conexão.

## Desempenho do banco

Cada round-trip até um PostgreSQL remoto custa, neste ambiente, uns 200 ms. Como as telas fazem de duas a quatro consultas em sequência, a diferença entre um banco remoto e um local aparece direto no tempo de resposta. Para desenvolver, prefira o Postgres local do Compose (`DATABASE_URL=...localhost:5432/magic_bulk`). Em produção, mantenha a API na mesma região do banco.

As consultas de lista já buscam os dados em lote e os índices cobrem os filtros usados com mais frequência (`group_members`, `card_copies`, `requests`, `decks` e as buscas por prefixo do catálogo). O pool não faz `ping` em toda leitura; ele recicla conexões antigas a cada 5 minutos.

## Testes e checagens

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

`uv run pytest` deixa de fora os testes que precisam do PostgreSQL. Quando eles rodam, o pytest entra em `ENVIRONMENT=test`, então o backend usa `TEST_DATABASE_URL` e nunca o `DATABASE_URL` da aplicação. Sem `TEST_DATABASE_URL`, o padrão é `postgresql+asyncpg://postgres:postgres@localhost:5432/magic_bulk_test`. O banco de teste é truncado a cada teste.

Com o Postgres local no ar e o banco de teste criado:

```bash
docker compose -f ../compose.yaml --profile local up db -d
docker exec bulkados-db psql -U postgres -d magic_bulk -c "CREATE DATABASE magic_bulk_test"
uv run pytest -o addopts="-q --strict-markers"
```

## Migrações

Cada modelo novo precisa ser importado em `app/models/__init__.py` para entrar no metadata do Alembic.

```bash
uv run alembic revision --autogenerate -m "descricao"
uv run alembic upgrade head
uv run python -m app.seed
```

A dependência `DbSession` abre a sessão do request e confirma a transação se a rota terminar sem erro.

## Variáveis de ambiente

O arquivo `.env.example` lista os valores locais. `DATABASE_URL` usa o driver `postgresql+asyncpg` e é o banco de desenvolvimento/produção. `TEST_DATABASE_URL` é usado só quando `ENVIRONMENT=test`; o padrão aponta para o Postgres local `magic_bulk_test`.

Auth fica no Supabase. O backend precisa da URL, da chave anônima, da service role e de um JWT secret ou JWKS para validar o access token. A service role só existe no processo do backend.

## Administração

Cada usuário tem um `level`: `0` é admin e `1` é usuário comum (o padrão do cadastro público). As rotas em `/api/v1/admin` exigem nível 0, ficam fora do `/docs` e o frontend não as chama.

`POST /api/v1/admin/users` cria um usuário com `email`, `password` e, opcionalmente, `level` (`0` ou `1`). Use o access token de um admin (`POST /api/v1/auth/login`).

`python -m app.seed`, logo depois de `alembic upgrade head`, grava o admin do `ADMIN_EMAIL` se esse e-mail ainda não existir. Um banco criado do zero passa por esse seed antes da API subir. A subida também tenta de novo, em segundo plano, e não derruba o processo se falhar: o motivo vai para o log. O seed e a subida nunca promovem um usuário que já exista com esse e-mail.

| Variável | Para que serve |
|---|---|
| `ADMIN_EMAIL` | E-mail do admin. Sem ele, o admin não é criado |
| `ADMIN_PASSWORD` | Senha do admin. Sem ela, só em `ENVIRONMENT=development` vale `@bulkados1234` |

Em produção, defina `ENVIRONMENT=production` e `ADMIN_PASSWORD`. Se o `ENVIRONMENT` ficar de fora, o backend assume `development` e o admin nasce com a senha padrão. A senha precisa ter pelo menos o mínimo do Supabase (6 caracteres, o padrão). Se o admin já existir no Supabase mas o banco local foi recriado, o backend reaproveita a conta quando a senha confere.

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
  -d '{"email":"admin@example.com","password":"..."}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s http://127.0.0.1:8000/api/v1/admin/catalog/sync -H "Authorization: Bearer $TOKEN"
```
