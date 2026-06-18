# Central DMF — Instalação e Primeiro Uso

Este guia ensina, do zero, como instalar a Central DMF no seu computador e entrar pela primeira vez. Não é preciso saber nada de informática além de ligar o computador e usar o mouse. Faça **um passo de cada vez, na ordem em que aparecem**. Se travar em algum ponto, pare e chame a TI — não pule etapas.

---

## Parte 1 — O que é a Central DMF

A Central DMF é o programa interno do escritório. Ele fica instalado no seu próprio computador (não é um site, não abre no navegador) e reúne as ferramentas de trabalho das áreas: controle de horas, relatórios, busca de notas fiscais e outras automações.

Cada pessoa entra com a sua própria conta (usuário e senha). O que cada um pode **fazer** dentro do programa depende da sua função no escritório.

---

## Parte 2 — Antes de começar, confira

Antes de instalar, confirme estes três itens. Se faltar algum, chame a TI antes de continuar.

1. **Seu computador é Windows 10 ou Windows 11.** Praticamente todos os computadores do escritório são. Em caso de dúvida, não precisa fazer nada — siga em frente.
2. **Você está no escritório, conectado à rede da empresa.** A instalação usa uma pasta que fica na rede interna (o "disco Z"). De casa ou fora da rede, essa pasta não aparece.
3. **Você consegue ver o "disco Z" no computador.** Como conferir isso está logo no Passo 1 abaixo.

Você **não** precisa instalar mais nada (nem Python, nem navegador especial, nem nada). Tudo o que o programa precisa já vem junto.

---

## Parte 3 — Passo a passo da instalação

### Passo 1 — Abrir o Explorador de Arquivos

O Explorador de Arquivos é o programa do Windows que mostra as pastas e os arquivos do computador. O ícone dele é uma **pastinha amarela**, que normalmente fica na barra de tarefas (a barra na parte de baixo da tela).

- Clique uma vez nessa pastinha amarela na barra de baixo.
- Se não encontrar o ícone, segure a tecla com o símbolo do Windows (fica perto da barra de espaço, embaixo à esquerda) e, sem soltar, aperte a letra **E**. Solte as duas. Uma janela com pastas vai abrir.

### Passo 2 — Ir até a pasta dos programas na rede

Agora você vai abrir a pasta onde fica o instalador. O caminho completo é:

```
Z:\ICARO CONCEICAO DOS SANTOS\PROGRAMAS
```

A forma mais simples e sem erro de chegar lá:

1. Na janela que abriu (o Explorador de Arquivos), localize a **barra de endereço**. É a faixa branca e comprida no alto da janela, onde aparece o nome do local atual.
2. Clique uma vez dentro dessa faixa branca. O conteúdo dela fica selecionado (azul).
3. Digite (ou copie e cole) exatamente este caminho:
   ```
   Z:\ICARO CONCEICAO DOS SANTOS\PROGRAMAS
   ```
4. Aperte a tecla **Enter**.

A janela vai mostrar o conteúdo da pasta **PROGRAMAS**. Dentro dela existe a pasta da Central DMF (o nome da pasta pode ser **DMF Engine** ou similar — a TI informa qual é, se houver mais de uma).

> **Não está achando o disco Z?** No lado esquerdo da janela existe a lista "Este Computador". Se nem o "Z:" nem a pasta aparecerem, você provavelmente não está conectado à rede do escritório. Pare aqui e chame a TI.

### Passo 3 — Entrar na pasta da Central DMF

- Dentro da pasta **PROGRAMAS**, dê **dois cliques rápidos** sobre a pasta da Central DMF para abri-la.
- Dentro dela você vai ver vários arquivos. O que interessa para a instalação se chama:
  ```
  Instalar DMF Engine.bat
  ```
- Esse arquivo costuma ter um ícone com duas **engrenagens** ou uma **janelinha**. O nome é o que importa: **Instalar DMF Engine**.

