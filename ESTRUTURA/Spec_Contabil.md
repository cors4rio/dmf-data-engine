# Spec ContÃ¡bil â€” Planilha HORAS CONTABEIS

> **Data:** 2026-04-13 | **Autor:** DMF AutomaÃ§Ã£o | **Ãšltima EdiÃ§Ã£o:** 2026-04-13
> **Planilha Alvo:** `HORAS CONTABEIS_.xlsx`
> **MÃªs Atual de ExecuÃ§Ã£o:** `03.2026`

---

## 1. ARQUITETURA DA PLANILHA

### 1.1 Estrutura das Abas
Cada aba segue o padrÃ£o `MM.AAAA` (ex: `03.2026`). Existe tambÃ©m uma aba `EXEMPLO` com modelo e aba `MÃ‰DIA 2025` para consolidaÃ§Ã£o.

### 1.2 Mapeamento de Colunas (17 Colunas)

| Coluna | Header | Tipo | Fonte | ObservaÃ§Ã£o |
|--------|--------|------|-------|------------|
| **A** | CÃ³d DomÃ­nio | INT | Planilha (fixo) | CÃ³digo `codi_emp` do Sistema DomÃ­nio |
| **B** | GRUPO | TEXT | Planilha (fixo) | Grupo empresarial (opcional) |
| **C** | CNPJ / CPF | TEXT | Planilha (fixo) | CNPJ (somente nÃºmeros) ou CPF |
| **D** | EMPRESA CARTÃƒO CNPJ | TEXT | Planilha (fixo) | Nome/RazÃ£o Social da empresa (pode conter CNPJ no prefixo) |
| **E** | REGIME | TEXT | Planilha (prÃ©-preenchido) | Regime tributÃ¡rio â€” jÃ¡ vem preenchido, NÃƒO alterar |
| **F** | QTD LANCAMENTOS CONTABEIS | INT | **ðŸ”µ BD DomÃ­nio** | â¬…ï¸� **PREENCHER** â€” LanÃ§amentos (`orig_lan IN (1, 39)`) |
| **G** | MES DOS LANCAMENTOS | DATE | Planilha (prÃ©-preenchido) | Data de referÃªncia â€” jÃ¡ vem preenchido, NÃƒO alterar |
| **H** | HORAS | TIME | Planilha (calculado) | Horas contÃ¡beis â€” calculado pela planilha, NÃƒO alterar |
| **I** | TEM FOLHA? | TEXT | **ðŸŸ¢ Planilha Carol** | â¬…ï¸� **PREENCHER** â€” SIM / NAO (baseado em empregados ativos) |
| **J** | HORAS FOLHA | TIME | Planilha (calculado) | CÃ¡lculo interno automÃ¡tico â€” NÃƒO alterar |
| **K** | TEM CONC. MANUAL? | TEXT | Manual/Fixo | SIM / NAO / 0 / - â€” NÃƒO alterar |
| **L** | HORAS CONC. MANUAL | TIME | Manual/Fixo | 3:00:00 se SIM â€” NÃƒO alterar |
| **M** | TEM CONTROLE ESTOQUE? | TEXT | Manual/Fixo | SIM / NAO / 0 / - â€” NÃƒO alterar |
| **N** | HORAS ESTOQUE | TIME | Manual/Fixo | 00:30:00 se SIM â€” NÃƒO alterar |
| **O** | TOTAL FATURAMENTO MÃŠS | FLOAT | **ðŸ”µ BD DomÃ­nio** | â¬…ï¸� **PREENCHER** â€” Valor monetÃ¡rio (efsaidas + efservicos) |
| **P** | HORAS FATURAMENTO | TIME | Planilha (calculado) | Calculado pela planilha â€” NÃƒO alterar |
| **Q** | TOTAL HORAS MÃŠS | TIME | Planilha (calculado) | Soma total â€” calculado pela planilha, NÃƒO alterar |

### 1.3 ClassificaÃ§Ã£o dos Campos

