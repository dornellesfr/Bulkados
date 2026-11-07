# Spec do frontend

O que este repositório precisa implementar para o produto descrito em [conceito.md](conceito.md), em cima do contrato de [spec-backend.md](../../backend/docs/spec-backend.md). A interface não recalcula regra de Commander, não chama Scryfall e não chama LigaMagic. Ela mostra o estado que a API devolve e dispara a transição que a API já definiu.

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

Login e cadastro que devolvem `access_token` e `refresh_token` gravam a sessão e em seguida chamam `GET /me`. O e-mail da conta vem de `GET /me`, não do corpo do login.

A spec do backend não descreve confirmação de e-mail. Cadastro com tokens entra direto. Cadastro sem tokens vai para `/entrar` com o texto "Conta criada. Entre com seu e-mail." A tela não inventa um aviso de e-mail de confirmação.

Recuperação de senha mostra a `message` da API. Se o corpo não trouxer texto, a frase fixa é "Se existir uma conta com esse e-mail, enviamos as instruções para trocar a senha." A frase é a mesma com conta existente ou não.

Sair apaga os dois tokens e volta para `/entrar`.

## Rotas

Públicas, e quem já tem sessão nelas cai em `/`:

- `/entrar`
- `/cadastrar`
- `/recuperar-senha`

Protegidas, atrás de um layout sem path (`src/routes/_app.tsx`). Sem sessão, `beforeLoad` manda para `/entrar` e guarda o href em `redirect` para voltar depois do login.

- `/` grupos e convites recebidos
- `/perfil` e-mail da conta e troca de senha
- `/grupos/$groupId` bulk daquele grupo
- `/grupos/$groupId/decks` decks da pessoa, que são globais e podem receber cartas de qualquer bulk
- `/grupos/$groupId/decks/$deckId` deck
- `/grupos/$groupId/encontro` levar e receber
- `/grupos/$groupId/membros` membros, convite, nome, saída

Não existe `GET /groups/{id}`. O layout do grupo lê o nome em `GET /groups`. Id ausente nessa lista, ou 404 da API, vira a página de não encontrado. O texto é "Esse grupo não está disponível." Não diz se a pessoa está fora do grupo: a API esconde o recurso de quem não é membro `accepted`.

Dentro do grupo, a navegação é Bulk, Decks, Encontro, Membros. Encontro carrega `GET /groups/{id}/handoffs` no layout e mostra a soma de `to_bring` e `to_receive` quando for maior que zero.

Cabeçalho logado: menu (Grupos, Perfil, Sair), nome do app `bulkados` com link para `/`, tema. O link de publicações sai.

Filtros de lista ficam na URL, no mesmo padrão de `validateSearch` que o exemplo já usa.

## Contrato que o cliente valida

O Zod descreve os campos abaixo. Campo desconhecido é descartado. Campo obrigatório ausente quebra a leitura de propósito, no `errorComponent`. Se o OpenAPI batizado no backend usar outro nome, o schema deste repositório acompanha o OpenAPI; a tela continua precisando da informação descrita aqui.

Erro: a API no estilo FastAPI manda `{ "detail": ... }`. `detail` string vira a mensagem do formulário ou do toast. `detail` lista vira uma frase em português sobre o campo (e-mail ou senha). Status sem corpo usa o texto da tabela de erros, mais abaixo.

### Auth

`POST /auth/register` com `first_name`, `last_name`, `email`, `password`. Nome e sobrenome de 1 a 80 caracteres. Senha de 6 a 128 caracteres.

`POST /auth/login` com `email`, `password`. Resposta usada: `access_token`, `refresh_token`, `expires_in`. E-mail ou senha errados usam a mesma mensagem.

`POST /auth/refresh` com `refresh_token`. Mesma forma de token.

`POST /auth/forgot-password` com `email`.

`POST /auth/password` com `current_password`, `new_password`, autenticado. 204 quando salva. Senha atual errada não é 401.

`GET /me` devolve `id`, `email`, `first_name`, `last_name` e `created_at`. `PATCH /me` salva nome e sobrenome.

