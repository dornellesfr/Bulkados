# Bulkados

Magic Bulk em um repositório só. O frontend e o backend ficam em pastas separadas.

```text
frontend/     interface (Bun, Vite, React)
backend/      API (FastAPI, PostgreSQL)
compose.yaml  API e interface em desenvolvimento
```

## Desenvolvimento

Copie os exemplos de ambiente, se os arquivos ainda não existirem:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Suba a API e a interface a partir desta pasta:

```bash
docker compose up
```

- Interface: http://localhost:3000
- API: http://127.0.0.1:8001
- Documentação da API: http://127.0.0.1:8001/docs

O processo da API lê `backend/.env` para o banco e para o Supabase. `DATABASE_URL` aponta para o Postgres remoto. No navegador, a interface chama a API em `http://127.0.0.1:8001`. O processo dentro do container continua escutando na porta 8000.

O Postgres local do Compose fica fora desse comando. Para subir só ele e rodar a API e a interface na máquina, use `docker compose --profile local up db -d`. Os comandos de cada pasta estão em `backend/README.md` e `frontend/README.md`.

## Deploy na Vercel

O frontend e a API sobem juntos, em um projeto só: a SPA na raiz e o FastAPI em `/api`, no mesmo domínio. O passo a passo, as variáveis de ambiente e as limitações do serverless estão em [DEPLOY.md](DEPLOY.md).
