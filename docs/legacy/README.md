# Documentação Histórica — docs/legacy/

> **Aviso:** Esta pasta contém documentação **histórica**. Não utilizá-la como fonte da verdade ativa para decisões técnicas ou operacionais.
>
> A documentação normativa e atualizada do projeto está em [`docs/`](../).

---

## Tabela de Equivalência

Use a tabela abaixo para navegar do documento legado ao equivalente ativo em `docs/`.

| Arquivo Legado | Documento Ativo Equivalente | Conteúdo Migrado |
|---|---|---|
| `DMF_ENGINEERING_GUIDE.md` | [`docs/arquitetura.md`](../arquitetura.md), [`docs/design-patterns.md`](../design-patterns.md), [`docs/onboarding.md`](../onboarding.md) | Seções 1-11 distribuídas entre os três documentos |
| `DISTRIBUICAO.md` | [`docs/operacoes.md`](../operacoes.md), [`docs/ROADMAP.md`](../ROADMAP.md) | Build, deploy, instalação e roadmap pós-piloto |
| `TASKBOARD.md` | [`docs/CHANGELOG.md`](../CHANGELOG.md), [`docs/ROADMAP.md`](../ROADMAP.md) | Seção Done → CHANGELOG; Seção A Fazer → ROADMAP |
| `task-REFATORACAO.md` | [`docs/CHANGELOG.md`](../CHANGELOG.md) (v0.2.0), [`docs/onboarding.md`](../onboarding.md) | Histórico do desacoplamento e exemplo de criação de serviço |
| `implementation_plan_melhorias.md` | [`docs/arquitetura.md`](../arquitetura.md) | Decisões arquiteturais e arquitetura-alvo |
| `SKILL.md` | [`docs/onboarding.md`](../onboarding.md) | Padrões de código consolidados na seção "Padrões de Código" |
| `SKILL1.md` | [`docs/onboarding.md`](../onboarding.md) | Padrões complementares consolidados na seção "Padrões de Código" |
| `Specs_Definitivos/Spec_Planilha_Master.md` | [`docs/regras-de-negocio.md`](../regras-de-negocio.md) | Estrutura da master e lookup duplo |
| `Specs_Definitivos/Spec_Produtividade_Fiscal.md` | [`docs/regras-de-negocio.md`](../regras-de-negocio.md) | Regras Fiscal (GELOGUSER, adicional 80%) |
| `Specs_Definitivos/Spec_Folha_Pagamento.md` | [`docs/regras-de-negocio.md`](../regras-de-negocio.md) | Regras DP (fórmula em cascata, exceções) |
| `Specs_Definitivos/Spec_Contabil.md` | [`docs/regras-de-negocio.md`](../regras-de-negocio.md) | Regras Contábil (3 fases, coluna R) |
| `Specs_Definitivos/QUERY_*.md` | `docs/legacy/Specs_Definitivos/` (preservado) | Queries SQL — não migradas; consultar aqui para rastreabilidade |
| `Specs_Definitivos/CT_*.md` | `docs/legacy/Specs_Definitivos/` (preservado) | Casos de teste de tabelas do banco — não migrados |
| `migracao-64bit.md` | [`docs/arquitetura.md`](../arquitetura.md), [`docs/ROADMAP.md`](../ROADMAP.md) (Seção 3) | Guia da migração 64-bit/DSN-less — **concluída (2026-06)**; preservado como registro da decisão e dos passos executados |

---

## Quando Consultar Esta Pasta

Esta pasta é útil exclusivamente para:

- **Arqueologia técnica**: entender decisões tomadas em versões anteriores do projeto.
- **Rastreabilidade histórica**: verificar o estado do sistema antes do desacoplamento Central ↔ Automação (v0.2.0).
- **Comparação**: contrastar como uma regra ou padrão era documentado anteriormente versus como está documentado hoje.

Para qualquer finalidade normativa (como implementar uma feature, entender uma regra de negócio, ou fazer onboarding), use os documentos em [`docs/`](../).

---

## Aviso sobre Links Internos

Os documentos nesta pasta foram preservados **byte-a-byte** a partir da raiz do repositório. Links internos entre eles podem estar **quebrados** devido à mudança de localização. Isso é esperado e não será corrigido — a integridade histórica do conteúdo tem prioridade sobre a navegabilidade dos links legados.

---

*Última atualização: 2026-05-29*