### Grupos

`POST /groups` `{ name }` e `PATCH /groups/{id}` `{ name }`.

`GET /groups` lista grupos em que a pessoa é membro `accepted`:

- `id`, `name`, `owner_id`, `created_at`

Dono na tela é `owner_id === me.id`. Não há campo extra de papel.

`GET /groups/{id}/members`:

- `user_id`, `email`, `first_name`, `last_name`, `status` (`invited` ou `accepted`), `created_at`

`POST /groups/{id}/invitations` `{ email }`.

`POST /invitations/{id}/accept` e `POST /invitations/{id}/decline`.

`POST /groups/{id}/leave`.

`GET /groups` não inclui convite pendente: quem está `invited` não lê o grupo e o grupo não entra na lista.

`GET /invitations` lista só os convites `invited` de quem está logado:

- `id`
- `group`: `id`, `name`
- `invited_by`: `id`, `email`, `first_name`, `last_name`
- `created_at`

Aceitar e recusar usam esse `id`. Lista vazia não ocupa a tela.

### Catálogo

`GET /catalog/cards?q=`. Cada item: `oracle_id`, `name_en`, `name_pt` nulo, `mana_cost` nulo, `image_url` nulo (link da imagem da carta), `type_line` nulo, `color_identity` (lista), `is_basic`. A API devolve no máximo 20 itens, por prefixo do nome em português ou inglês, sem diferenciar acento nem maiúscula.

A busca dispara com pelo menos 2 caracteres, com debounce, e cancela a request anterior. Campo vazio não chama a API.

### Cópias

`GET /groups/{id}/copies`. Cada item:

- `id`
- `catalog`: `oracle_id`, `name_en`, `name_pt`, `image_url`, `mana_cost`, `type_line`, `oracle_text`, `color_identity`, `is_basic`, `keywords`, `can_be_commander`, `partner_kind` nulo
- `holder`: `id`, `email`, `first_name`, `last_name`
- `added_by`: `id`, `email`, `first_name`, `last_name`
- `price_cents` nulo, `price_fetched_at` nulo
- `state`: `available`, `reserved`, `in_deck`
- `locked`
- `visibility`: `available`, `reserved`, `in_deck`, `in_use_elsewhere`
- `deck` nulo, ou `{ id, name, owner: { id, email, first_name, last_name } }` quando `visibility` é `in_deck` (o dono do deck participa de algum grupo de quem vê)
- `open_request` nulo, ou `{ id, status, source, requester: { id, email, first_name, last_name } }` com `status` `pending_acceptance` ou `awaiting_handoff` e `source` `bulk` ou `deck`
- `group_ids`: grupos em que a cópia está vinculada

`in_use_elsewhere` é a cópia no deck de alguém que não participa de nenhum grupo de quem vê. Nesse caso `deck` vem nulo: a tela não mostra nome de deck nem e-mail de outro grupo.

`POST /groups/{id}/copies`:

- `oracle_id`
- `quantity`, inteiro `>= 1`
- `holder_id` opcional; omitido, a casa é quem cadastra
- `group_ids` opcional, a lista exata dos grupos da carta. Omitido com a casa sendo quem cadastra, a API vincula todos os grupos dela. A tela sempre manda a lista marcada.

Resposta: a lista das cópias criadas. Falha de preço não falha o cadastro; `price_cents` nulo é sucesso.

`POST /copies/{id}/groups` `{ group_id }` inclui a cópia num grupo.

`DELETE /copies/{id}/groups/{group_id}` tira de um grupo. O último grupo e uma cópia que está num deck respondem 409 até ser devolvida ao bulk.

`DELETE /copies/{id}`.

`POST /copies/{id}/refresh-price` devolve a cópia com o preço novo ou ainda nulo.

### Decks

`POST /decks` `{ name, format }` cria um deck da pessoa. O deck não pertence a um grupo e pode receber cartas de vários bulks. `format` é `commander_10`, `commander_100`, `commander_200`, `commander_500` ou `competitive`.

