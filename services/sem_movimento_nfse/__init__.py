"""
services/sem_movimento_nfse/ — Módulo "Sem Movimento NFS-e Salvador".

Automação que, para um lote de empresas (CNPJ + senha), emite os comprovantes
de notas EMITIDAS e RECEBIDAS no portal NFS-e de Salvador para uma competência.

Pacotes com prefixo `sm_` para não colidir com os pacotes da raiz da Central
(engine/, config/, core/, modules/) — ver memória colisao-pacotes-engine-config.
"""
from sm_service import SemMovimentoService  # noqa: F401
