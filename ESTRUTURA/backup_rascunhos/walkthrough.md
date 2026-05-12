# Mapeamento EFD Reinf > Rendimentos Isentos

A busca nos arquivos do projeto confirmou que já temos o mapeamento técnico (tabelas de banco de dados) para o fluxo de **EFD Reinf > Rendimentos Isentos**.

## Tabelas Identificadas

As tabelas específicas para Rendimentos Isentos foram localizadas no **Lote 64** da documentação de tabelas descobertas:

| Tabela | Descrição |
|--------|-----------|
| [EFOUTROSDADOS_REINF_RENDIMENTOS_ISENTOS](file:///z:/ICARO%20CONCEICAO%20DOS%20SANTOS/PROJETOS/BANCO%20DE%20DADOS%20DOMIINIO/07_TABELAS_DESCOBERTAS/lote_64_tabelas_1891_a_1920.md#L214) | Tabela principal que armazena os valores de rendimentos isentos por beneficiário e competência. |
| [EFOUTROSDADOS_REINF_RENDIMENTOS_ISENTOS_CONTAS](file:///z:/ICARO%20CONCEICAO%20DOS%20SANTOS/PROJETOS/BANCO%20DE%20DADOS%20DOMIINIO/07_TABELAS_DESCOBERTAS/lote_64_tabelas_1891_a_1920.md#L247) | Vínculo entre os rendimentos isentos e as contas contábeis. |
| [EFOUTROSDADOS_REINF_RENDIMENTOS_ISENTOS_CONTAS_PARAM](file:///z:/ICARO%20CONCEICAO%20DOS%20SANTOS/PROJETOS/BANCO%20DE%20DADOS%20DOMIINIO/07_TABELAS_DESCOBERTAS/lote_64_tabelas_1891_a_1920.md#L274) | Parâmetros para importação de saldos das contas contábeis. |
| [EFOUTROSDADOS_REINF_RENDIMENTOS_ISENTOS_RES_EXTERIOR](file:///z:/ICARO%20CONCEICAO%20DOS%20SANTOS/PROJETOS/BANCO%20DE%20DADOS%20DOMIINIO/07_TABELAS_DESCOBERTAS/lote_64_tabelas_1891_a_1920.md#L303) | Dados complementares para beneficiários residentes no exterior. |

## Informações Adicionais de REINF

Também existem tabelas mapeadas para o controle geral de envio e retorno dos eventos da EFD Reinf (Eventos da série R-2000 e R-4000):

- **Controle de Envio**: `bethadba.EFD_REINF_ENVIO_ARQUIVOS`
- **Controle de Retorno**: `bethadba.EFD_REINF_RETORNO_ARQUIVOS`
- **Parâmetros de Acumulador**: A tabela `bethadba.EFACUMULADOR_VIGENCIA` possui o campo `EFD_REINF_TIPO_SERVICO` para classificar o tipo de serviço no REINF.

## Onde encontrar os detalhes técnicos
O detalhamento completo do schema destas tabelas (colunas, tipos e amostras de dados) pode ser encontrado em:
- [07_TABELAS_DESCOBERTAS/lote_64_tabelas_1891_a_1920.md](file:///z:/ICARO%20CONCEICAO%20DOS%20SANTOS/PROJETOS/BANCO%20DE%20DADOS%20DOMIINIO/07_TABELAS_DESCOBERTAS/lote_64_tabelas_1891_a_1920.md)
- [07_TABELAS_DESCOBERTAS/lote_21_tabelas_0601_a_0630.md](file:///z:/ICARO%20CONCEICAO%20DOS%20SANTOS/PROJETOS/BANCO%20DE%20DADOS%20DOMIINIO/07_TABELAS_DESCOBERTAS/lote_21_tabelas_0601_a_0630.md) (para eventos generais do REINF)