`GET /decks` lista os decks de quem está logado, em qualquer bulk: `id`, `name`, `format`, `created_at`, `color_identity`, `color_identity_name`, `commanders`. A contagem fica no detalhe. `POST /groups/{id}/decks` e `GET /groups/{id}/decks` continuam valendo por compatibilidade e devolvem os mesmos decks globais da pessoa.

`GET /decks/{id}`:

- `id`, `name`, `format`, `owner_id`, `created_at`
- `color_identity`, `color_identity_name`
- `card_count`, `main_price_cents`, `commander_price_cents`
- `warnings`: `code`, `card_copy_id` nulo, `message`
- `cards`: `card_copy_id`, `role` (`commander` ou `main`), `locked`, `price_cents` nulo, `holder` (`id`, `email`, `first_name`, `last_name`), `catalog` (os campos da cópia, mais `commander_legal`), `open_request` no mesmo formato da lista de cópias, `can_toggle_commander`

O texto do aviso é o `message` da API. O `code` só escolhe o lugar na tela. A interface não tem uma segunda lista de regras.

`PATCH /decks/{id}` com `name`, `format`, ou os dois.

`DELETE /decks/{id}` devolve as cartas ao bulk. A tela pede confirmação antes.

`POST /decks/{id}/commanders` `{ card_copy_ids }` substitui o conjunto inteiro. Pode ir lista vazia.

`POST /decks/{id}/take` `{ card_copy_id, as_commander }`. `as_commander` omitido é falso: a carta entra como `main`. Verdadeiro entra como `commander`, com a mesma validação de marcar comandante.

`POST /decks/{id}/copies` `{ oracle_id, quantity }`. A casa é quem cadastra. Não há campo de casa nem de grupo nesse corpo.

`POST /decks/{id}/cards/{card_copy_id}/move` `{ target_deck_id, as_commander }`. Sem `as_commander`, comandante na origem volta a `main` no destino. Com ele, entra na cadeira se a dupla e a identidade de cor fecharem.

`POST /decks/{id}/cards/{card_copy_id}/return`, `/lock` e `/unlock` sem corpo.

### Pedidos

`POST /decks/{id}/requests` `{ card_copy_id, group_id?, as_commander? }`. O `id` da URL é o deck de destino, sempre um deck de quem pede. A API decide se o pedido nasce do bulk ou de um deck pelo estado da cópia. A tela não manda `source`. `as_commander` entra como comandante no deck destino, com a mesma validação de marcar comandante. `group_id` é o bulk em que a carta está sendo vista; omitido, a API escolhe um grupo em comum.

`POST /requests/{id}/accept`, `/reject`, `/cancel` e `/confirm` sem corpo. Quem aceita ou recusa é a casa física, num pedido de bulk, ou o dono do deck de origem, num pedido de deck. Quem cancela é sempre quem pediu. A confirmação é dos dois lados: o solicitante confirma o recebimento e o detentor atual confirma a entrega.

`GET /groups/{id}/handoffs`:

- `to_bring`: pedidos abertos em que a casa é quem está logado ou o deck de origem é dele. Inclui os `pending_acceptance` que esperam a decisão de aceitar/recusar e os `awaiting_handoff` que ele precisa levar. Item com `id`, `source`, `catalog` (`name_en`, `name_pt`), `status`, `requester`, `holder`, `target_deck` (`id`, `name`), `requester_confirmed`, `holder_confirmed`.
- `to_receive`: pedidos abertos em que quem está logado pediu. Item com `id`, `source`, `catalog`, `status`, `holder`, `target_deck`, `requester_confirmed`, `holder_confirmed`.

Os pedidos pendentes também aparecem na carta do deck de origem, para o dono daquele deck, quando `open_request.status` é `pending_acceptance`.

### Onde cada aviso aparece

