# Spec do frontend

O que este repositório precisa implementar para o produto descrito em [conceito.md](conceito.md), em cima do contrato de [spec-backend.md](../../magic-bulk-backend/docs/spec-backend.md). A interface não recalcula regra de Commander, não chama Scryfall e não chama LigaMagic. Ela mostra o estado que a API devolve e dispara a transição que a API já definiu.

As rotas de publicações (`/posts`, `src/lib/api/posts.ts`, `src/components/posts/`) são o exemplo da stack. Saem na primeira etapa.

## Stack

A que já está no repositório:

- Bun, Vite, TypeScript, React 19.
- TanStack Router, rotas em `src/routes`, preload no `intent`.
- TanStack Query, `ensureQueryData` no `loader`, `useSuspenseQuery` na tela. `pendingComponent` e `errorComponent` da raiz continuam valendo.
- Zod na resposta da API, na busca da URL e no formulário. React Hook Form com `zodResolver`.
- shadcn/ui, tema claro e escuro, toaster que já existe.

`VITE_API_URL` aponta para a origem da API, sem path. Exemplo local: `http://127.0.0.1:8000`. O cliente prefixa `/api/v1`. Sem a variável, o app não sobe: o fallback do JSONPlaceholder sai junto com o exemplo de publicações.

JSON em snake_case. Dinheiro em centavos, inteiro. A tela formata com `Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })`. Nunca envia `float`. `price_cents` nulo aparece como "sem preço". Land básica aparece como R$ 0,00 e não oferece atualizar preço.

O nome visível da carta é `name_pt` quando existe. `name_en` fica na linha de baixo. Busca local olha os dois.

## Sessão

O browser não fala com o Supabase. Cadastro, login, refresh e recuperação passam pela API. A service role não existe neste repositório.

Tokens em `localStorage`, chaves `magic-bulk.access-token` e `magic-bulk.refresh-token`. Não vão para log, toast nem query string.

`apiRequest` manda `Authorization: Bearer` quando há access token. Um 401 dispara um único refresh (`POST /auth/refresh` com `refresh_token`). Pedidos paralelos esperam a mesma promise. Se o refresh falha, a sessão é apagada e a rota protegida manda para `/entrar`. O pedido original é repetido uma vez depois do refresh. 401 no próprio refresh não entra em loop.

Login e cadastro que devolvem `access_token` e `refresh_token` gravam a sessão e em seguida chamam `GET /me`. O corpo do login não é lido em busca de e-mail: login por nick não traz e-mail, e a tela não precisa dele. O cabeçalho mostra o `nick` de `GET /me`.

A spec do backend não descreve confirmação de e-mail. Cadastro com tokens entra direto. Cadastro sem tokens vai para `/entrar` com o texto "Conta criada. Entre com seu nick ou e-mail." A tela não inventa um aviso de e-mail de confirmação.

Recuperação de senha mostra a `message` da API. Se o corpo não trouxer texto, a frase fixa é "Se existir uma conta, o e-mail de recuperação foi enviado." A frase é a mesma com conta existente ou não.

Sair apaga os dois tokens e volta para `/entrar`.

## Rotas

Públicas, e quem já tem sessão nelas cai em `/`:

- `/entrar`
- `/cadastrar`
- `/recuperar-senha`

Protegidas, atrás de um layout sem path (`src/routes/_app.tsx`). Sem sessão, `beforeLoad` manda para `/entrar` e guarda o href em `redirect` para voltar depois do login.

- `/` grupos e convites recebidos
- `/grupos/$groupId` bulk daquele grupo
- `/grupos/$groupId/decks` decks da pessoa naquele grupo
- `/grupos/$groupId/decks/$deckId` deck
- `/grupos/$groupId/encontro` levar e receber
- `/grupos/$groupId/membros` membros, convite, nome, saída

Não existe `GET /groups/{id}`. O layout do grupo lê o nome em `GET /groups`. Id ausente nessa lista, ou 404 da API, vira a página de não encontrado. O texto é "Esse grupo não está disponível." Não diz se a pessoa está fora do grupo: a API esconde o recurso de quem não é membro `accepted`.

Dentro do grupo, a navegação é Bulk, Decks, Encontro, Membros. Encontro carrega `GET /groups/{id}/handoffs` no layout e mostra a soma de `to_bring` e `to_receive` quando for maior que zero.

