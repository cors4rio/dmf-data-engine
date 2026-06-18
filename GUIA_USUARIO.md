# Guia do Usuário — Central DMF

Este guia foi feito para você usar o sistema no dia a dia. Não precisa de conhecimento técnico — basta seguir as instruções na ordem.

---

## Sumário

1. [O que é a Central DMF](#1-o-que-é-a-central-dmf)
2. [Quem faz o quê](#2-quem-faz-o-quê)
3. [Abrindo o sistema pela primeira vez](#3-abrindo-o-sistema-pela-primeira-vez)
4. [Entendendo a tela principal](#4-entendendo-a-tela-principal)
5. [Como executar cada módulo](#5-como-executar-cada-módulo)
   - [Fiscal](#5a-fiscal)
   - [Contábil](#5b-contábil)
   - [DP / Folha (Pessoal)](#5c-dp--folha-pessoal)
6. [Dashboard — o que cada gráfico mostra](#6-dashboard--o-que-cada-gráfico-mostra)
7. [Relatório consolidado](#7-relatório-consolidado)
8. [Exceções (clientes que não entram)](#8-exceções-clientes-que-não-entram)
9. [Painel de administração (perfil admin)](#9-painel-de-administração-perfil-admin)
10. [Mensagens de erro e o que fazer](#10-mensagens-de-erro-e-o-que-fazer)
11. [Regras importantes para lembrar](#11-regras-importantes-para-lembrar)
12. [Quando pedir ajuda](#12-quando-pedir-ajuda)

---

## 1. O que é a Central DMF

A Central DMF é o aplicativo interno do escritório (roda no seu próprio computador, sem internet obrigatória). Ela centraliza as ferramentas de automação das áreas e conecta-se ao sistema Domínio.

A plataforma atende **5 setores** — **Administrativo**, **Fiscal**, **Contábil**, **Pessoal** (DP) e **Legalização** — e hospeda vários módulos. Entre eles:

- **Automação de Horas**: calcula as horas trabalhadas por cliente (Fiscal, Contábil e DP) e preenche a planilha mestre `CONTROLE DE HORAS DMF.xlsm`.
- **Relatório de Rendimentos** (Contábil), **Buscar XML** (Fiscal), **Sem Movimento NFS-e Salvador** (Fiscal) e **TFF Salvador** (Legalização).

Novos módulos são adicionados sem mudar o restante do sistema. Este guia foca no fluxo de **Automação de Horas**; os demais módulos têm suas próprias telas dentro do app.

Cada conta tem uma função (papel). O sistema controla quem pode executar o quê — ver a próxima seção.

---

## 2. Quem faz o quê

O acesso é definido pela **função (papel)** da sua conta, não pela pessoa:

| Função (papel) | Acessa | Executa |
|--------|--------|---------|
| **Admin** | Tudo | Tudo + administra usuários |
| **Contábil** | Tudo | Só o fluxo Contábil |
| **Fiscal** | Tudo | Só o fluxo Fiscal |
| **DP / Pessoal** | Tudo | Só o fluxo DP |
| **Legalização** | Tudo | Fluxo de Legalização (ex.: TFF Salvador) |

**Importante:**
- Cada pessoa tem sua própria conta com senha pessoal.
- Sua conta fica **vinculada ao seu computador** depois do primeiro acesso. Se você tentar entrar de outra máquina, o sistema bloqueia.
- Mesmo que você abra a aba de outro setor, os botões de execução ficam bloqueados com um aviso de que apenas o responsável daquele setor pode executar.

---

## 3. Abrindo o sistema pela primeira vez

### Passo a passo

1. Na pasta do projeto, **dê dois cliques no arquivo `run.bat`**.
2. Uma janela preta de terminal abre — **não feche essa janela**, ela é necessária para o sistema funcionar. A janela da Central DMF vai abrir junto.
3. Aparece a tela de login.
4. No primeiro acesso de cada pessoa:
   - **Usuário**: seu nome de usuário em minúsculas (exemplo: `seu.nome`)
   - **Senha**: o mesmo nome de usuário em minúsculas também (exemplo: `seu.nome`)
5. O sistema vai pedir para você **trocar a senha**. Escolha uma senha sua, confirme, e clique em "Definir senha e entrar".
6. Pronto — sua conta está vinculada a este computador. Nas próximas vezes, basta entrar com seu nome e a senha que você escolheu.

### Dica
- Se você esquecer a senha, peça a um **administrador** para resetar pelo Painel de Administração. Sua senha volta para o padrão (seu nome em minúsculas) e você troca de novo no próximo login.

---

## 4. Entendendo a tela principal

### Lado esquerdo (sidebar)

Lista de áreas do sistema:

- **Execução**
  - **Dashboard** — visão geral do mês com gráficos
  - **Relatório** — histórico do que foi feito
- **Parâmetros**
  - **Fiscal** — fluxo do setor Fiscal
  - **Contábil** — fluxo do setor Contábil
  - **DP / Folha** — fluxo do setor Pessoal (DP)
- **Configuração**
  - **Conexão BD** — credenciais do sistema Domínio
  - **Exceções** — listas de clientes que não entram
  - **Governança** — regras de qualidade
- **Admin** (só aparece para contas com perfil admin) — gestão de usuários

### Parte superior

- À esquerda: nome da aba atual.
- À direita: **Competência** — qual mês estamos olhando ou processando. Por padrão, mostra o mês anterior ao atual.

### Parte inferior da sidebar

- Nome de quem está logado + função (ex: "usuário · Fiscal")
- Estado da conexão com o Domínio (verde = conectado, vermelho = falha)
- Qual planilha master está sendo usada
- Link "sair" para fazer logout

---

## 5. Como executar cada módulo

### Regra de competência

| Módulo | Competência aplicada |
|--------|---------------------|
| **DP** | Mês anterior ao mês atual |
| **Contábil** | Mês anterior ao mês atual |
| **Fiscal** | Dois meses antes do mês atual |

Exemplo: estamos em **maio**.
- DP e Contábil vão processar dados de **abril**.
- Fiscal vai processar dados de **março**.

O dropdown da competência no topo já vem com o mês correto pré-selecionado. Se precisar refazer um mês anterior, basta escolher no dropdown.

---

### 5a. Fiscal

**O que faz:** consulta o Domínio, soma o tempo trabalhado em cada cliente no mês, aplica um acréscimo de 80% (ajustável), e grava na coluna O da planilha master.

**Passo a passo:**

1. Confira no topo o **mês de competência** (deve ser dois meses atrás do mês atual).
2. Clique na aba **Fiscal** na sidebar.
3. No card azul superior, confira a janela aplicada — exemplo: "Dropdown da topbar: 04/2026 → Janela aplicada ao Fiscal: 03/2026".
4. (Opcional) No card "Acréscimo aplicado ao tempo bruto", ajuste o percentual se necessário, e clique em **Salvar**.
5. No card "Executar Fiscal", clique em **Executar Fiscal agora**.
6. Acompanhe a barra de progresso no canto superior direito.
7. Quando concluir, aparece uma mensagem verde "Fiscal executado com sucesso".

**Antes de executar, garanta que:**
- O computador está conectado à rede do escritório (precisa acessar o Domínio).
- A planilha `CONTROLE DE HORAS DMF.xlsm` **não está aberta no Excel** — feche se estiver.

---

### 5b. Contábil

**O que faz:** o módulo Contábil é diferente dos outros porque tem uma **etapa manual** no meio. São 3 passos.

#### Passo 1 — Anexar a planilha HORAS CONTABEIS

1. Clique na aba **Contábil**.
2. No primeiro card, clique em **Selecionar arquivo**.
3. Aponte para a planilha `HORAS CONTABEIS.xlsx` da pasta do OneDrive (o sistema lembra do caminho da última vez).
4. A badge muda para "anexada".

#### Passo 2 — Preencher dados na planilha contábil

1. Confira no Passo 2 a aba alvo (exemplo: `04.2026`).
2. Clique em **Processar lançamentos contábeis**.
3. O sistema consulta o Domínio e escreve **apenas 3 colunas** da `HORAS CONTABEIS.xlsx`:
   - **F**: quantidade de lançamentos contábeis
   - **I**: tem folha? (SIM / NAO)
   - **O**: total de faturamento do mês
4. Demais colunas são **preservadas** — o sistema não mexe em mais nada.
5. Quando concluir, aparece resumo: quantas linhas foram processadas, quantas tiveram match perfeito (3/3), match parcial (2/3) e quantas foram rejeitadas (faltam dados).

#### Etapa manual obrigatória (entre o Passo 2 e o Passo 3)

> **Atenção:** depois do Passo 2, abra a `HORAS CONTABEIS.xlsx` no Excel e preencha **manualmente a coluna R (HORAS VALIDADAS)** de cada cliente. **Salve e feche** a planilha antes de seguir.

#### Passo 3 — Lançar na master

1. Quando os valores manuais estiverem na coluna R, volte à Central DMF.
2. Aba **Contábil**, no Passo 3, clique em **Lançar na master**.
3. O sistema lê a coluna R, confere cliente por cliente (código + CNPJ) e grava a coluna P da `CONTROLE DE HORAS DMF.xlsm`.
4. Aparece resumo: quantas linhas foram gravadas, quantas não bateram com nenhum cliente da master.

---

### 5c. DP / Folha (Pessoal)

**O que faz:** usa a planilha de Controle de Empregados (entrada manual do DP) mais os dados do Domínio (funcionários, estagiários e sócios ativos) para calcular as horas de DP por empresa, e grava na coluna Q da master.

**Passo a passo (2 etapas):**

#### Passo 1 — Importar a planilha de Controle de Empregados

1. Clique na aba **DP / Folha**.
2. No Passo 1, clique em **Selecionar planilha**.
3. Aponte para a planilha de Controle de Empregados da competência (o arquivo `.xls` entregue pelo DP). O nome pode ter variações (exemplo: `Controle de Empregados 042026.xls`, `05.2026.xls`). O sistema aceita qualquer um, mas avisa se o nome não tem o mês da competência (para evitar erro de competência).
4. O sistema lê a planilha e mostra: total de empresas mapeadas, quantas têm funcionários ativos, quantas estão sem ativos.
5. Badge muda para "mapeada".

#### Passo 2 — Lançar na master

1. Clique em **Lançar na master**.
2. O sistema cruza a planilha de Controle de Empregados com o Domínio (se conectado), aplica a fórmula em cascata, e grava a coluna Q da master.
3. Aparece a mensagem "DP lançado na master com sucesso".

**Fórmula em cascata:**
- Empresa **sem nenhum colaborador ativo**: 5 minutos.
- Empresa **com apenas sócios**: trata como 1 colaborador.
- Empresa **com funcionários/estagiários**: total de ativos × 0,33h + 1,5h fixa.
- Empresa em **consultoria** (lista de exceções): 1h30.
- Empresa em **DP NÃO** (lista de exceções): grava o texto "DP NÃO" na célula.

Os valores das fórmulas podem ser ajustados nos parâmetros da aba DP.

---

## 6. Dashboard — o que cada gráfico mostra

O Dashboard puxa os dados direto da planilha master, da aba do mês que você selecionou no topo.

### Métricas (topo, 5 caixas)

1. **Clientes na planilha** — total de linhas com código preenchido.
2. **Com match ≥ 2/3** — clientes que têm pelo menos 2 dos 3 dados identificadores (código, nome, CNPJ).
3. **Pendências** — clientes com 0 ou 1 dado preenchido (atenção). **Clique** para ver a lista detalhada.
4. **CNPJ duplicados** — quando o mesmo CNPJ aparece em mais de uma linha. **Clique** para ver a lista.
5. **Códigos duplicados** — quando o mesmo código aparece em mais de uma linha. **Clique** para ver a lista.

### Gráficos

- **Horas totais por setor (donut)** — quanto de tempo total cada setor (Fiscal, Contábil, DP) consumiu no mês.
- **Distribuição por faixa de horas (barras)** — quantos clientes têm 0h, 0-2h, 2-5h, 5-10h, 10-20h, e mais de 20h.
- **Top 10 clientes** — os 10 que mais consumiram tempo, com a divisão por setor em cores diferentes.
- **Preenchimento por setor** — quantos clientes têm lançamento maior que zero em cada coluna.
- **Maiores variações mês a mês** — clientes que aumentaram ou diminuíram mais de horas comparado ao mês anterior. Útil para detectar mudanças bruscas.

### Atualização

O Dashboard se atualiza automaticamente:
- Quando você abre o sistema
- Quando troca a competência no topo
- Quando termina uma execução
- Quando você clica em **Atualizar** no topo da página

---

## 7. Relatório consolidado

Aba **Relatório** mostra três blocos:

1. **Resumo da competência** — estado de cada módulo (Fiscal, Contábil, DP) para o mês selecionado: se foi processado, quando, com quantos clientes.
2. **Relatórios gerados pelo motor** — lista de arquivos `.md` que o sistema gerou automaticamente (auditoria do Contábil, etc). Clique em qualquer um para ver o conteúdo dentro do app.
3. **Últimos erros e avisos** — histórico de problemas. Útil para investigar quando algo deu errado. Botão "Limpar" zera o histórico após você revisar.
4. **Log técnico** — últimas 30 linhas do diário do sistema. Para conferência rápida.

---

## 8. Exceções (clientes que não entram)

Algumas empresas **não devem receber lançamento** em determinados setores. Para isso, cada área tem um arquivo de texto:

- `DP_NAO.txt` — clientes que não entram no DP
- `CONTABIL_NAO.txt` — clientes que não entram no Contábil
- `FISCAL_NAO.txt` — clientes que não entram no Fiscal

**Como atualizar:**

1. Clique na aba **Exceções** na sidebar.
2. Para o setor que quer atualizar, clique em **Importar TXT**.
3. Aponte para o arquivo `.txt` atualizado (com os códigos de cliente, um por linha).
4. O sistema **sobrescreve** o arquivo antigo do setor. A partir desse momento, a lista nova passa a valer.
5. Os arquivos ficam guardados na pasta do projeto — você não precisa importar de novo a cada uso. Só atualize quando incluir ou remover algum cliente.

**Como o sistema usa essas listas:**
- Toda vez que um módulo (Fiscal / Contábil / DP) for executado, ele **lê o arquivo correspondente** e pula esses clientes na hora de gravar na master.

---

## 9. Painel de administração (perfil admin)

A aba **Admin** aparece apenas para contas com perfil **admin**. Mostra a tabela de todos os usuários com:

- **Nome e função**
- **Máquina amarrada** — em qual computador a conta foi usada pela primeira vez
- **Último login**
- **Estado da senha** — "padrão (pendente)" se a pessoa ainda não trocou, "definida" se já trocou

**Ações disponíveis por usuário:**

- **Liberar máquina** — quando alguém precisa trocar de computador. A próxima entrada da pessoa será permitida de qualquer máquina e a nova vinculação acontecerá automaticamente.
- **Resetar senha** — volta a senha da pessoa para o padrão (= o próprio nome). No próximo login, ela será obrigada a trocar.

---

## 10. Mensagens de erro e o que fazer

### "Planilha master está aberta no Excel"

**Causa:** alguém (talvez você mesmo) tem a `CONTROLE DE HORAS DMF.xlsm` aberta.
**Solução:** feche o arquivo no Excel e tente de novo.

---

### "Esta conta está vinculada a outra máquina"

**Causa:** sua conta foi usada antes em outro computador. O sistema bloqueia acesso de máquinas diferentes para evitar que alguém entre na sua conta.
**Solução:** peça a um **administrador** para entrar no painel **Admin** e clicar em **Liberar máquina** para o seu usuário. Depois disso, sua próxima entrada vai amarrar a conta a este computador.

---

### "Usuário ou senha incorretos"

**Causa:** ou o nome está errado, ou a senha está errada. O sistema não diz qual dos dois, de propósito.
**Solução:**
1. Confira se digitou o nome de usuário em minúsculas (ex.: `usuario`, não `Usuario`).
2. Confira a senha (cuidado com Caps Lock).
3. Se esqueceu mesmo, peça a um administrador para resetar.

---

### "Falha na conexão ODBC" / "DSN não encontrado"

**Causa:** o sistema não consegue conversar com o Domínio.
**Solução:**
1. Confira se o computador está na **rede do escritório** (algumas conexões fora do escritório não acessam o Domínio).
2. Abra a aba **Conexão BD** e clique em **Diagnóstico** no canto superior. O diagnóstico mostra detalhes técnicos para o suporte resolver.
3. Em caso de dúvida persistente, chame um administrador.

---

### "Arquivo está como 'somente online' no OneDrive"

**Causa:** a planilha está marcada no OneDrive como "liberar espaço" (ícone de nuvem ao lado do nome), ou seja, não está baixada no seu computador.
**Solução:**
1. Abra o Explorador de Arquivos.
2. Encontre a planilha (`CONTROLE DE HORAS DMF.xlsm` ou `HORAS CONTABEIS.xlsx`).
3. Clique com o **botão direito** sobre ela.
4. Escolha **"Sempre manter neste dispositivo"**.
5. Aguarde alguns segundos para o OneDrive baixar o arquivo (o ícone muda para um círculo verde).
6. Volte à Central DMF e tente de novo.

---

### "Apenas X pode executar este módulo"

**Causa:** você está logado com uma conta que não tem permissão para executar esse setor (por exemplo: uma conta do Contábil tentando executar o Fiscal).
**Solução:**
- Se for executar uma função alheia ao seu setor, peça à pessoa responsável fazer.
- Em situação de urgência (a pessoa não está disponível), peça a um administrador para entrar com a conta dela (que tem acesso a tudo).

---

### Janela preta (terminal) fechou sozinha

**Causa:** algum erro grave no boot do programa.
**Solução:**
1. Tente abrir o `run.bat` de novo.
2. Se fechar de novo, abra o `run.bat` clicando com botão direito → "Editar" para ver, e troque a última linha por:
   ```
   py -3-32 dmf_engine\main.py
   pause
   ```
   Salve, abra de novo, e copie a mensagem que aparece para enviar ao suporte.

---

### Gráficos do Dashboard estão zerados / vazios

**Causas possíveis:**
1. A aba do mês selecionado não tem dados ainda. Confira no dropdown da competência se você está olhando o mês certo.
2. A planilha master não foi definida. Clique em **Definir master** no Dashboard e aponte para `CONTROLE DE HORAS DMF.xlsm`.
3. A planilha master está em local diferente do esperado. Mesma solução acima.

---

### "Aba 'MM.AAAA' não encontrada"

**Causa:** a `HORAS CONTABEIS.xlsx` (ou a master) não tem aba para o mês que você está tentando processar.
**Solução:** abra a planilha no Excel, **crie a aba** com o nome no formato `MM.AAAA` (exemplo: `04.2026`) usando como base a aba do mês anterior, salve, feche, e tente de novo.

---

### O botão "Lançar na master" do Contábil está bloqueado

**Causa:** você ainda não executou o Passo 2 nesta competência.
**Solução:** execute o Passo 2 primeiro (Processar lançamentos contábeis). Só depois o sistema libera o Passo 3.

---

### O botão "Lançar na master" do DP está bloqueado

**Causa:** você ainda não importou a planilha de Controle de Empregados nesta competência.
**Solução:** execute o Passo 1 primeiro (Selecionar planilha).

---

## 11. Regras importantes para lembrar

1. **Não compartilhe sua senha.** Cada um tem a sua. Se compartilhar e alguém fizer alguma coisa indevida no seu nome, o sistema vai registrar como se você tivesse feito.
2. **Sempre feche a planilha master no Excel** antes de executar qualquer módulo na Central DMF.
3. **A coluna R da `HORAS CONTABEIS.xlsx` é manual.** O responsável do Contábil preenche, salva e fecha. Só depois disso o sistema lança na master.
4. **Não mexa em arquivos da pasta `config\nao_faz_setor\`** diretamente. Use a aba Exceções no sistema.
5. **Não rode o módulo de outro setor** (mesmo que o botão estivesse desbloqueado), porque os cálculos dependem de regras específicas que só quem é da área conhece.
6. **A competência muda automaticamente** todo mês. Se for o dia 1 de junho, o dropdown já vai mostrar maio (e o Fiscal vai mirar em abril). Não precisa configurar nada.
7. **Trabalhos fora do horário podem dar problemas** se outras pessoas estiverem acessando os arquivos do OneDrive ao mesmo tempo. Em horário comercial é o ideal.
8. **A janela preta do terminal não deve ser fechada.** Ela é parte do sistema. Quando você quiser sair, clique no "X" da janela da Central DMF (não da janela preta).

---

## 12. Quando pedir ajuda

Procure um **administrador** quando:
- Esqueceu a senha
- Trocou de computador e precisa liberar a vinculação
- Apareceu uma mensagem de erro que não está neste guia
- O sistema fechou sozinho e não abre mais

Antes de pedir ajuda, ajude a quem vai te atender:
1. Anote a mensagem exata que apareceu na tela.
2. Tire um print da tela.
3. Anote em que passo você estava (exemplo: "Cliquei em Lançar na master do Contábil e apareceu o erro X").
4. Se aparecer "Veja os Últimos erros e avisos", entre na aba **Relatório**, role até esse card, e copie as últimas 2 ou 3 linhas em vermelho ou laranja.

Isso ajuda muito a resolver mais rápido.

---

**Última atualização:** Maio/2026 — versão alinhada com a entrega atual do sistema.
