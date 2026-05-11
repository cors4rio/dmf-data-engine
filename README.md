# DMF Data Engine

## Visão Geral

O **DMF Data Engine** é um conjunto de ferramentas e automações desenvolvidas em Python focadas na produtividade contábil e fiscal. O principal objetivo do projeto é a extração, transformação e carga (ETL) de dados provenientes do sistema ERP Domínio Sistemas (via ODBC). 

Este sistema captura tempos de operação (logs de uso), cruza com dados de folhas de pagamento e faturamento, e preenche planilhas mestras de produtividade de forma automatizada, garantindo precisão de segundos na apuração.

## Funcionalidades Principais

- **Extração via ODBC**: Conexões diretas ao banco de dados Sybase SQL Anywhere (Domínio).
- **Tratamento de Dados**: Aplicação de regras de negócio específicas, como fator de adicional de tempo (ex: 80% de overhead em tarefas fiscais).
- **Preenchimento Automatizado**: Manipulação de planilhas complexas em Excel (`.xlsx`, `.xlsm`) mantendo a integridade das fórmulas VBA originais.
- **Relatórios**: Geração de dados analíticos detalhando produtividade individual de colaboradores por cliente.

## Estrutura do Projeto

- `/ESTRUTURA`: Contém todos os scripts Python (`.py`) para análises, testes, mapeamento e automações centrais, além da documentação detalhada (Specs) do negócio.
- Modelos lógicos e queries validadas estão documentadas em arquivos Markdown (ex: `Spec_Produtividade_Fiscal.md`).

## Aviso de Segurança (⚠️ IMPORTANTE)

**Nenhum dado sensível é versionado neste repositório.**
- Senhas, URIs e configurações de conexão devem ser obrigatoriamente passadas via variáveis de ambiente (`.env`).
- Os scripts foram higienizados para utilizar placeholders (`<SENHA_NO_ENV>`, `<USER_NO_ENV>`).
- Planilhas contendo dados reais de clientes (`.xls`, `.xlsx`, `.csv`) e logs sensíveis (`.txt`, `.log`) são ignorados via `.gitignore`.