Cabeçalho logado: nome do app, link para `/`, nick, sair, tema. O link de publicações sai.

Filtros de lista ficam na URL, no mesmo padrão de `validateSearch` que o exemplo já usa.

## Contrato que o cliente valida

O Zod descreve os campos abaixo. Campo desconhecido é descartado. Campo obrigatório ausente quebra a leitura de propósito, no `errorComponent`. Se o OpenAPI batizado no backend usar outro nome, o schema deste repositório acompanha o OpenAPI; a tela continua precisando da informação descrita aqui.

Erro: a API no estilo FastAPI manda `{ "detail": ... }`. `detail` string vira a mensagem do formulário ou do toast. `detail` lista mostra "Revise os campos." Status sem corpo usa o texto da tabela de erros, mais abaixo.

### Auth

`POST /auth/register` com `email`, `password`, `nick`.

`POST /auth/login` com `identifier`, `password`. Resposta usada: `access_token`, `refresh_token`, `expires_in`.

`POST /auth/refresh` com `refresh_token`. Mesma forma de token.

`POST /auth/forgot-password` com `identifier`.

`GET /me` devolve `id` e `nick`.

Nick no formulário: 3 a 20 caracteres, letras, números e `_`. A API continua sendo quem recusa nick duplicado.

### Grupos

`POST /groups` `{ name }` e `PATCH /groups/{id}` `{ name }`.

`GET /groups` lista grupos em que a pessoa é membro `accepted`:

- `id`, `name`, `owner_id`, `created_at`

Dono na tela é `owner_id === me.id`. Não há campo extra de papel.

`GET /groups/{id}/members`:

- `user_id`, `nick`, `status` (`invited` ou `accepted`), `created_at`

`POST /groups/{id}/invitations` `{ nick }`.

`POST /invitations/{id}/accept` e `POST /invitations/{id}/decline`.

`POST /groups/{id}/leave`.

`GET /groups` não inclui convite pendente: quem está `invited` não lê o grupo. A caixa de convites precisa de uma leitura que a spec do backend ainda não nomeia:

`GET /invitations`, só os convites `invited` de quem está logado:

- `id`
- `group`: `id`, `name`
- `invited_by`: `id`, `nick`
- `created_at`

Aceitar e recusar usam esse `id`. Sem essa rota, a etapa de grupos entrega criar, renomear, convidar, membros e sair; a caixa de entrada fica para quando a rota existir. Não chutar outra URL.

### Catálogo

`GET /catalog/cards?q=`. Cada item: `oracle_id`, `name_en`, `name_pt` nulo, `mana_cost` nulo, `image_url` nulo (link da imagem da carta), `type_line` nulo, `color_identity` (lista), `is_basic`. A API devolve no máximo 20 itens, por prefixo do nome em português ou inglês, sem diferenciar acento nem maiúscula.

A busca dispara com pelo menos 2 caracteres, com debounce, e cancela a request anterior. Campo vazio não chama a API.

### Cópias

`GET /groups/{id}/copies`. Cada item:

- `id`
- `catalog`: `oracle_id`, `name_en`, `name_pt`, `type_line`, `color_identity`, `is_basic`
- `holder`: `id`, `nick`
- `added_by`: `id`, `nick`
- `price_cents` nulo, `price_fetched_at` nulo
- `state`: `available`, `reserved`, `in_deck`
- `locked`
- `visibility`: `available`, `reserved`, `in_deck`, `in_use_elsewhere`
- `deck` nulo, ou `{ id, name, owner: { id, nick } }` quando `visibility` é `in_deck` (o deck é deste grupo)
- `open_request` nulo, ou `{ id, status, source, requester: { id, nick } }` com `status` `pending_acceptance` ou `awaiting_handoff` e `source` `bulk` ou `deck`

`in_use_elsewhere` é a cópia no deck de um grupo que quem vê não participa. Nesse caso `deck` vem nulo: a tela não mostra nome de deck nem nick de outro grupo.

`POST /groups/{id}/copies`:

- `oracle_id`
- `quantity`, inteiro `>= 1`
- `holder_id` opcional; omitido, a casa é quem cadastra
- `group_ids` opcional, os outros grupos além do grupo da URL

Resposta: a lista das cópias criadas. Falha de preço não falha o cadastro; `price_cents` nulo é sucesso.

`POST /copies/{id}/groups` `{ group_id }`.

`DELETE /copies/{id}`.