| `code`                                                            | Lugar                                                      |
| ----------------------------------------------------------------- | ---------------------------------------------------------- |
| `deck_over_100`, `deck_under_100`                                 | Contagem do deck                                           |
| `budget_main`, `budget_commanders`                                | Orçamento                                                  |
| `missing_price`                                                   | Orçamento e a carta, quando houver `card_copy_id`          |
| `commander_pairing`                                               | Bloco dos comandantes                                      |
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

Cadastrar: nome, sobrenome, e-mail e senha. E-mail duplicado usa o `detail` da API. Perfil mostra o e-mail e deixa salvar nome e sobrenome.

Recuperar: um campo "Nick ou e-mail". Sucesso é a frase única da seção de sessão, com o formulário desabilitado depois do envio.

Senha: obrigatória no cliente. Tamanho mínimo e política são os do Supabase; a mensagem que chega na API é a que o campo mostra.

### Início

Lista os grupos. Cada item leva ao bulk e marca "Dono" quando `owner_id` é a pessoa. Vazio: "Você ainda não está em um grupo." e o botão de criar.

Criar pede o nome (texto com algo depois do trim, no máximo 80 caracteres).

Acima da lista, os convites de `GET /invitations`. Cada um tem o nome do grupo, o nome de quem convidou, Aceitar e Recusar. Recusar pede confirmação. Aceitar entra no grupo e abre o bulk dele. Lista vazia não ocupa a tela.

### Bulk

`GET /groups/{id}/copies`. A URL guarda `q`, `estado` (`available`, `in_deck`, `todas`), `cores` (lista com `W`, `U`, `B`, `R`, `G` e `C`), `cmc` (`0` a `7+`), `destino` e `vista` (`lista`; o padrão `cartas` fica de fora da URL). Sem `estado`, o filtro começa em Livre (`available`) e mostra só o que está livre. `in_deck` é Reservadas e mostra o que já está num deck, inclusive o que está travado. `todas` mostra todos os estados. A lista já vem só daquele grupo: o filtro não mistura cartas de outros bulks. A busca por nome é local. Cores é um multiselect com o ícone de cada cor e usa a identidade de cor da carta; incolor entra como `C`. Custo de mana usa as faixas `0`, `1`, `2`, `3`, `4`, `5`, `6` e `7+`. A organização fica ao lado dos filtros. `cartas` é a grade, uma cópia por cartão: imagem grande, nome, custo de mana à direita do nome, identidade de cor numa linha própria, "Lendária" quando o tipo traz isso, onde está, o status e o botão principal. `lista` é uma linha por carta: a miniatura permanece, o custo fica com o nome, as cores ficam abaixo, e tipo, casa, preço, estado e a ação ocupam a largura.

O status aparece por texto, cor e ícone: **Livre** em verde, **Reservada** em azul (`in_deck` destravada), **Travada** em âmbar (`locked`) e **Indisponível** em cinza (pedido aberto ou carta em uso fora dos seus grupos). O mesmo ícone aparece no canto da imagem. Carta indisponível fica esmaecida e o botão fica desabilitado, mas o cartão continua clicável para abrir o detalhe. Clicar no cartão, travado ou não, abre o detalhe: imagem, tipo, custo separado das cores, texto da carta numa caixa, estado, casa, preço e os mesmos botões de selecionar e de `...` que existem fora do modal.

Cada linha ou cartão mostra a ação principal e o menu `...`:

- `available`: Livre. Ação **Selecionar**; se a casa é outra pessoa, o mesmo botão abre a solicitação para o deck de destino.
- `reserved` (pedido aberto): Indisponível. O botão fica desabilitado; quem pediu vê **Cancelar** no menu.
- `in_deck` destravada: Reservada, com o nome do deck e o dono. Ação **Selecionar** se o deck é seu; **Solicitar** se é de outra pessoa.
- `in_deck` travada: Travada, com cadeado. Ação **Indisponível**, desabilitada, mas o cartão abre o detalhe.
- `in_use_elsewhere`: Indisponível. Ação desabilitada; a tela não revela o deck nem o e-mail de quem está fora dos seus grupos.

