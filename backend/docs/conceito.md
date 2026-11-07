# bulkados

App para um grupo de amigos montar decks de Commander a partir de um bulk compartilhado de cartas baratas. Este documento descreve o produto inteiro. O repositório atual implementa só o backend; a interface consome as regras daqui.

O formato de origem é o Commander 10: a soma das cartas que não são comandante fica em até R$ 10, e a soma dos comandantes fica em até R$ 5. O app também aceita Commander 100, Commander 200, Commander 500 e competitivo. O teto de preço desses outros formatos ainda não está definido.

## Pessoas

Cada pessoa tem uma conta identificada pelo e-mail. O e-mail é o identificador usado no cadastro, no login e no convite.

O login é e-mail e senha. A recuperação e a troca de senha usam esse e-mail. A autenticação fica no Supabase; o e-mail e o restante dos dados do app ficam no backend.

No grupo, as pessoas se veem pelo e-mail.

## Grupos

Um grupo é um bulk com nome. Qualquer membro cria um grupo e convida pelo e-mail. O convite aparece na tela inicial de quem foi convidado, com o nome do grupo e o e-mail de quem convidou. Aceitar entra no grupo. Recusar apaga o convite. Enquanto o convite está pendente, esse grupo não entra na lista de grupos da pessoa e ela não vê as cartas nem os membros daquele grupo. Uma pessoa participa de vários grupos ao mesmo tempo.

Dentro do grupo, todo membro pode cadastrar cartas, montar decks e solicitar cartas. O deck é de uma pessoa e não pertence ao grupo: ele pode reunir cartas de vários bulks. Outra pessoa não edita o deck dela.

Quem criou o grupo dá o nome e pode renomear. Qualquer membro convida. O deck não é apagado quando a pessoa sai do grupo: ele continua sendo dela, com as cartas que estiverem nele. Sair do grupo só desfaz o vínculo das cartas da própria casa com aquele bulk e cancela os pedidos abertos daquela pessoa naquele grupo.

## A carta física

O que circula no app é uma cópia física, não uma quantidade genérica. Duas cartas com o mesmo nome são dois registros quando são dois papéis. Cada uma tem a própria casa, o próprio deck e a própria trava.

A casa é a pessoa com quem o papel está. No cadastro, a casa padrão é quem está cadastrando. Pode ser outro membro. Land básica também é cópia física; o preço dela é sempre zero.

A mesma cópia pode estar em vários grupos ao mesmo tempo. Isso acontece quando a pessoa da casa participa de mais de um grupo e a cópia foi vinculada a esses grupos. Quem reserva a cópia trava ela em todos os grupos até o pedido acabar. Colocar no deck não trava. Existe um deck por vez para aquela cópia. Nos outros grupos ela continua visível, e ninguém solicita se estiver travada.

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
- a identidade de cor do deck é a união das cores dos comandantes. Com comandante, o app recusa a carta cuja identidade sai dela: ao adicionar, selecionar do bulk, mover de outro deck ou solicitar. Sem comandante, não há limite. Carta incolor cabe em qualquer deck.

A identidade aparece com os ícones das cores e o nome da combinação (Azorius, Bant, Mono-verde, Incolor, Cinco cores). Incolor é só do deck cujo comandante não tem cor, como Karn ou Ullamog. Marcar comandante também respeita a identidade: se o deck tem carta fora da identidade que os comandantes passariam a ter, o app recusa e diz quais cartas atrapalham. Tirar todos os comandantes sempre é possível, e sem comandante não há limite.

## Como a carta entra no deck

Há quatro caminhos. A trava não acompanha a entrada no deck. Ela só existe quando o dono trava na tela do deck, ou enquanto um pedido deixa a cópia reservada. Reservada, a trava vale para todos os grupos daquela cópia.

### Já está com você, livre no bulk

Se a casa da cópia é você e ela está livre no bulk, Selecionar abre na hora a escolha: criar um deck novo ou adicionar a um que já existe. No deck existente dá para marcar a carta como comandante, se a cadeira ainda couber (um comandante, ou uma dupla válida de Partner e afins). Ela sai do monte disponível e fica destravada.

### Adicionando no seu deck