`POST /copies/{id}/refresh-price` devolve a cópia com o preço novo ou ainda nulo.

### Decks

`POST /groups/{id}/decks` `{ name, format }`. `format` é `commander_10`, `commander_100`, `commander_200`, `commander_500` ou `competitive`.

`GET /groups/{id}/decks` só os decks de quem está logado naquele grupo: `id`, `name`, `format`. A contagem fica no detalhe.

`GET /decks/{id}`:

- `id`, `group_id`, `name`, `format`, `owner_id`
- `card_count`, `main_price_cents`, `commander_price_cents`
- `warnings`: `code`, `card_copy_id` nulo, `message`
- `cards`: `card_copy_id`, `role` (`commander` ou `main`), `locked`, `price_cents` nulo, `holder` (`id`, `nick`), `catalog` (os campos da cópia, mais `commander_legal`, `can_be_commander`, `partner_kind` nulo), `open_request` no mesmo formato da lista de cópias

O texto do aviso é o `message` da API. O `code` só escolhe o lugar na tela. A interface não tem uma segunda lista de regras.

`PATCH /decks/{id}` com `name`, `format`, ou os dois.

`DELETE /decks/{id}` devolve as cartas ao bulk. A tela pede confirmação antes.

`POST /decks/{id}/commanders` `{ card_copy_ids }` substitui o conjunto inteiro. Pode ir lista vazia.

`POST /decks/{id}/take` `{ card_copy_id }`.

`POST /decks/{id}/copies` `{ oracle_id, quantity }`. A casa é quem cadastra. Não há campo de casa nem de grupo nesse corpo.

`POST /decks/{id}/cards/{card_copy_id}/move` `{ target_deck_id }`.

`POST /decks/{id}/cards/{card_copy_id}/return`, `/lock` e `/unlock` sem corpo.

### Pedidos

`POST /decks/{id}/requests` `{ card_copy_id }`. O `id` da URL é o deck de destino, sempre um deck de quem pede, no grupo em que a cópia está sendo vista. A API decide se o pedido nasce do bulk ou de um deck pelo estado da cópia. A tela não manda `source`.

`POST /requests/{id}/accept`, `/reject`, `/cancel` e `/confirm` sem corpo.

`GET /groups/{id}/handoffs`:

- `to_bring`: pedidos `awaiting_handoff` em que a casa é quem está logado. Item com `id`, `source`, `catalog` (`name_en`, `name_pt`), `requester` (`id`, `nick`), `target_deck` (`id`, `name`).
- `to_receive`: pedidos abertos em que quem está logado pediu. O mesmo item, mais `status` (`pending_acceptance` ou `awaiting_handoff`) e `holder` (`id`, `nick`) no lugar de `requester`.

Aceitar e recusar não aparecem nessas duas listas. Aparecem na carta do deck de origem, para o dono daquele deck, quando `open_request.status` é `pending_acceptance`.

### Onde cada aviso aparece

| `code` | Lugar |
| --- | --- |
| `deck_over_100`, `deck_under_100` | Contagem do deck |
| `budget_main`, `budget_commanders` | Orçamento |
| `missing_price` | Orçamento e a carta, quando houver `card_copy_id` |
| `commander_pairing` | Bloco dos comandantes |
| `duplicate_name`, `color_identity`, `banned`, `commander_illegal` | A carta, quando houver `card_copy_id`, e a lista de avisos |

Nenhum aviso desabilita botão de adicionar, solicitar, salvar ou marcar comandante.

Orçamento na tela, com os centavos que a API já somou:

- Commander 10: soma das `main` contra R$ 10 (`1000`) e soma dos `commander` contra R$ 5 (`500`). Os tetos são rótulo do produto; o aviso continua vindo da API. Estourar um não consome o outro.
- Commander 100, 200 e 500: as duas somas, sem teto e sem frase de preço. O formato escolhido continua visível.
- Competitivo: as duas somas, sem teto.
- `missing_price`: a linha "Orçamento incompleto" junto das somas. Carta sem preço não entra na conta, e a tela não inventa zero no lugar.

Contagem: `card_count` e o texto "de 100", com o aviso de acima ou abaixo quando a API mandar. Land básica conta nas 100.

Identidade de cor sai como letras `W` `U` `B` `R` `G`, não só como cor. Lista vazia mostra "incolor". `partner_kind`, quando vem na carta do deck, aparece como texto secundário (`partner`, `partner_with`, `friends_forever`, `background`, `choose_a_background`, `doctors_companion`). Isso não valida a cadeira; o aviso `commander_pairing` valida.