> O computador pode estar configurado para **não mostrar** o final `.bat` no nome. Tudo bem — procure pelo arquivo chamado **Instalar DMF Engine**, com ou sem o `.bat` no final.

### Passo 4 — Rodar o instalador

1. Dê **dois cliques rápidos** sobre o arquivo **Instalar DMF Engine**.
2. Vai abrir uma **janela preta** com letras (parece "tela de hacker", mas é normal — é só o instalador trabalhando). **Não feche essa janela** e não clique nela enquanto ela estiver trabalhando.
3. A janela mostra o progresso da cópia dos arquivos, com uma barrinha enchendo de `#`. Isso leva de alguns segundos a um ou dois minutos. **Aguarde sem mexer.**
4. Quando terminar, aparece a mensagem:
   ```
   Instalação concluída com sucesso!
   ```
5. Em seguida, a janela pergunta:
   ```
   Deseja abrir a Central DMF agora? [S/N]:
   ```
   Digite a letra **S** (de "sim") no teclado e aperte **Enter**. O programa abre na hora.

Pronto — a instalação terminou. O instalador copiou o programa para dentro do **seu** computador (não fica mais dependendo do disco Z para funcionar) e criou um atalho na sua Área de Trabalho para você abrir nas próximas vezes.

### Se aparecer uma tela azul do Windows ("O Windows protegeu o computador")

Às vezes, na primeira vez, o Windows mostra uma tela azul dizendo **"O Windows protegeu o computador"**. Isso acontece com programas internos da empresa e **não é vírus**. Para continuar:

1. Clique no texto **"Mais informações"** (fica no meio da tela azul).
2. Aparece um botão **"Executar assim mesmo"**. Clique nele.
3. A instalação continua normalmente.

### Se aparecer "O DMF Engine está aberto" / "A Central DMF está aberta"

Isso quer dizer que o programa já está aberto no seu computador. Feche-o primeiro (clique no **X** no canto superior direito da janela do programa) e rode o instalador de novo. O instalador não consegue atualizar com o programa aberto.

---

## Parte 4 — Abrir o programa nas próximas vezes

Depois de instalado, você **não** precisa voltar no disco Z. Para abrir a Central DMF no dia a dia:

1. Vá até a **Área de Trabalho** (a tela inicial do Windows, com o papel de parede e os ícones). Para chegar nela rapidamente, segure a tecla do Windows e aperte a letra **D**.
2. Procure o ícone chamado **DMF Engine**.
3. Dê **dois cliques** nesse ícone.
4. A janela da Central DMF abre e mostra a tela de **login** (entrada com usuário e senha).

---

## Parte 5 — Primeiro acesso (login inicial)

No seu **primeiro acesso**, o usuário e a senha são iguais: ambos são o **seu nome de usuário, tudo em letra minúscula** (sem espaços, sem letra maiúscula). A TI informa qual é o seu nome de usuário.

Por exemplo, se o seu usuário for `seu.nome`, então:

| Campo na tela | O que digitar |
|---------------|---------------|
| **Usuário** | `seu.nome` |
| **Senha** | `seu.nome` (o mesmo, na primeira vez) |

Passo a passo:

1. No campo **Usuário**, digite o seu nome de usuário em minúsculas.
2. No campo **Senha**, digite o mesmo nome de usuário (na primeira vez a senha é igual ao usuário).
3. Clique no botão de entrar.
4. O sistema vai **obrigar você a criar uma senha nova** (isso é por segurança — ninguém deve continuar com a senha padrão).
5. Escolha uma senha só sua. Ela precisa ter **pelo menos 4 caracteres** e **não pode ser igual ao seu nome de usuário**.
6. Digite a senha nova, confirme onde for pedido e clique em **"Definir senha e entrar"**.
7. Pronto. A partir de agora, você entra com o seu nome de usuário e **essa senha nova** que acabou de criar. Guarde-a — ela é pessoal e não deve ser compartilhada.