- **FIXOS (NÃƒO ALTERAR):** A, B, C, D â€” Dados cadastrais. **PROIBIDO TERMINANTEMENTE MODIFICAR.**
- **PRÃ‰-PREENCHIDOS (NÃƒO ALTERAR):** E, G â€” JÃ¡ vÃªm na planilha.
- **CALCULADOS PELA PLANILHA (NÃƒO ALTERAR):** H, J, P, Q â€” FÃ³rmulas internas da planilha.
- **CAMPOS MANUAIS (NÃƒO ALTERAR via automaÃ§Ã£o):** K, L, M, N â€” Mantidos do mÃªs anterior ou preenchidos manualmente.
- **ðŸŽ¯ CAMPOS DE PREENCHIMENTO AUTOMÃ�TICO (SOMENTE ESSES):**
  - **F** (QTD LanÃ§amentos) â†’ Fonte: **BD DomÃ­nio** (`bethadba.ctlancto`)
  - **O** (Faturamento) â†’ Fonte: **BD DomÃ­nio** (`bethadba.efsaidas` + `bethadba.efservicos`)
  - **I** (Tem Folha?) â†’ Fonte: **Planilha da Carol** (NÃƒO Ã© direto do DomÃ­nio)

---

## 2. REGRAS DE GOVERNANÃ‡A E INTELIGÃŠNCIA

Estas regras foram estabelecidas para garantir 100% de integridade e evitar inflaÃ§Ã£o de dados.

### 2.1 ValidaÃ§Ã£o Tripla de Identidade
Antes de qualquer escrita, o script deve validar o cliente cruzando:
- **A:** CÃ³digo DomÃ­nio (`codi_emp`) - **OBRIGATÃ“RIO**
- **C:** CNPJ / CPF (`cgce_emp`) - **PREFERENCIAL**
- **D:** Nome da Empresa (`nome_emp`) - **SECUNDÃ�RIO** (Tratar nomes fuzzy)
> **Regra de Escrita:** Somente preencher se pelo menos **2 de 3** campos baterem com o Banco de Dados.

### 2.2 LanÃ§amentos ContÃ¡beis (Coluna F)
- **REGRA DEFINITIVA:** Filtrar pelos cÃ³digos `1` (LanÃ§amento Normal) e `39` (ConciliaÃ§Ã£o BancÃ¡ria/Extrato BancÃ¡rio via importaÃ§Ã£o).
- **POR QUE:** Anteriormente filtrava-se apenas a origem 1. Contudo, validou-se que a produtividade contÃ¡bil manual e bancÃ¡ria Ã© composta pela soma de 1 e 39 (conforme verificado nos clientes 1283 e 3).

### 2.3 Fonte de Dados de Folha (Colunas I e J)
- **FONTE:** Planilha da Carol (`Controle de Empregados (CAROL)MM.AAAA.xls`).
- **LÃ“GICA:** Se a soma de (FuncionÃ¡rios + EstagiÃ¡rios + Contribuintes) for > 0, preencher **I** com "SIM".
- **NOTA:** A coluna **J** Ã© cÃ¡lculo interno da planilha e **nÃ£o deve ser alterada pela automaÃ§Ã£o**.

---

### 2.4 Anomalias a Reportar (ObrigatÃ³rio em .md)
O script deve gerar um **relatÃ³rio `.md`** de auditoria contendo:
1. **EMPRESAS COM MATCH PARCIAL (2/3):** Listar qual campo divergiu.
2. **EMPRESAS REJEITADAS (0-1/3):** Listar todos os campos e valores para conferÃªncia manual.
3. **EMPRESAS DUPLACADAS/Ã“RFÃƒS:** Alertas de integridade da planilha.

---

## 3. MAPEAMENTO DO BANCO DE DADOS â€” SISTEMA DOMÃ�NIO (Sybase)

### 3.1 ConexÃ£o ODBC
```
DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>
```

### 3.2 MÃ“DULO GERAL (CADASTROS)
Base central do Ecossistema DomÃ­nio.

*   **Tabela Mestre de Empresas:** `bethadba.geempre` (Nome tÃ©cnico correto)
    *   **Finalidade:** VÃ­nculo oficial dos cÃ³digos (`codi_emp`) com a razÃ£o social (`nome_emp`) e CNPJ (`cgce_emp`).
    *   **Uso na ValidaÃ§Ã£o Tripla:** Ã‰ a fonte primÃ¡ria dos 3 campos de conferÃªncia.