## Telas

O uso é com o papel na mão. Bulk, deck e encontro funcionam na largura de um telefone: a ação principal da linha fica visível, o resto vai para um menu. Confirmação destrutiva é diálogo, não um clique só.

### Entrar, cadastrar, recuperar

Entrar: um campo "Nick ou e-mail", senha, link para cadastrar e para recuperar. O identifier vai inteiro; quem decide se é e-mail é a API, pela presença de `@`.

Cadastrar: e-mail, senha, nick. Erro de nick duplicado usa o `detail` da API.

Recuperar: um campo "Nick ou e-mail". Sucesso é a frase única da seção de sessão, com o formulário desabilitado depois do envio.

Senha: obrigatória no cliente. Tamanho mínimo e política são os do Supabase; a mensagem que chega na API é a que o campo mostra.

### Início

Lista os grupos. Cada item leva ao bulk e marca "Dono" quando `owner_id` é a pessoa. Vazio: "Você ainda não está em um grupo." e o botão de criar.

Criar pede o nome (texto com algo depois do trim, no máximo 80 caracteres).

Acima da lista, os convites de `GET /invitations`. Cada um tem o nome do grupo, o nick de quem convidou, Aceitar e Recusar. Recusar pede confirmação. Aceitar entra no grupo e abre o bulk dele. Lista vazia não ocupa a tela.

### Bulk

`GET /groups/{id}/copies`. A URL guarda `q` e `estado` (`available`, `reserved`, `in_deck`, `in_use_elsewhere`). O filtro é local, nos nomes e na `visibility`. Não há paginação na API; a tela lista o que veio.

Cada linha: nome da carta, tipo, cores, casa, preço, e o estado:

- `available`: Livre
- `reserved`: Reservada
- `in_deck`: "No deck de {nick}" e o nome do deck. Se `locked`, o selo Travada; se não, Destravada
- `in_use_elsewhere`: "Em uso em outro grupo", sem mais detalhe

Cadastrar abre a busca do catálogo e, depois da carta escolhida, pede quantidade e casa.

Quantidade é inteiro de 1 a 99. O teto é da tela, para um zero a mais não criar centenas de cópias. A API não define máximo.

A casa padrão é a pessoa logada, entre os membros `accepted`. Outra casa só entra na lista se for `accepted` em todos os grupos marcados.

Grupos: o da URL sempre entra. A opção "Vincular a todos os meus grupos" começa marcada quando a casa é a própria pessoa e, marcada, omite `group_ids` (a API vincula todos os grupos dela). Desmarcada, a pessoa escolhe outros grupos seus e a tela manda esses ids em `group_ids`. Se a casa deixa de ser a pessoa logada, a opção some e os grupos passam a ser explícitos: no mínimo o grupo atual. A tela não tenta adivinhar a interseção de membros de todos os grupos da casa alheia além dos que ela mesma marcou.

Carta cadastrada permanece na lista mesmo com preço nulo.

### Decks do grupo

Lista os decks da pessoa. Vazio: "Você ainda não tem um deck neste grupo."

Criar pede nome e formato. O seletor explica:

- Commander 10: até R$ 10 nas cartas e até R$ 5 na soma dos comandantes
- Commander 100, 200 e 500: teto de preço ainda não definido
- Competitivo: sem teto de preço

### Deck

Só o dono edita. Outra pessoa não chega aqui pela lista do grupo, que só devolve os decks dela. Um link direto de deck alheio cai no erro da API.

Cabeçalho: nome, formato, contagem, orçamento, avisos. Renomear e trocar formato usam `PATCH`. Apagar pede confirmação: "As cartas voltam para o bulk, livres, na casa de quem está com elas."

Dois blocos, comandantes e o restante, pela `role`. Carta sem preço mostra "sem preço". Aviso com `card_copy_id` repete na linha da carta.

Marcar comandante manda a lista inteira de `card_copy_ids` que devem ficar com `role` `commander`. Tirar o último manda `[]`. O botão só aparece na carta com `can_toggle_commander`; a API recusa com 409 o comandante inválido.