Cadastrar abre a busca do catálogo e, depois da carta escolhida, pede quantidade e onde entra. "Livre no bulk" segue com casa e grupos. Um deck da pessoa manda `POST /decks/{id}/copies`: a carta entra destravada, na casa de quem cadastra. A lista de decks é global e não depende do bulk aberto. Se ela já tem essa carta livre no bulk deste grupo, essa cópia é a que entra no deck; o que faltar é cadastrado. Sem nenhum deck, a única opção é livre, e a tela diz para criar um deck se quiser que a carta já entre com ela. Casa e grupos ficam ocultos quando o destino é um deck.

Quantidade é inteiro de 1 a 99. O teto é da tela, para um zero a mais não criar centenas de cópias. A API não define máximo.

A casa padrão é a pessoa logada, entre os membros `accepted`. Outra casa só entra na lista se for `accepted` em todos os grupos marcados.

Grupos: uma lista com Todos e cada grupo em que a casa escolhida já entrou. Todos começa marcado. A tela manda os ids marcados em `group_ids`. Trocar a casa marca de novo os grupos dessa pessoa. A casa só lista quem é `accepted` em todos os grupos marcados.

Carta cadastrada permanece na lista mesmo com preço nulo.

### Decks da pessoa

Lista os decks da pessoa, em qualquer bulk. Vazio: "Você ainda não tem nenhum deck." Criar pede nome e formato; o deck criado já pode receber cartas de qualquer bulk. O seletor explica:

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

- Adicionar carta: a mesma busca de catálogo, com `deck_id`, e a quantidade. `POST /decks/{id}/copies`. A API coloca no deck uma cópia livre da casa, se houver, e cadastra o resto já no deck. Nenhuma das duas fica travada.
- Selecionar do bulk o que já está na casa da pessoa continua sendo ação do cartão livre no bulk, com este deck como destino. Se ela abrir o deck e ainda não tem carta, o texto aponta para o bulk. Travar e destravar ficam nesta tela, não no bulk.

Mover lista os outros decks da pessoa, de qualquer bulk, com `GET /decks`. Destino no mesmo deck não aparece. Comandante no deck de origem volta a `main`; a pessoa marca de novo se quiser. A tela diz isso antes de confirmar.

### Encontro

Duas listas, só daquele grupo.

Levar (`to_bring`): pedidos abertos em que a carta está na sua casa ou no seu deck. Os `pending_acceptance` pedem uma decisão: Aceitar ou Recusar. Os já aceitos mostram carta, quem pediu, deck de destino, se veio do bulk ou de um deck, e o estado das duas confirmações. Ação: Confirmar entrega. Texto da seção: "Aceite os pedidos e leve as cartas no próximo encontro. Quem entrega e quem recebe confirmam no app."

Receber (`to_receive`):

- `pending_acceptance`: "Esperando aceite de {nome}". Ação: Cancelar.
- `awaiting_handoff`: "Esperando a carta" ou o texto de quem já confirmou. Ações: Cancelar e Confirmar recebimento.

Confirmar recebimento é diálogo: "Confirme só se a carta já está na sua mão. A carta só muda de mão quando a outra pessoa também confirmar. Trave no deck se não quiser que peçam."

Confirmar entrega é diálogo: "Confirme só se você já entregou a carta. A carta só muda de mão quando a outra pessoa também confirmar."

Cancelar é diálogo: "O pedido é desfeito e a carta volta para onde estava."

Lista vazia diz o que ela é. "Nada para levar neste grupo." e "Nada para receber neste grupo."

### Membros

Lista com nome e sobrenome, o e-mail embaixo, selo Dono no `owner_id`, e selo Convidado quando `status` é `invited`.

Convidar pede o e-mail. 409: "Essa pessoa já foi convidada ou já está no grupo." E-mail que a API não acha: o `detail`, ou "Não há conta com esse e-mail."

Renomear só para o dono.

Sair pede confirmação com o que a API faz:

