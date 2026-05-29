# DMF Engine

O **DMF Engine** é uma plataforma desktop interna desenvolvida em Python para automação de produtividade contábil, fiscal e de departamento pessoal. A plataforma conecta-se ao banco Sybase SQL Anywhere (ERP Domínio) via ODBC, processa as regras de negócio de cada setor e alimenta as planilhas mestras de controle de horas.

**Status atual:** Teste Piloto em Produção — supervisores operando a interface compilada.

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

Para operadores do sistema (supervisores), consulte [`GUIA_USUARIO.md`](GUIA_USUARIO.md).

---

## Segurança

Nenhum dado sensível é versionado neste repositório. Senhas, URIs de banco e configurações de conexão residem exclusivamente em `config.json` local. Planilhas e dados de clientes são bloqueados pelo `.gitignore`.

---

*Para contribuir ou configurar o ambiente local, consulte [`docs/onboarding.md`](docs/onboarding.md).*
