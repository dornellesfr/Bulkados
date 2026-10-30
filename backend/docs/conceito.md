# Magic Bulk

App para um grupo de amigos montar decks de Commander a partir de um bulk compartilhado de cartas baratas. Este documento descreve o produto inteiro. O repositório atual implementa só o backend; a interface consome as regras daqui.

O formato de origem é o Commander 10: a soma das cartas que não são comandante fica em até R$ 10, e a soma dos comandantes fica em até R$ 5. O app também aceita Commander 100, Commander 200, Commander 500 e competitivo. O teto de preço desses outros formatos ainda não está definido.

## Pessoas

Cada pessoa tem uma conta e um nick único. O nick é o identificador usado no cadastro, no login e no convite.

O login aceita nick ou e-mail, com senha. A recuperação de senha usa o e-mail. A autenticação fica no Supabase; o nick e o restante dos dados do app ficam no backend.

No grupo, as pessoas se veem pelo nick.

## Grupos

Um grupo é um bulk com nome. Qualquer membro cria um grupo, convida pelo nick e a pessoa convidada aceita ou recusa. Uma pessoa participa de vários grupos ao mesmo tempo.

Dentro do grupo, todo membro pode cadastrar cartas, montar decks e solicitar cartas. O deck é de uma pessoa, dentro daquele grupo. Outra pessoa não edita o deck dela.

Quem criou o grupo dá o nome e pode renomear. Qualquer membro convida. Quem sai leva as cartas que estão na casa dela: elas saem do bulk e dos decks daquele grupo. As cartas que estão na casa de outras pessoas e estavam só no deck de quem saiu voltam para o bulk do grupo.

## A carta física

O que circula no app é uma cópia física, não uma quantidade genérica. Duas cartas com o mesmo nome são dois registros quando são dois papéis. Cada uma tem a própria casa, o próprio deck e a própria trava.

A casa é a pessoa com quem o papel está. No cadastro, a casa padrão é quem está cadastrando. Pode ser outro membro. Land básica também é cópia física; o preço dela é sempre zero.

A mesma cópia pode estar em vários grupos ao mesmo tempo. Isso acontece quando a pessoa da casa participa de mais de um grupo e a cópia foi vinculada a esses grupos. Quem reserva ou coloca a cópia num deck primeiro a trava em todos os grupos em que ela aparece. Existe um deck por vez para aquela cópia. Nos outros grupos ela continua visível como travada, e ninguém solicita.

Uma cópia livre na casa de uma pessoa pode ser compartilhada com outro grupo dessa pessoa. Entrar num grupo novo não publica sozinho as cartas que já estavam em casa.

### Catálogo e preço

A busca aceita o nome em inglês e em português. O catálogo da carta (nome, tipo, identidade de cor, se é land básica, se pode ser comandante, se é banida no Commander) vem do Scryfall.

O preço em reais vem da LigaMagic, o menor preço da carta, e fica gravado na cópia na hora do cadastro. Land básica não consulta preço: entra como R$ 0. Se o preço não vier, a cópia entra mesmo assim e o deck avisa que o orçamento está incompleto.

A LigaMagic não oferece API pública de preços. A busca de preço fica isolada no backend para a fonte poder ser ligada sem mudar o resto do app. Enquanto não houver uma fonte estável e permitida, o preço fica vazio e o aviso de orçamento incompleto cobre o caso.

## Decks

Na criação, a pessoa escolhe o formato:

| Formato | Preço |
| --- | --- |
| Commander 10 | Até R$ 10 fora do comandante e até R$ 5 na soma dos comandantes |
| Commander 100 | Teto ainda não definido |
| Commander 200 | Teto ainda não definido |
| Commander 500 | Teto ainda não definido |
| Competitivo | Sem teto de preço |

O Commander tradicional tem 100 cartas, comandante incluso. O app mostra a contagem e avisa quando o deck passa de 100 ou fica abaixo de 100. Não bloqueia salvar, adicionar nem solicitar.

O orçamento também só avisa. Não impede a carta de entrar no deck. No Commander 10 os dois tetos são separados: estourar o comandante não usa a folga das outras 99, e o contrário também. Preço desconhecido não entra na soma e gera aviso próprio. Competitivo não avisa preço. Os formatos 100, 200 e 500 guardam a escolha do formato e ficam sem aviso de preço até o teto ser definido.

Além do tamanho e do preço, o deck avisa as regras do Commander usual, sem bloquear:

