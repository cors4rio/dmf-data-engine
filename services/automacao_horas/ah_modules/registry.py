"""
dmf_engine/modules/registry.py
ModuleRegistry — auto-discovery e dispatch genérico para todos os módulos.
"""
import logging

from dmf_engine.core.thread_runner import ThreadRunner
from dmf_engine.modules.base import BaseModule

log = logging.getLogger("ModuleRegistry")


class ModuleRegistry:
    """
    Mantém o catálogo de módulos registrados e despacha execuções via ThreadRunner.

    Uso:
        registry = ModuleRegistry(runner)
        registry.register(FiscalModule(bus, config, session_fn))
        registry.execute("fiscal", opcoes)   # → dispara em thread, emite eventos
        registry.catalog()                   # → {setor: [meta_dict, ...]}
    """

    def __init__(self, runner: ThreadRunner):
        self._modules: dict[str, BaseModule] = {}
        self._runner = runner

    def register(self, module: BaseModule):
        mid = module.meta.id
        if mid in self._modules:
            log.warning(f"[REGISTRY] Módulo '{mid}' já registrado — substituindo.")
        self._modules[mid] = module
        log.info(f"[REGISTRY] Módulo registrado: {mid} ({module.meta.nome})")

    def execute(self, module_id: str, opcoes: dict) -> dict:
        mod = self._modules.get(module_id)
        if not mod:
            return {"ok": False, "erro": f"Módulo '{module_id}' não encontrado."}
        self._runner.run(module_id, mod.execute, opcoes)
        return {"ok": True, "status": "running"}

    def get_status(self, module_id: str) -> dict:
        mod = self._modules.get(module_id)
        return mod.get_status() if mod else {}

    def catalog(self) -> dict:
        """Retorna {setor: [meta_dict, ...]} para o JS renderizar o catálogo."""
        result: dict[str, list] = {}
        for mod in self._modules.values():
            m = mod.meta
            result.setdefault(m.setor, []).append({
                "id": m.id,
                "nome": m.nome,
                "desc": m.desc,
                "icon": m.icon,
                "color": m.color,
                "status": m.status,
                "papeis": m.papeis,
            })
        return result

    def catalog_for_role(self, papel: str) -> dict:
        """Catálogo filtrado por papel do usuário."""
        raw = self.catalog()
        filtered = {}
        for setor, mods in raw.items():
            visible = [m for m in mods if papel == "admin" or papel in m["papeis"]]
            if visible:
                filtered[setor] = visible
        return filtered

    def get(self, module_id: str) -> "BaseModule | None":
        return self._modules.get(module_id)

    def ids(self) -> list[str]:
        return list(self._modules.keys())
