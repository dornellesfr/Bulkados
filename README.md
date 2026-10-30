# Bulkados

Magic Bulk em um repositório só. O frontend e o backend ficam em pastas separadas.

```text
frontend/     interface (Bun, Vite, React)
backend/      API (FastAPI, PostgreSQL)
compose.yaml  Postgres, API e interface em desenvolvimento
```

## Desenvolvimento

Copie os exemplos de ambiente, se os arquivos ainda não existirem:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Suba os três serviços a partir desta pasta:

```bash
docker compose up
```

- Interface: http://localhost:3000
- API: http://127.0.0.1:8000
- Documentação da API: http://127.0.0.1:8000/docs
- Postgres: `localhost:5432`, banco `magic_bulk`, usuário e senha `postgres`

O processo da API lê `backend/.env` para o Supabase. O Compose define `DATABASE_URL` com o host `db`, então o banco do container não usa `localhost`. No navegador, a interface continua chamando a API em `http://127.0.0.1:8000`.

Para subir só o Postgres e rodar a API e a interface na máquina, use `docker compose up db -d`. Os comandos de cada pasta estão em `backend/README.md` e `frontend/README.md`.
