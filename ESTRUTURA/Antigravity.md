# Usando n8n com o Antigravity 🚀

## 1. O que é o n8n MCP?
O **n8n-mcp** é um servidor MCP (Model Context Protocol) que permite ao Antigravity interagir diretamente com a sua instância do n8n. Com isso, é possível:
- Criar, editar, buscar e ativar/desativar fluxos de trabalho (workflows) do n8n.
- Obter informações dos nós (nodes) e credenciais dispobíveis na instância.
- Obter execuções e estatísticas do n8n.

### Configuração no Antigravity
A configuração base já foi adicionada ao arquivo `C:\Users\DMF-AUTOMACAO\.gemini\antigravity\mcp_config.json`.
Para que o Antigravity consiga conectar a sua instância, você precisará editar o arquivo e substituir os valores de ambiente `env`:
- `N8N_HOST`: O endereço da sua instância n8n (ex: `https://meu-n8n.com`).
- `N8N_EMAIL`: E-mail associado à sua conta n8n.
- `N8N_API_KEY`: Chave de API gerada no painel do n8n.

## 2. Skills para o n8n 📚
Para tornar a criação de fluxos de trabalho infalível e robusta, baixamos o repositório **n8n-skills**. Ele contém um conjunto de 7 habilidades (skills) especializadas que o Antigravity consulta e utiliza antes e durante o processo de programação (neste workspace, estão na pasta `scratch/n8n-skills/skills/`).

Aqui está o que cada uma das skills oferece:

### 1. n8n Expression Syntax (`n8n-expression-syntax`)
Ajuda o Antigravity a dominar a sintaxe de expressões do n8n (uso de `{{}}`, variáveis como `$json`, `$node`, `$now`, etc) e a evitar erros comuns, como tentar usar expressões onde nós de código (`Code nodes`) seriam mais adequados.

### 2. n8n MCP Tools Expert (`n8n-mcp-tools-expert`) - **Maior Prioridade**
Uma base de conhecimento essencial para eu saber como interagir e formatar corretamente os comandos do MCP. Ajuda a definir filtros de validação, diferenciar os formatos de nomeclatura de nodes (`nodes-base.*` vs `n8n-nodes-base.*`) e aplicar os parâmetros de configuração de maneira segura.

### 3. n8n Workflow Patterns (`n8n-workflow-patterns`)
Baseada na análise de mais de 2.600 templates do n8n, ensina as 5 principais arquiteturas e padrões para construção de fluxos de trabalho sólidos e eficientes (como processamento via webhook, APIs HTTP, integrações de bancos de dados, fluxos agendados, e uso de IAs).

### 4. n8n Validation Expert (`n8n-validation-expert`)
Guia especializado em validação, interpretação de erros e loops de debugging. É acionado quando um erro ocorre, ajudando o Antigravity a interpretar falsos positivos e a corrigir configurações corrompidas.

### 5. n8n Node Configuration (`n8n-node-configuration`)
Auxilia na configuração fina de nós focando na dependência entre propriedades (exemplo: ao ativar `sendBody`, ativar `contentType`). Fornece boas práticas para conectar tipos de operações específicas e inteligência artificial.

### 6. n8n Code JavaScript (`n8n-code-javascript`)
Garante a escrita do código em nós de Código utilizando JavaScript de forma compatível e livre de erros ($input.all(), acesso ao $json, e retorno apropriado no formato `[{json: {...}}]`). Previne a esmagadora maioria das falhas em implantações de código JS no n8n.

### 7. n8n Code Python (`n8n-code-python`)
Um guia importante sobre as *limitações* do Python dentro do n8n. Sabendo que não é possível instalar bibliotecas externas (como requests, pandas), esta skill ensina *workarounds* e como utilizar apenas bibliotecas contidas na Standard Library do Python.

---

**Como começar a criar fluxos?**
Com isto em mãos, sempre que você pedir para eu construir ou consertar um workflow do n8n, basta dizer o que é preciso e eu automaticamente utilizarei as _skills_ e ferramentas MCP para entregar no padrão correto!