- a identidade de cor de cada carta cabe na identidade dos comandantes;
- não há duas cartas com o mesmo nome, com as exceções de land básica e de carta que permite qualquer quantidade daquele nome;
- o comandante é elegível: criatura lendária, ou carta que pode ser comandante pela própria regra;
- a combinação de comandantes fecha (um comandante, ou uma dupla válida de Partner, Partner with, Friends forever, Background ou Doctor's Companion);
- carta banida no Commander.

Lands básicas contam nas 100 cartas, custam zero e podem repetir o nome.

### Comandante e identidade de cor

Duas regras bloqueiam, porque o resto do deck depende delas:

- só uma carta que pode ser comandante vira comandante: criatura lendária, planeswalker ou carta cujo texto diz que pode ser o comandante. Dois comandantes só valem como uma dupla válida: Partner, Partner with (cada um citando o outro), Friends forever, Choose a Background com um Background, ou Doctor com Doctor's companion. A tela oferece "Marcar comandante" só quando a escolha fica válida, e a API recusa o resto;
- a identidade de cor do deck é a união das cores dos comandantes. Com comandante, o app recusa a carta cuja identidade sai dela: ao adicionar, pegar do bulk, mover de outro deck ou solicitar. Sem comandante, não há limite. Carta incolor cabe em qualquer deck.

A identidade aparece com os ícones das cores e o nome da combinação (Azorius, Bant, Mono-verde, Incolor, Cinco cores). Incolor é só do deck cujo comandante não tem cor, como Karn ou Ullamog. Marcar comandante também respeita a identidade: se o deck tem carta fora da identidade que os comandantes passariam a ter, o app recusa e diz quais cartas atrapalham. Tirar todos os comandantes sempre é possível, e sem comandante não há limite.

## Como a carta entra no deck

Há quatro caminhos. Em todos, a trava vale para todos os grupos daquela cópia.

### Já está com você, livre no bulk

Se a casa da cópia é você e ela está livre no bulk, você coloca no seu deck na hora. Ela sai do monte disponível e nasce travada.

### Adicionando no seu deck

Você pesquisa a carta e adiciona ao deck. Se você já tem uma cópia livre dela na sua casa, no bulk deste grupo, o app trava essa cópia no deck. Se não tem, cadastra a cópia já no deck. A casa é você e ela nasce travada. Nos outros grupos seus ela aparece travada. A busca dentro do deck só sugere cartas que cabem na identidade de cor dele.

### No bulk, na casa de outra pessoa

Você escolhe o deck de destino e solicita. Não há aceite de quem está com a carta: quem pediu primeiro ficou com a vez. A cópia trava na hora, em todos os grupos, e entra na lista do que a outra pessoa leva no próximo encontro daquele grupo.

A carta só entra no seu deck quando você confirma que ela está na sua mão. Nessa confirmação a casa passa a ser você e a cópia continua travada. Até lá ela segue fisicamente com quem já estava, fora do seu deck.

Se a pessoa não achou o papel, ela combina com quem pediu. Quem pediu cancela. A cópia destrava. Quem está com ela remove do bulk se o papel não existe mais.

Quem pediu também cancela por qualquer outro motivo, enquanto a carta não entrou no deck. A cópia volta ao bulk, livre.

### No deck de outra pessoa, destravada

Carta travada no deck de alguém não pode ser pedida. Carta destravada pode.

Você solicita para um deck seu, no grupo em que está vendo a carta. A cópia trava na hora em todos os grupos, para ninguém pedir junto. A pessoa do deck aceita ou recusa no app.

Se recusar, a cópia volta ao deck dela, destravada. Se você cancelar, o mesmo. Se aceitar, a carta entra na lista do que ela leva quando vocês se encontrarem naquele grupo. Você confirma só com o papel na mão. Aí ela sai do deck antigo, entra no seu, a casa passa a ser você e ela fica travada.

## Trava

A trava é da cópia, não do grupo.

- Livre no bulk: qualquer membro de um grupo em que ela aparece pode pegar, se for a casa, ou solicitar, se for outra casa.
- Reservada por um pedido: ninguém mais solicita, em grupo nenhum. Só quem pediu cancela.
- No seu deck, travada: ninguém solicita. Você pode destravar.
- No seu deck, destravada: outros membros podem solicitar, por qualquer grupo em que a cópia aparece.

Colocar no deck, seja na hora ou depois da confirmação, deixa a cópia travada. Destravar é uma ação sua, com o deck já em mãos e sem pedido pendente.

## Listas do encontro

Cada lista é de um grupo.

- **Levar:** pedidos aceitos (ou pedidos de bulk, que não precisam de aceite) das cartas que estão na sua casa e ainda não foram confirmadas por quem pediu.
- **Receber:** pedidos que você abriu e que ainda dependem de aceite ou da carta na mão.

A confirmação é sempre de quem pediu, e só com a carta na mão. Quem leva não confirma a entrega no app.

## O que a dona da carta faz com ela

Sem pedido pendente, e com a cópia já no seu deck:

- move para outro deck seu, no mesmo grupo ou em outro grupo seu, na hora;
- devolve ao bulk, na casa dela, livre, na hora;
- trava ou destrava.

Com a cópia livre no bulk, a pessoa da casa remove o registro quando o papel saiu de circulação. Remover tira a cópia de todos os grupos.

## O que fica de fora

O app não cobra, não calcula frete e não organiza partida. Fora a escolha do comandante e a identidade de cor, não bloqueia deck ilegal: mostra o aviso e a pessoa decide. Não exige que quem está com a carta no bulk aceite o pedido.