### 3.3 MÃ“DULO CONTÃ�BIL
### 3.2 MÓDULO GERAL (CADASTROS)
Base central do Ecossistema Domínio.

*   **Tabela Mestre de Empresas:** `bethadba.geempre` (Nome técnico correto)
    *   **Finalidade:** Vínculo oficial dos códigos (`codi_emp`) com a razão social (`nome_emp`) e CNPJ (`cgce_emp`).
    *   **Uso na Validação Tripla:** É a fonte primária dos 3 campos de conferência.

### 3.3 MÓDULO CONTÁBIL
Base para extração de Lançamentos e Regimes de Apuração (SPED).

*   **Tabela de Lançamentos:** `bethadba.ctlancto`
    *   **Finalidade:** Contagem e auditoria de linhas de lançamento.
    *   **Data de Filtro:** `data_lan`
    *   **Identificador de Origem:** `orig_lan`
        *   `1` = Lançamento Normal
        *   `39` = Conciliação Bancária (Extrato Bancário Importado)
        *   **Nota:** Filtro oficial para produtividade: `orig_lan IN (1, 39)`. O código `5` é **PROIBIDO** para fins de produtividade, pois contém lançamentos automáticos que não refletem volume manual.
*   **Tabela de Parâmetros SPED ECF (Vigência):** `bethadba.ctparmto_sped_vigencia`
    *   **Finalidade:** A principal e mais assertiva fonte para definir o Regime Tributário das empresas do Lucro Presumido e Lucro Real (pois os indicativos Fiscais muitas vezes se sobrepõem como 'Isentos' em alguns casos como o da empresa 1227).
    *   **Data de Filtro:** `vigencia`
    *   **Identificadores:** `forma_tributacao`
        *   `5` = Lucro Presumido
        *   `6` = Lucro Real
        *   `1` ou outros = Regime Geral (Buscar detalhamento na tabela Fiscal)

### 3.4 MÃ“DULO FISCAL (Enquadramento Federal)
Base definitiva para extraÃ§Ã£o de Regimes TributÃ¡rios e Faturamentos.

*   **Tabela de ParÃ¢metros Fiscais (VigÃªncia):** `bethadba.efparametro_vigencia`
    *   **Finalidade:** Fonte primÃ¡ria e tÃ©cnica para o Regime TributÃ¡rio (Enquadramento).
    *   **Caminho do Sistema:** ParÃ¢metros -> VigÃªncia -> Geral -> Federal -> Enquadramento -> Regime.
    *   **Campo Principal:** `rfed_par`
    *   **Tabela de Mapeamento TÃ©cnico:**
        *   `1` -> **Lucro Real**
        *   `2` -> **Simples Nacional** (ME)
        *   `4` -> **Simples Nacional** (EPP)
        *   `5` -> **Lucro Presumido**
        *   `7` -> **Lucro Arbitrado**
        *   `8` -> **Imune / Isenta**
    *   **Regra de AtivaÃ§Ã£o:** Utilizar sempre a `MAX(vigencia_par)` que seja menor ou igual Ã  data de apuraÃ§Ã£o desejada.

### 3.5 CONFRONTO E PRIORIDADE (Regras de Ouro)
Para garantir 100% de acerto:
1.  **Prioridade 1 (Fiscal):** Consultar `rfed_par` em `efparametro_vigencia`. Este campo ignora descriÃ§Ãµes personalizadas (como "VigÃªncia Inicial") e foca no cÃ³digo de enquadramento federal do DomÃ­nio.
2.  **Prioridade 2 (ContÃ¡bil):** Em caso de auditoria de SPED ECF, validar contra `forma_tributacao` em `ctparmto_sped_vigencia` (onde `5`=Presumido e `6`=Real).
3.  **AtenÃ§Ã£o:** Evitar o campo `descricao_par`, pois ele Ã© de livre digitaÃ§Ã£o pelo usuÃ¡rio e pode conter termos imprecisos.

