# Guia Mestre de Integração - Domínio Sistemas (Sybase)

Este documento é o **Padrão Oficial** para criação de novas bases de dados, fluxos de automação (n8n, Python, PowerBI) e relatórios que dependam do ERP Domínio.

## 1. Conectividade
- **Protocolo**: ODBC (Driver SQL Anywhere)
- **DSN Padrão**: `Contabil`
- **Usuário/Senha**: `EXTERNO` / `<SENHA_NO_ENV>`

## 2. Estrutura Mestre (Cadastros)
Toda integração deve começar pelo vínculo oficial:
- **Tabela**: `bethadba.geempre`
- **Chave Única**: `codi_emp`
- **Campos Essenciais**: `nome_emp` (Razão Social), `cnpj_emp` (CNPJ).

## 3. Lógica de Vigência (Regra de Ouro)
Como o Domínio armazena históricos, para pegar o dado **ATUAL** ou **DA ÉPOCA**, utilize sempre a sub-query de MAX:
```sql
SELECT campo FROM tabela p 
WHERE p.codi_emp = X 
AND p.vigencia = (SELECT MAX(vigencia) FROM tabela WHERE codi_emp = p.codi_emp AND vigencia <= 'DATA_AFETADA')
```

## 4. Enquadramento Tributário (Regime Real)
Para evitar "Regimes Falsos", use exclusivamente o mapeamento por código `rfed_par`.
- **Tabela**: `bethadba.efparametro_vigencia`
- **Caminho GUI**: Parâmetros > Vigência > Geral > Federal > Enquadramento > Regime.
- **Mapeamento**:
    - `1`: **Lucro Real**
    - `2` ou `4`: **Simples Nacional**
    - `5`: **Lucro Presumido**
    - `8`: **Imune / Isenta**

## 5. Módulos e Tabelas Chave

### 💹 Contábil
- `ctlancto`: Lançamentos (Filtro: `data_lan`)
- `ctparmto_sped_vigencia`: Forma de Tributação ECF (`forma_tributacao`)

### 📑 Fiscal
- `efsaidas`: Faturamento de Vendas (Filtro: `dsai_sai`)
- `efservicos`: Faturamento de Serviços (Filtro: `dser_ser`)
- `efparametro_vigencia`: Configurações Federais e Enquadramento.

### 👥 Folha de Pagamento
- `foparmto`: Parâmetros de cálculo.
- `foempregados`: Dados contratuais.

## 6. Boas Práticas de Integração
1. **Data Only**: Sempre carregue dados com `data_only=True` em Excel para evitar fórmulas quebradas.
2. **Normalização de CNPJ**: Converter CNPJs para String sem pontuação antes de comparar.
3. **Tratamento de None**: No Sybase, campos vazios retornam `None`. Sempre tratar no código.
