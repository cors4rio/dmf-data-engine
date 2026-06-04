"""
dmf_engine/modules/base.py
Contrato formal de módulo: BaseModule (ABC) + ModuleMeta (dataclass).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ModuleMeta:
    id: str
    nome: str
    desc: str
    setor: str       # "FISCAL" | "CONTABIL" | "DP" | "GESTAO"
    icon: str        # classe Tabler: "ti-receipt-2"
    color: str       # hex: "#B06A00"
    papeis: list     # ["admin", "fiscal"]
    status: str = "disponivel"   # "disponivel" | "breve"
    execucao: str = "async"      # "async" = via ThreadRunner (tarefa longa, emite eventos)
                                 # "sync"  = chamada direta; o retorno do execute() volta ao JS.
                                 #           Use para launchers que lançam subprocesso e
                                 #           precisam reportar sucesso/erro imediatamente.


class BaseModule(ABC):
    """
    Classe base para todos os módulos DMF Engine.

    Contrato:
      - meta  → ModuleMeta com identidade do módulo
      - execute(opcoes) → dict com resultado (chamado em thread separada via ThreadRunner)
      - get_status() → dict com estado atual (síncrono, opcional)

    Helpers disponíveis:
      - self.emit(event, data) → EventBus.emit
      - self.progress(pct, msg) → EventBus.progress
      - self.cfg(key, default) → ConfigManager.get
      - self.sessao() → dict da sessão atual
    """

    def __init__(self, bus, config, session_fn):
        self._bus = bus            # EventBus
        self._config = config      # ConfigManager
        self._session_fn = session_fn  # callable → dict sessão atual

    @property
    @abstractmethod
    def meta(self) -> ModuleMeta: ...

    @abstractmethod
    def execute(self, opcoes: dict) -> dict: ...

    def get_status(self) -> dict:
        return {"status": "idle"}

    def emit(self, event: str, data: dict = None):
        self._bus.emit(self.meta.id, event, data)

    def progress(self, pct: int, msg: str):
        self._bus.progress(self.meta.id, pct, msg)

    def cfg(self, key: str, default=None):
        return self._config.get(key, default)

    def sessao(self) -> dict:
        return self._session_fn() or {}