A linha do deck na lista do grupo mostra a foto e o nome dos `commanders` (ou "Sem comandante"). O cabeçalho do deck e a linha do deck na lista do grupo mostram `color_identity` com os ícones das cores (símbolos do Scryfall; lista vazia usa o símbolo de incolor) e `color_identity_name`. Cada carta do deck tem a foto de `catalog.image_url`.

Adicionar tem dois caminhos, os dois a partir desta tela:

- Adicionar carta: a mesma busca de catálogo, com `deck_id`, e a quantidade. `POST /decks/{id}/copies`. A API trava a cópia livre da casa no bulk, se houver, e cadastra o resto já no deck, travado.
- Pegar do bulk o que já está na casa da pessoa continua sendo ação da linha livre no bulk, com este deck como destino. Se ela abrir o deck e ainda não tem carta, o texto aponta para o bulk.

Mover lista os outros decks da pessoa. A API não tem um deck global: o diálogo busca `GET /groups/{id}/decks` em cada grupo de `GET /groups`. Destino no mesmo deck não aparece. Comandante no deck de origem volta a `main`; a pessoa marca de novo se quiser. A tela diz isso antes de confirmar.

### Encontro

Duas listas, só daquele grupo.

Levar (`to_bring`): carta, quem pediu, deck de destino, se veio do bulk ou de um deck. Não há botão de confirmar entrega. O texto da seção: "Leve estas cartas no próximo encontro. Quem pediu confirma no app quando o papel estiver na mão dela."

Receber (`to_receive`):

- `pending_acceptance`: "Esperando aceite de {nick}". Ação: Cancelar.
- `awaiting_handoff`: "Esperando a carta". Ações: Cancelar e Confirmar.

Confirmar é diálogo: "Confirme só se a carta já está na sua mão. A casa passa a ser você e ela entra no deck travada."

Cancelar é diálogo: "O pedido é desfeito e a carta volta para onde estava."

Lista vazia diz o que ela é. "Nada para levar neste grupo." e "Nada para receber neste grupo."

### Membros

Lista com nick, selo Dono no `owner_id`, e selo Convidado quando `status` é `invited`.

Convidar pede o nick. 409: "Essa pessoa já foi convidada ou já está no grupo." Nick que a API não acha: o `detail`, ou "Não há conta com esse nick."

Renomear só para o dono.

Sair pede confirmação com o que a API faz:

- os decks de quem sai neste grupo são apagados;
- carta desses decks que está na casa de outra pessoa volta ao bulk, livre;
- carta na casa de quem sai deixa este grupo e continua nos outros grupos em que já estava;
- se quem sai é o dono e ainda há gente, o membro `accepted` mais antigo fica dono;
- se era a última pessoa, o grupo acaba.

Não há expulsar.

## Ações da cópia

A trava é da cópia. A tela não oferece trava por grupo. Reservada some como opção de pedido em todo grupo, porque a lista de cada grupo já vem com `reserved`.

| O que a pessoa vê | Ação | Pedido |
| --- | --- | --- |
| Livre, casa sou eu | Pegar na hora | `POST /decks/{destino}/take` |
| Livre, casa sou eu | Compartilhar | `POST /copies/{id}/groups` |
| Livre, casa sou eu | Remover | `DELETE /copies/{id}` |
| Livre, casa de outra pessoa | Solicitar | `POST /decks/{destino}/requests` |
| No deck de outra pessoa, neste grupo, destravada | Solicitar | `POST /decks/{destino}/requests` |
| No deck de outra pessoa, travada | nenhuma | — |
| Em uso em outro grupo | nenhuma | — |
| Reservada, eu pedi | Cancelar | `POST /requests/{id}/cancel` |
| No meu deck, pedido `pending_acceptance` de outra pessoa | Aceitar ou recusar | `POST /requests/{id}/accept` ou `/reject` |
| No meu deck, sem pedido aberto | Mover, devolver, travar ou destravar | rotas `/cards/{card_copy_id}/...` |
| Casa sou eu, ou eu cadastrei, e não é básica | Atualizar preço | `POST /copies/{id}/refresh-price` |

Pegar na hora e solicitar pedem o deck de destino entre os decks da pessoa neste grupo. Um deck só não abre escolha. Nenhum deck leva a criar um. Vários abrem a lista.

Compartilhar lista os outros grupos da pessoa. Cópia livre ganha o vínculo livre. Cópia no deck pode ganhar o vínculo e continua travada; a tela diz isso. Reservada não mostra compartilhar.

