# Central DMF

A **Central DMF** é a plataforma desktop interna do escritório, desenvolvida em Python. Atende 5 setores — Administrativo, Fiscal, Contábil, Pessoal (DP) e Legalização — hospedando múltiplos módulos (Automação de Horas, Relatório de Rendimentos, Buscar XML, Sem Movimento NFS-e, TFF Salvador). Conecta-se ao banco SAP SQL Anywhere 17 (ERP Domínio) via ODBC 64-bit DSN-less e alimenta as planilhas mestras de controle de horas.

> O executável e o instalador mantêm o nome de arquivo histórico **`DMF Engine`** (`DMF Engine.exe`, `Instalar DMF Engine.bat`). O nome do produto, em qualquer texto, é **Central DMF**.

**Status atual:** Piloto em produção — interface compilada em uso.

---

## Documentação Técnica

Toda a documentação técnica está centralizada em **[`docs/`](docs/README.md)**.

| Área | Documento |
|---|---|
| Portal e índice navegável | [`docs/README.md`](docs/README.md) |
| Arquitetura do sistema | [`docs/arquitetura.md`](docs/arquitetura.md) |
| Padrões e decisões técnicas | [`docs/design-patterns.md`](docs/design-patterns.md) |
| Catálogo de módulos | [`docs/modulos.md`](docs/modulos.md) |
| Regras de negócio (fonte da verdade) | [`docs/regras-de-negocio.md`](docs/regras-de-negocio.md) |
| Build, deploy e segurança | [`docs/operacoes.md`](docs/operacoes.md) |
| Setup e onboarding técnico | [`docs/onboarding.md`](docs/onboarding.md) |
| Glossário do domínio | [`docs/glossario.md`](docs/glossario.md) |
| Histórico de versões | [`docs/CHANGELOG.md`](docs/CHANGELOG.md) |
| Próximos passos | [`docs/ROADMAP.md`](docs/ROADMAP.md) |
| Documentação histórica | [`docs/legacy/`](docs/legacy/README.md) |

---

## Guia do Usuário Final

Para qualquer pessoa da empresa que usa o sistema, consulte [`GUIA_USUARIO.md`](GUIA_USUARIO.md) (uso no dia a dia) e [`docs/guia-instalacao-primeiro-uso.md`](docs/guia-instalacao-primeiro-uso.md) (instalação e primeiro login).

---

## Segurança

Nenhum dado sensível é versionado neste repositório. Senhas, URIs de banco e configurações de conexão residem exclusivamente em `config.json` local. Planilhas e dados de clientes são bloqueados pelo `.gitignore`.

---

*Para contribuir ou configurar o ambiente local, consulte [`docs/onboarding.md`](docs/onboarding.md).*