---

## 4. QUERIES SQL PARA PREENCHIMENTO

### 4.1 Query de ValidaÃ§Ã£o Tripla (NOVA â€” EXECUTAR PRIMEIRO)
```sql
SELECT 
    codi_emp,
    cgce_emp,
    nome_emp
FROM bethadba.geempre
ORDER BY codi_emp
```

### 4.2 LanÃ§amentos ContÃ¡beis (â†’ Coluna F)
```sql
SELECT 
    codi_emp,
    COUNT(*) as qtd_lancamentos
FROM bethadba.ctlancto
WHERE data_lan >= '{{DATA_INICIO}}' AND data_lan <= '{{DATA_FIM}}'
AND orig_lan IN (1, 39)
GROUP BY codi_emp
ORDER BY codi_emp
```

### 4.3 Faturamento (â†’ Coluna O)
```sql
SELECT 
    codi_emp, 
    SUM(total_contabil) as faturamento
FROM (
    SELECT codi_emp, SUM(vcon_sai) as total_contabil 
    FROM bethadba.efsaidas 
    WHERE dsai_sai >= '{{DATA_INICIO}}' AND dsai_sai <= '{{DATA_FIM}}' 
    GROUP BY codi_emp
    UNION ALL
    SELECT codi_emp, SUM(vcon_ser) as total_contabil 
    FROM bethadba.efservicos 
    WHERE dser_ser >= '{{DATA_INICIO}}' AND dser_ser <= '{{DATA_FIM}}' 
    GROUP BY codi_emp
) base
GROUP BY codi_emp
```

### 4.4 Dados de Folha (â†’ Colunas I, J) â€” FONTE: PLANILHA DA CAROL

> âš ï¸� **ATENÃ‡ÃƒO:** Os dados de Folha **NÃƒO** sÃ£o extraÃ­dos diretamente do DomÃ­nio.
> A fonte Ã© a planilha da Carol: `Controle de Empregados {MES}{ANO}(CAROL).xls`
> Caminho: `c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\`

**Colunas da planilha Carol:**
- Coluna 1 (B): CÃ³digo da empresa
- Coluna 5 (F): CNPJ
- Coluna 7 (H): FuncionÃ¡rios
- Coluna 9 (J): EstagiÃ¡rios
- Coluna 11 (L): Contribuintes

**LÃ³gica de extraÃ§Ã£o:**
```
total_ativos = funcionarios + estagiarios + contribuintes

SE total_ativos > 0:
    I = "SIM"
    J = (total_ativos Ã— 0.33) + 1.5 horas
SE total_ativos == 0:
    I = "NAO"
    J = 00:00:00

