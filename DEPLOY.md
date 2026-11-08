# Deploy na Vercel

O repositório sobe como **um projeto Vercel com dois services**:

- `web` (`frontend/`): SPA Vite, servida na raiz;
- `api` (`backend/`): FastAPI, servida em `/api/*`.

As duas ficam no mesmo domínio (`https://<projeto>.vercel.app`), então o navegador
chama a API na própria origem e não há CORS. A configuração está em
[`vercel.json`](vercel.json).

> Services está em beta na Vercel. O deploy é feito em um único projeto, com
> previews e rollback compartilhados.

## 1. Preparar o banco (antes do primeiro deploy)

As migrações e o seed **não rodam na Vercel**: o processo é serverless e não deve
alterar schema a cada deploy. Rode da sua máquina, com `backend/.env` apontando
para o banco de produção (o mesmo Aiven usado hoje):

```bash
cd backend
uv run alembic upgrade head
uv run python -m app.seed
```

Opcional, se o catálogo ainda não estiver carregado no banco. Leva vários minutos:

```bash
cd backend
uv run python -m app.sync_catalog
```

## 2. Criar o projeto

Importe o repositório no dashboard da Vercel ou use a CLI:

```bash
npm i -g vercel
vercel login
vercel link
```

Se for importar pelo dashboard, deixe o **Root Directory** como a raiz do
repositório (não selecione `frontend/` nem `backend/`). É a raiz que contém o
`vercel.json` com os dois services.

## 3. Variáveis de ambiente

Cadastre em **Settings > Environment Variables** (Production e Preview):

| Variável | Valor |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | `postgresql+asyncpg://...` do Aiven |
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_ANON_KEY` | chave anon |
| `SUPABASE_SERVICE_ROLE_KEY` | service role |
| `SUPABASE_JWT_SECRET` | segredo HS256 (se o projeto usa HS256) |
| `SUPABASE_JWKS_URL` | URL do JWKS (se o projeto usa RS256/ES256) |
| `ADMIN_EMAIL` | e-mail do admin |
| `ADMIN_PASSWORD` | senha do admin (obrigatória em produção) |
| `CATALOG_SYNC_ENABLED` | `false` |
| `DB_POOL_SIZE` | `2` |
| `DB_MAX_OVERFLOW` | `1` |
| `CORS_ORIGINS` | vazio (mesma origem) |

`CATALOG_SYNC_ENABLED=false` desliga o agendador do catálogo e a rota de sync.
Uma carga do Scryfall leva mais que o limite de execução de uma função e seria
interrompida no meio. Para atualizar o catálogo, rode
`uv run python -m app.sync_catalog` localmente (passo 1).

`DB_POOL_SIZE` e `DB_MAX_OVERFLOW` limitam as conexões por instância. Cada
instância da função abre o próprio pool; valores altos podem estourar o limite
de conexões do Aiven.

**Não defina `VITE_API_URL`.** Em produção o frontend usa a própria origem
(`window.location.origin`), o que também faz os previews chamarem a API do
próprio preview. Se precisar apontar para outro host, defina a URL absoluta.

## 4. Deploy

```bash
vercel --prod
```

Ou faça o deploy pelo Git: cada push na branch conectada gera um novo deploy.

## 5. Conferir

```bash
curl https://<projeto>.vercel.app/api/v1/health
curl https://<projeto>.vercel.app/api/v1/ready
```

- App: `https://<projeto>.vercel.app`
- Swagger: `https://<projeto>.vercel.app/docs`

O `/ready` confirma a conexão com o PostgreSQL.

## Observações

- **Migrações**: sempre que houver uma migração nova, rode
  `uv run alembic upgrade head` antes de publicar o código que depende dela.
- **Região**: deixe a função o mais perto possível do banco. O pool e as
  consultas em lote ajudam, mas cada round-trip para um Postgres remoto custa
  caro.
- **Aiven**: se houver allowlist de IP, libere o tráfego da Vercel (os IPs de
  saída são dinâmicos) ou desative a restrição para o ambiente de teste.
- **Plano**: no Hobby a função tem até 300s e 2 GB. O uso de teste se encaixa;
  uso comercial exige o plano Pro.
- **Preview**: como frontend e API estão no mesmo deployment, cada preview tem
  sua própria API e banco configurado nas variáveis de Preview.