> **Por que minha conta fica "presa" neste computador?**
> Depois do primeiro acesso, a sua conta fica vinculada **a este computador específico**. Se você tentar entrar pela sua conta em outra máquina, o sistema vai bloquear. Isso é proposital e serve para a sua segurança: mesmo que alguém descubra a sua senha, não consegue entrar de outro computador. Se você **trocar de computador** de verdade, peça a um administrador para "Liberar máquina" (explicado na Parte 7).

---

## Parte 6 — Conhecendo a tela principal

Quando você entra, a tela tem três regiões:

- **Menu da esquerda (a coluna vertical):** é por onde você navega entre as partes do sistema — o painel geral (Dashboard), os relatórios e os módulos de cada setor.
- **Faixa de cima:** mostra o nome da tela em que você está e o **mês de competência** (qual mês está sendo consultado ou processado no momento).
- **Rodapé do menu (parte de baixo da coluna esquerda):** mostra o seu nome de usuário e a sua função, se a conexão com o sistema Domínio está ativa (verde quer dizer conectado; vermelho quer dizer sem conexão), qual planilha está em uso e o link **sair** para encerrar a sessão.

Você pode abrir e olhar qualquer parte do sistema. Porém, os botões de **executar** (os que de fato processam e gravam dados) só ficam ativos nas áreas da **sua** função. Nas áreas de outros setores, esses botões ficam bloqueados, com um aviso de que apenas o responsável daquele setor pode executar.

---

## Parte 7 — Quando algo não sai como esperado

Procure abaixo a situação parecida com a sua e siga a orientação. Se nada resolver, chame a TI e descreva o que aconteceu.

**"Esqueci minha senha"**
Peça a um administrador da Central DMF para resetar a sua senha. Ela volta a ser igual ao seu nome de usuário (em minúsculas), e no próximo acesso o sistema vai pedir para você criar uma senha nova de novo.

**Apareceu "Esta conta está vinculada a outra máquina"**
Isso acontece quando você tenta entrar de um computador diferente daquele do seu primeiro acesso (por exemplo, trocou de máquina). Peça a um administrador para usar a opção **"Liberar máquina"** da sua conta. Depois disso, faça o login normalmente neste computador — a conta passa a ficar vinculada a ele.

**A conexão com o Domínio aparece vermelha**
Confira se o seu computador está conectado à rede do escritório (a mesma rede que dá acesso ao disco Z). Se estiver na rede e mesmo assim continuar vermelho, avise a TI.

**O programa não abre, ou abre e fecha sozinho**
Tente abrir de novo pelo atalho **DMF Engine** na Área de Trabalho. Se continuar fechando sozinho, avise a TI para verificar a instalação.

**Não encontro o atalho na Área de Trabalho**
Refaça a instalação (Partes 3) a partir do disco Z. O instalador recria o atalho toda vez que roda.

---

## Parte 8 — Atualizações (quando sair uma versão nova)

De tempos em tempos, a TI disponibiliza uma versão nova do programa na mesma pasta do disco Z. Para atualizar:

1. **Feche a Central DMF**, se ela estiver aberta (clique no **X** no canto superior direito).
2. Vá novamente até `Z:\ICARO CONCEICAO DOS SANTOS\PROGRAMAS`, entre na pasta da Central DMF e rode o **Instalar DMF Engine** outra vez (igual à Parte 3).
3. Pronto. A sua senha e as suas configurações são **preservadas** — a atualização só troca o programa por dentro, sem apagar nada do que é seu.

---

## Parte 9 — Quem procurar

- **Dúvidas de uso, senha ou liberação de máquina:** um administrador da Central DMF.
- **Problemas de instalação, de rede, do disco Z ou de conexão:** a TI.

Quando for pedir ajuda, ajude quem vai te atender: anote (ou tire uma foto da tela com) a **mensagem exata** que apareceu e diga **em que passo** você estava.