ExceÃ§Ã£o: 1 contribuinte apenas (0 func, 0 estag) â†’ J = 1:10:00
```

---

## 5. REFERÃŠNCIA: TABELA DE HORAS (Calculada pela planilha â€” NÃƒO preencher)

> As colunas H, P e Q sÃ£o **calculadas internamente pela planilha** com base nos dados inseridos.
> Esta seÃ§Ã£o serve apenas como referÃªncia para auditoria.

### 5.1 Horas ContÃ¡beis (Coluna H) â€” FÃ³rmula Interna
Baseado no Regime (E) e na QTD LanÃ§amentos (F):

| Regime | LanÃ§amentos | Horas |
|--------|-------------|-------|
| Simples Nacional | atÃ© 200 | 4:30 |
| Simples Nacional | 201-500 | 7:00 |
| Simples Nacional | 501-1000 | 9:00 |
| Simples Nacional | 1001-2000 | 15:30 |
| Simples Nacional | 2001+ | 21:30 |
| Lucro Presumido | atÃ© 200 | 4:30 |
| Lucro Presumido | 201-500 | 9:00 |
| Lucro Presumido | 501-1000 | 15:30 |
| Lucro Presumido | 1001-2000 | 21:30 |
| Lucro Presumido | 2001+ | 23:30 |
| Lucro Real | atÃ© 200 | 9:00 |
| Lucro Real | 201-500 | 15:30 |
| Lucro Real | 501-1000 | 21:30 |
| Lucro Real | 1001-2000 | 33:40 |
| Lucro Real | 2001+ | 45:00 |

> Quando F = 0 ou NULL â†’ H = "False"

---

## 6. FLUXO DE EXECUÃ‡ÃƒO

### Passo 1: ValidaÃ§Ã£o Tripla
1. Extrair cadastros completos do DomÃ­nio (Query 4.1)
2. Para cada linha da planilha (linhas 2 a 760):
   - Comparar A â†” codi_emp
   - Comparar C â†” cgce_emp (limpos)
   - Comparar D â†” nome_emp (fuzzy)
3. Classificar: âœ… (3/3) | âš ï¸� (2/3) | â�Œ (0-1/3)
4. Gerar relatÃ³rio de anomalias

### Passo 2: Preenchimento (SOMENTE para âœ… e âš ï¸�)
1. **F** (QTD LanÃ§amentos) â†’ via Query 4.2 (BD DomÃ­nio)
2. **O** (Faturamento) â†’ via Query 4.3 (BD DomÃ­nio)
3. **I** (Tem Folha?) â†’ via Planilha da Carol (SeÃ§Ã£o 4.4)

> â›” **NÃƒO PREENCHER** nenhum outro campo alÃ©m de F, O e I.

### Passo 3: PreservaÃ§Ã£o
- **PROIBIDO** alterar colunas A, B, C, D (identificadores)
- **NÃƒO ALTERAR** colunas E, G (prÃ©-preenchidos)
- **NÃƒO ALTERAR** colunas H, J, P, Q (fÃ³rmulas/cÃ¡lculos internos da planilha)
- **NÃƒO ALTERAR** colunas K, L, M, N (campos manuais)
- Coluna I: valores texto "SIM" ou "NAO" (sem acento)

### Passo 4: RelatÃ³rio
Gerar arquivo `.md` com:
- Resumo da execuÃ§Ã£o (total processados, aprovados, alertas, rejeitados)
- Lista detalhada de anomalias (conforme SeÃ§Ã£o 2.5)
- Timestamp da execuÃ§Ã£o

---

## 7. REGRAS DE OURO

> â›” **PROIBIDO TERMINANTEMENTE** alterar qualquer dado da planilha que nÃ£o seja o que precisa ser preenchido.

> â›” Caso encontre empresa repetida, faltante, ou qualquer anomalia: **APENAS SINALIZE EM RELATÃ“RIO .MD**

> âœ… **TODO RELATÃ“RIO DEVE SER EM .MD**

> âœ… A validaÃ§Ã£o tripla Ã© o primeiro passo obrigatÃ³rio antes de qualquer escrita

> *Dica: Ao interligar queries temporais para "Pegar o ParÃ¢metro Ativo", utilizar sempre `INNER JOIN` filtrando pela funÃ§Ã£o `MAX(vigencia)` ou `MAX(vigencia_par)` menor ou igual ao fim do MÃªs de ApuraÃ§Ã£o para evitar duplicidades de mÃºltiplos enquadramentos passados.*

## 8. INTEGRAÇÃO COM A PLANILHA MASTER

Após a validação dos dados pela supervisão na planilha HORAS CONTABEIS_.xlsx, os valores devem ser sincronizados com a planilha CONTROLE DE HORAS DMF.xlsx.

### 8.1 Regras de De-Para (Master)
- **Coluna Destino:** P (Horário Contábil) na planilha Master.
- **Critério de Match (Double Match):**
    1. **Código Domínio:** Coluna H (8) na Master <-> Coluna A (1) na Contábil.
    2. **CNPJ:** Coluna J (10) na Master <-> Coluna C (3) na Contábil.
- **Ação:** O valor da Coluna **R** (Horas Validadas) da Contábil é copiado para a Coluna **P** da Master somente se ambos os critérios baterem.

### 8.2 Recalibragem de Totais
Toda vez que houver uma integração de dados contábeis, o script de reparo de totais deve ser executado para atualizar a **Coluna R (Total)** e os **Subtotais da linha 7** da Master, garantindo que a soma dos setores esteja correta.