- os seus decks continuam existindo, com as cartas que estiverem neles; o deck não é do grupo;
- cartas na sua casa deixam de aparecer neste grupo e continuam nos outros grupos e nos seus decks;
- pedidos abertos neste grupo em que você pediu ou está com a carta são cancelados;
- se quem sai é o dono e ainda há gente, o membro `accepted` mais antigo fica dono;
- se era a última pessoa, o grupo acaba e os decks continuam.

Não há expulsar.

## Ações da cópia

A trava é da cópia. A tela não oferece trava por grupo, e o bulk não trava nem destrava: isso fica na tela do deck. Reservada é a carta que já está num deck; travada é reservada e marcada pelo dono para não ser pedida. Pedido aberto deixa a carta Indisponível em todos os grupos.

O botão principal do cartão no bulk tem três rótulos. O mesmo botão e o menu ficam no detalhe da carta. O menu, no ícone de três pontos, não trava nem destrava.

| O que a pessoa vê                          | Botão                                | Pedido                                                  |
| ------------------------------------------ | ------------------------------------ | ------------------------------------------------------- |
| Na minha casa, livre                       | Selecionar                           | `POST /decks/{destino}/take`                            |
| Na minha casa, já num deck meu, destravada | Selecionar                           | `POST /decks/{origem}/cards/{id}/move`                  |
| Livre no bulk, na casa de outra pessoa     | Selecionar                           | `POST /decks/{destino}/requests`                        |
| No deck de outra pessoa, destravada        | Solicitar, com ícone de carta em uso | `POST /decks/{destino}/requests`                        |
| Travada no meu deck                        | Indisponível, com cadeado            | o botão fica desativado, mas o cartão abre o detalhe    |
| Reservada por um pedido aberto             | Indisponível                         | o botão fica desativado; quem pediu vê Cancelar no menu |
| Em uso fora dos meus grupos                | Indisponível                         | o botão fica desativado                                 |

| O que a pessoa vê                                        | Menu                                                  | Pedido                                                                |
| -------------------------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------- |
| Casa sou eu, e não está reservada                        | Mudar bulks                                           | `POST /copies/{id}/groups` ou `DELETE /copies/{id}/groups/{group_id}` |
| Livre, casa sou eu                                       | Remover                                               | `DELETE /copies/{id}`                                                 |
| Reservada, eu pedi                                       | Cancelar                                              | `POST /requests/{id}/cancel`                                          |
| Casa sou eu, ou eu cadastrei, e não é básica             | Atualizar preço                                       | `POST /copies/{id}/refresh-price`                                     |
| No meu deck, pedido `pending_acceptance` de outra pessoa | Aceitar ou recusar, na tela do deck ou no Encontro    | `POST /requests/{id}/accept` ou `/reject`                             |
| No meu deck, sem pedido aberto                           | Mover, devolver, travar ou destravar, na tela do deck | rotas `/cards/{card_copy_id}/...`                                     |