Remover só com a cópia livre e a casa sendo a pessoa. Confirmação: "Isso apaga o registro em todos os grupos. Só faça isso se o papel saiu de circulação."

Quem está com a carta no bulk não vê aceitar nem recusar. Pedido de bulk já nasce esperando a carta.

Segunda pessoa na mesma cópia recebe 409. Toast: "Essa carta acabou de ser reservada por outra pessoa." A lista é recarregada.

Devolver ao bulk: "A carta sai do deck e volta a ficar livre na sua casa." Travar e destravar não pedem diálogo; o selo muda depois da resposta.

Atualizar preço pode continuar nulo. A tela não trata isso como erro. O aviso `missing_price` segue até existir preço.

## Erros

| Status | Texto quando não há `detail` string |
| --- | --- |
| 401, refresh esgotado | Sua sessão expirou. |
| 404 num grupo, deck ou cópia | Esse recurso não está disponível. |
| 409 num pedido | Essa carta acabou de ser reservada por outra pessoa. |
| 409 num convite | Essa pessoa já foi convidada ou já está no grupo. |
| 422 | Revise os campos. |
| rede ou outro | Não foi possível concluir. Tente de novo. |

Mutação não usa atualização otimista no estado da cópia. O 409 precisa do estado novo da API. Depois de uma mutação que mexe em cópia, deck ou pedido, invalidar as cópias dos grupos envolvidos, os decks envolvidos e o encontro desses grupos. Mudança de grupo ou convite invalida `GET /groups` e `GET /invitations`.

## O que fica de fora

Cobrança, frete, partida, push, e-mail de convite, bloqueio de deck ilegal, aceite de quem está com a carta no bulk, e teto de Commander 100, 200 e 500. A tela não calcula esses tetos por conta própria quando a regra ainda não existe.

Também fica de fora: login direto no Supabase, busca no Scryfall pelo browser, preço pela LigaMagic pelo browser, expulsar membro, e mostrar deck ou nick de um grupo do qual a pessoa não participa.

## Ordem de implementação

Cada etapa substitui o que a anterior deixou pela metade e fecha com o fluxo percorrido no navegador, no telefone e no desktop. A API da mesma etapa é a fonte. Onde a rota ainda não existe, a tela mostra o vazio descrito aqui e não simula carta, grupo ou pedido.

1. Sessão. `src/lib/api/client.ts` com Bearer e refresh. `src/lib/auth/session.ts`. Schemas e telas de entrar, cadastrar, recuperar e `GET /me`. Layout protegido. Cabeçalho com nick e sair. Apagar publicações e o fallback do JSONPlaceholder. `VITE_API_URL` obrigatório.
2. Grupos. Início, criar, layout do grupo, membros, convite, renomear, sair. Caixa de `GET /invitations` quando a rota existir.
3. Catálogo. Busca usada pelos formulários de cadastrar, ainda sem gravar cópia se a etapa 4 não entrou. Preço vazio é o estado normal.
4. Bulk. Lista, filtros na URL, cadastrar com quantidade, casa e grupos, preço nulo, land básica a R$ 0,00, remover, compartilhar, atualizar preço.
5. Decks. Criar, detalhe, avisos, orçamento do Commander 10, comandantes, cadastrar direto, pegar na hora a partir do bulk.
6. Pedidos. Solicitar do bulk e do deck destravado, 409, aceitar e recusar no deck de origem, encontro, cancelar, confirmar com a carta na mão. Cópia reservada sem ação para o resto do grupo.
7. Mover, devolver, travar, destravar. A saída do grupo já está explicada no diálogo da etapa 2; aqui se confere, com a API, que a carta da própria casa some daquele grupo e a carta da casa alheia volta ao bulk.
8. Nada novo de preço até o adaptador da LigaMagic existir no backend. Atualizar preço e o aviso `missing_price` continuam como na etapa 4.

## Arquivos

Contrato e query keys junto da função que chama a API:

- `src/lib/api/auth.ts`
- `src/lib/api/groups.ts`
- `src/lib/api/catalog.ts`
- `src/lib/api/copies.ts`
- `src/lib/api/decks.ts`
- `src/lib/api/requests.ts`
- `src/lib/money.ts` para formatar centavos

Formulários e listas em `src/components/auth`, `groups`, `copies`, `decks` e `requests`. Rota fina: loader, search params e composição. O `PageHeader` que já existe serve para o título das telas.
