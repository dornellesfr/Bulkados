# Magic Bulk

Frontend do Bulkados. A interface mostra o estado que a API devolve e dispara as transições que a API já definiu.

Na raiz do repositório, `docker compose up` sobe esta interface junto com a API e o Postgres. Para rodar só o frontend, os scripts abaixo assumem que a API já está em `http://127.0.0.1:8000`.

## Stack

- Bun, Vite e TypeScript
- TanStack Router, com rotas em `src/routes` e preload no `intent`
- TanStack Query, com `ensureQueryData` no loader e `useSuspenseQuery` na tela
- Zod, na resposta da API, na busca da URL e nos formulários
- React Hook Form
- shadcn/ui (preset Nova, base Radix), tema claro e escuro

## Scripts

```bash
bun install
bun run dev
bun run typecheck
bun run lint
bun run build
```

O servidor de desenvolvimento sobe em `http://localhost:3000`.

## Dados

`VITE_API_URL` é obrigatório e aponta para a origem da API, sem path. Exemplo local: `http://127.0.0.1:8000`. O cliente prefixa `/api/v1`. Sem a variável, o app não sobe. O exemplo está em `.env.example`.

O fluxo de uma tela com dados fica assim:

1. O schema Zod descreve o contrato em `src/lib/api`.
2. `apiRequest` manda o Bearer, renova a sessão num 401 e só devolve o JSON depois do `safeParse`.
3. A rota chama `queryClient.ensureQueryData` no `loader`.
4. O componente lê o cache com `useSuspenseQuery`.
5. O `pendingComponent` do router cobre a navegação, e o `Suspense` da raiz cobre uma query que ainda suspende.
6. O `errorComponent` zera o boundary do Query e invalida a rota no retry.

Passar o mouse num link pré-carrega a rota (`defaultPreload: 'intent'`).

## Sessão

Cadastro, login, refresh e recuperação passam pela API. Os tokens ficam em `localStorage` (`magic-bulk.access-token` e `magic-bulk.refresh-token`). Rotas protegidas ficam no layout sem path `src/routes/_app.tsx`.

## Produto

O que o app faz está em [docs/conceito.md](docs/conceito.md). As telas, o contrato que o cliente valida e a ordem de construção estão em [docs/spec-frontend.md](docs/spec-frontend.md).