Selecionar e solicitar abrem o modal na hora. O botão do cartão não espera a API. A primeira etapa escolhe criar um deck novo ou usar um deck que já existe. Sem nenhum deck da pessoa, a segunda opção fica desabilitada. Deck novo pede nome e formato, como criar deck. Deck existente lista os decks da pessoa em qualquer bulk; no mover, o deck de origem fica de fora. Se a URL tem `destino`, esse deck já vem marcado. Selecionar e mover oferecem "Adicionar como comandante". A caixa só habilita quando a cadeira fecha: zero comandantes e a carta pode ser comandante, ou um comandante e a dupla é válida (Partner, Partner with, Friends forever, Choose a Background com Background, Doctor com Doctor's companion). `partner_kind`, o texto e as keywords da carta vêm do catálogo. Dois comandantes deixam a caixa desabilitada. Enquanto o detalhe do deck carrega para conferir se as outras cartas continuam dentro da identidade de cor, essa caixa fica em skeleton. Solicitar não marca comandante. O menu abre fora do cartão, por cima da grade, e também dentro do detalhe.

Mudar bulks lista os grupos da pessoa. Incluir cria o vínculo. Tirar remove um. Cópia com pedido aberto não mostra mudar bulks. O texto deixa claro que a carta continua no estado em que está.

Remover só com a cópia livre e a casa sendo a pessoa. Confirmação: "Isso apaga o registro em todos os grupos. Só faça isso se o papel saiu de circulação."

Quem está com a carta no bulk aceita ou recusa pelo Encontro ou pelo detalhe da própria carta; o pedido nasce pendente. Aceitar não move a carta: ela só entra no deck quando os dois confirmam no encontro.

Segunda pessoa na mesma cópia recebe 409. Toast: "Essa carta acabou de ser reservada por outra pessoa." A lista é recarregada.

Devolver ao bulk: "A carta sai do deck e volta a ficar livre na sua casa." Travar e destravar não pedem diálogo; o selo muda depois da resposta.

Atualizar preço pode continuar nulo. A tela não trata isso como erro. O aviso `missing_price` segue até existir preço.

## Erros

| Status                       | Texto quando não há `detail` string                  |
| ---------------------------- | ---------------------------------------------------- |
| 401, refresh esgotado        | Sua sessão expirou.                                  |
| 404 num grupo, deck ou cópia | Esse recurso não está disponível.                    |
| 409 num pedido               | Essa carta acabou de ser reservada por outra pessoa. |
| 409 num convite              | Essa pessoa já foi convidada ou já está no grupo.    |
| 422                          | Revise os campos.                                    |
| rede ou outro                | Não foi possível concluir. Tente de novo.            |

Mutação não usa atualização otimista no estado da cópia. O 409 precisa do estado novo da API. Depois de uma mutação que mexe em cópia, deck ou pedido, invalidar as cópias dos grupos envolvidos, os decks envolvidos e o encontro desses grupos. Mudança de grupo ou convite invalida `GET /groups` e `GET /invitations`.

## O que fica de fora

Cobrança, frete, partida, push, e-mail de convite, bloqueio de deck ilegal, e teto de Commander 100, 200 e 500. A tela não calcula esses tetos por conta própria quando a regra ainda não existe.

Também fica de fora: login direto no Supabase, busca no Scryfall pelo browser, preço pela LigaMagic pelo browser, expulsar membro, e mostrar deck ou e-mail de um grupo do qual a pessoa não participa.

## Ordem de implementação

Cada etapa substitui o que a anterior deixou pela metade e fecha com o fluxo percorrido no navegador, no telefone e no desktop. A API da mesma etapa é a fonte. Onde a rota ainda não existe, a tela mostra o vazio descrito aqui e não simula carta, grupo ou pedido.

1. Sessão. `src/lib/api/client.ts` com Bearer e refresh. `src/lib/auth/session.ts`. Schemas e telas de entrar, cadastrar, recuperar e `GET /me`. Layout protegido. Cabeçalho com menu e tema. Apagar publicações e o fallback do JSONPlaceholder. `VITE_API_URL` obrigatório.
2. Grupos. Início, criar, layout do grupo, membros, convite, caixa de `GET /invitations`, renomear, sair.
3. Catálogo. Busca usada pelos formulários de cadastrar, ainda sem gravar cópia se a etapa 4 não entrou. Preço vazio é o estado normal.
4. Bulk. Lista, filtros na URL, cadastrar com quantidade, casa e grupos, preço nulo, land básica a R$ 0,00, remover, compartilhar, atualizar preço.
5. Decks. Criar, detalhe, avisos, orçamento do Commander 10, comandantes, cadastrar direto, selecionar a partir do bulk sem travar.
6. Pedidos. Solicitar do bulk e do deck destravado, 409, aceitar e recusar pela casa (bulk) ou pelo dono do deck de origem, encontro, cancelar, confirmação dos dois lados. Cópia reservada sem ação para o resto do grupo.
7. Mover, devolver, travar, destravar. A saída do grupo já está explicada no diálogo da etapa 2; aqui se confere, com a API, que os decks continuam existindo e que a carta da própria casa some daquele grupo.
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