Você pesquisa a carta e escolhe: livre no bulk, nos grupos marcados, ou direto num deck seu. Se você já tem uma cópia livre dela na sua casa, no bulk deste grupo, o app coloca essa cópia no deck, sem travar. Se não tem, cadastra a cópia já no deck, destravada, na sua casa. A busca dentro do deck só sugere cartas que cabem na identidade de cor dele.

### No bulk, na casa de outra pessoa

Você escolhe o deck de destino e seleciona. Como a carta está em outra casa, isso vira uma solicitação, que fica pendente até quem está com a carta aceitar. A cópia fica reservada na hora, em todos os grupos, para ninguém pedir junto; para os outros, o botão passa a Indisponível.

Aceito o pedido, a carta entra na lista do que a outra pessoa leva no próximo encontro daquele grupo. Ela só entra no seu deck quando os dois confirmam no encontro, cada um pelo seu lado: quem está com o papel confirma a entrega e quem pediu confirma o recebimento. Aí a casa passa a ser você, ela entra no deck e destrava. Até lá ela segue fisicamente com quem já estava, fora do seu deck.

Se a pessoa não achou o papel, ela recusa. Quem pediu também cancela por qualquer outro motivo, enquanto a carta não entrou no deck. A cópia volta ao bulk, livre. Quem está com ela remove o registro se o papel não existe mais.

### No deck de outra pessoa, destravada

Carta travada no deck de alguém não pode ser pedida. Carta destravada pode.

Você solicita para um deck seu, em qualquer bulk. A cópia fica reservada na hora em todos os grupos, para ninguém pedir junto. O dono do deck de origem aceita ou recusa no app, na tela do deck.

Se recusar, a cópia volta ao deck dela, destravada. Se você cancelar, o mesmo. Se aceitar, a carta entra na lista do que ela leva quando vocês se encontrarem naquele grupo. A entrega se fecha quando os dois confirmam no encontro. Aí ela sai do deck antigo, entra no seu, a casa passa a ser você e ela fica destravada.

## Trava

A trava é da cópia, não do grupo. Só se trava e destrava na tela do deck em que a carta está. O bulk não oferece essa ação.

- Livre no bulk: Selecionar. Se é a sua casa, entra direto no deck; se é outra, vira uma solicitação.
- Reservada por um pedido: ninguém mais solicita, em grupo nenhum. O botão fica Indisponível. Só quem pediu cancela.
- No seu deck, travada: ninguém solicita. Você pode destravar na tela do deck.
- No seu deck, destravada: outros membros podem solicitar, por qualquer grupo em que a cópia aparece.

Selecionar, cadastrar direto no deck ou confirmar o recebimento não trava. Travar é uma ação sua, com o deck aberto e sem pedido pendente.

No bulk, o estado aparece por texto e cor: Livre, Reservada, Indisponível e Travada. O filtro de estado começa em Livre e esconde o resto; Todas mostra tudo; Reservadas mostra as cartas que já estão num deck, inclusive as travadas. Carta travada leva um cadeado e o botão fica Indisponível, mas o cartão continua abrindo o detalhe. A busca é por nome, e ainda dá para filtrar por cor e por custo de mana.

## Listas do encontro

Cada lista é de um grupo.

- **Levar:** pedidos em que a carta está na sua casa ou no seu deck. Inclui os pedidos que ainda esperam a sua decisão de aceitar ou recusar e os que você já aceitou e precisa levar.
- **Receber:** pedidos que você abriu e que ainda esperam aceite ou a confirmação da entrega.

A entrega só se completa quando os dois lados confirmam no encontro: quem leva confirma a entrega e quem pediu confirma o recebimento. Enquanto só um confirmou, o pedido continua aberto.

## O que a dona da carta faz com ela

Sem pedido pendente, e com a cópia já no seu deck:

- move para outro deck seu, em qualquer bulk, na hora;
- devolve ao bulk, na casa dela, livre, na hora;
- trava ou destrava, só na tela desse deck.

No bulk, o menu da carta tira ou inclui um grupo, ou remove o registro de todos quando o papel saiu de circulação. Remover o registro só com a cópia livre. Tirar o último grupo não vale: isso é remover o registro. Tirar o vínculo de uma carta que está num deck também não vale, até devolver ao bulk.

## O que fica de fora

O app não cobra, não calcula frete e não organiza partida. Fora a escolha do comandante, a identidade de cor e o aceite de quem está com a carta, não bloqueia deck ilegal: mostra o aviso e a pessoa decide.
