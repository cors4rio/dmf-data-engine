# DMF Engine

## Visão Geral

O **DMF Engine** é um motor local robusto desenvolvido em Python focado na automação e extração de métricas de produtividade contábil, fiscal e de departamento pessoal. Originalmente criado como um conjunto de scripts soltos (ETL), o projeto evoluiu para um aplicativo desktop completo com uma interface web moderna (pywebview + HTML/CSS/JS) instalável na máquina dos supervisores.

O objetivo do sistema é conectar-se diretamente ao banco Sybase SQL Anywhere (Domínio Sistemas), consolidar tempos de operação (logs de uso), cruzar com dados de folhas de pagamento e faturamento (exceções), e calcular a produtividade com precisão milimétrica para alimentar as planilhas mestras de controle de horas.

## Fase Atual: Teste Piloto em Produção 🚀

O projeto completou sua fase de desenvolvimento central e estruturação da arquitetura e agora está em **Teste de Produção com Usuários Reais**. Os supervisores utilizarão a interface gráfica compilada para gerar os relatórios de produtividade, substituindo a execução de scripts manuais.

## Funcionalidades Principais

- **Interface de Usuário (Dashboard)**: UI moderna, dark mode com visual premium, desenhada para ser amigável a usuários não-técnicos (supervisores dos setores).
- **Extração via ODBC Dinâmica**: Consultas SQL de alta performance conectadas à base Sybase, abstraindo a complexidade relacional do Domínio Sistemas.
- **Motor de Regras (DP, Contábil, Fiscal)**: Lógicas avançadas de acréscimo de tempo, rateio entre empresas filiais, e cálculos de "sócios vs funcionários".
- **Sistema de Lock Cooperativo**: Previne que dois usuários alterem as planilhas mestras simultaneamente (concorrência).
- **Automação de Instalação e Distribuição**: Build simplificado usando PyInstaller e instalação na máquina cliente via script híbrido Batch/PowerShell com barra de progresso customizada.

## Estrutura do Projeto

- `/dmf_engine/`: Módulo principal contendo a inicialização do app UI e orquestrador.
- `/dmf_engine/ui/`: Frontend Vanilla JS e CSS do aplicativo.
- `/engine/`: Módulos de conexão (banco de dados, arquivos excel) e sistema de locking.
- `/modulos/`: Implementação das regras de negócio por setor (dp.py, fiscal.py, contabil.py).
- `build_runner.py` e `build.bat`: Pipelines locais de compilação da aplicação.
- `Instalar DMF Engine.bat`: Instalador local (deploy para rede) utilizado pelo usuário final.

## Aviso de Segurança e Conformidade (⚠️ IMPORTANTE)

**Nenhum dado sensível é versionado neste repositório.**
- Senhas, URIs e configurações sensíveis de conexão devem existir apenas no arquivo `config.json` e nas variáveis de ambiente na máquina host/usuário.
- Arquivos contendo dados de clientes (Planilhas Excel, `.txt`, relatórios de dump, etc.) são proibidos e bloqueados pelo `.gitignore`.
- O código-fonte está estritamente em conformidade com as regras de higienização de PII e chaves criptográficas.

## Guias e Documentação

- `DISTRIBUICAO.md`: Diretrizes e roadmap de deployment do projeto em rede.
- `GUIA_USUARIO.md`: Documentação passo a passo ensinando os usuários a operar a interface (versão live também hospedada no Anytype do escritório).
- `TASKBOARD.md`: Backlog técnico e histórico de desenvolvimento.
