"""
dmf_engine/modules/m_buscar_xml.py
Módulo Buscar XML (Padrão A) — adaptador BaseModule para o BuscarXMLService.

O BuscarXMLService roda no mesmo processo da Central DMF. Eventos de progresso
são traduzidos do callback interno (evento, dados) para o EventBus via self.emit().
"""
import os
import sys
import logging

from dmf_engine.modules.base import BaseModule, ModuleMeta

log = logging.getLogger("BuscarXML")

# Caminho do projeto externo (services/buscar_xml/) resolvido uma vez.
_SVC_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "buscar_xml")
)


def _injetar_path():
    if _SVC_DIR not in sys.path:
        sys.path.insert(0, _SVC_DIR)


class BuscarXMLModule(BaseModule):
    """
    Adaptador Padrão A: injeta services/buscar_xml/ no sys.path e delega
    toda a execução ao BuscarXMLService — que opera sem PyWebView.

    O execute() aqui é usado apenas para ações de controle simples
    (cancelar, status). As operações reais (executar_nfe, etc.) são
    despachadas via api.py → _service().
    """

    _service_instance = None  # singleton por processo

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="buscar_xml",
            nome="Buscar XML",
            desc="Exporta e organiza XMLs fiscais: NF-e, NFCe, SPED e TOKAI.",
            setor="FISCAL",
            icon="ti-file-search",
            color="#1565C0",
            papeis=["admin", "fiscal"],
        )

    def _get_service(self):
        """Retorna (ou cria) o BuscarXMLService singleton."""
        if BuscarXMLModule._service_instance is None:
            _injetar_path()
            from services import BuscarXMLService  # noqa

            def _on_event(evento: str, dados: dict):
                self.emit(evento, dados)

            cfg = self._config.load()
            base_dir = cfg.get("buscar_xml_base_dir") or _SVC_DIR
            BuscarXMLModule._service_instance = BuscarXMLService(
                base_dir=base_dir,
                on_event_cb=_on_event,
            )
        return BuscarXMLModule._service_instance

    def execute(self, opcoes: dict) -> dict:
        """
        execute() aqui trata apenas ações de controle (cancelar, status).
        As operações principais são chamadas diretamente pelo api.py.
        """
        import traceback
        try:
            acao = opcoes.get("acao", "status")
            svc = self._get_service()

            if acao == "cancelar":
                modulo = opcoes.get("modulo", "")
                return svc.cancelar(modulo)

            if acao == "status":
                return {"ok": True, **svc.get_status()}

            return {"ok": False, "erro": f"Ação desconhecida: {acao}"}

        except Exception as e:
            log.error(traceback.format_exc())
            return {"ok": False, "erro": str(e)}

    def get_status(self) -> dict:
        try:
            svc = self._get_service()
            return svc.get_status()
        except Exception:
            return {"status": "idle"}
