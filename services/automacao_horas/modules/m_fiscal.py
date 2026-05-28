"""
dmf_engine/modules/m_fiscal.py
FiscalModule — adaptador do módulo Fiscal para o sistema de plugins DMF Engine.
"""
import os
import logging
import traceback
from datetime import datetime

from modules.base import BaseModule, ModuleMeta

log = logging.getLogger("FiscalModule")


class FiscalModule(BaseModule):

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="fiscal",
            nome="Fiscal",
            desc="Apuração de horas fiscais via ERP Domínio.",
            setor="FISCAL",
            icon="ti-receipt-2",
            color="#B06A00",
            papeis=["admin", "fiscal"],
        )

    def execute(self, opcoes: dict) -> dict:
        from modulos.fiscal import extrair_e_preencher_fiscal
        from engine.master_writer import MasterWriter
        from engine.lock_master import adquirir_lock, liberar_lock

        import compat as _main
        db = _main.db
        estado_sh = _main.estado_sh
        PROJECT_ROOT = _main.PROJECT_ROOT

        cfg = self._config.load()
        sessao = self.sessao()
        usuario = sessao.get("usuario", "desconhecido")
        host = os.environ.get("COMPUTERNAME", "unknown")

        master_path = opcoes.get("master_path") or cfg.get("master_path") or os.path.join(
            PROJECT_ROOT, "CONTROLE DE HORAS DMF.xlsm"
        )
        data_inicio = opcoes.get("data_inicio")
        data_fim = opcoes.get("data_fim")

        if not data_inicio or not data_fim:
            return {"ok": False, "erro": "Competência ausente."}
        if not os.path.exists(master_path):
            return {"ok": False, "erro": "Planilha master não encontrada."}

        ok_lock, info_lock = adquirir_lock(master_path, usuario, host, "Fiscal")
        if not ok_lock:
            ocupante = info_lock.get("usuario", "?")
            return {"ok": False, "tipo": "lock", "erro": f"Master em uso por {ocupante}."}

        try:
            lockfile = os.path.join(os.path.dirname(master_path),
                                    "~$" + os.path.basename(master_path))
            if os.path.exists(lockfile):
                return {"ok": False, "tipo": "locked",
                        "erro": "Master aberta no Excel. Feche e tente de novo."}

            self.progress(15, "Conectando ao Domínio...")
            if not db.connect():
                return {"ok": False, "erro": "Falha na conexão ODBC."}

            self.progress(30, "Abrindo master...")
            writer = MasterWriter(master_path)
            if not writer.carregar():
                return {"ok": False, "erro": "Falha ao abrir master."}

            self.progress(55, f"Executando Fiscal ({data_inicio[:7]})...")
            ok = extrair_e_preencher_fiscal(
                writer, data_inicio, data_fim,
                adicional_pct=cfg.get("fiscal_adicional_pct", 80),
            )

            if cfg.get("governanca_gravar_zero", True):
                self.progress(80, "Limpando resíduos do mês anterior na col. O...")
                writer.limpar_nao_tocadas([15])

            self.progress(88, "Recalculando totais...")
            writer.recalcular_totais()

            self.progress(95, "Salvando master...")
            salvo = writer.salvar()
            if not salvo and writer.ultimo_erro:
                return {"ok": False, **writer.ultimo_erro}

            if ok:
                competencia = data_inicio[:7]
                estado_sh.marcar(master_path, "fiscal", competencia, "lancado",
                                 por=usuario, host=host)

            self.progress(100, "Concluído.")
            return {"ok": bool(ok), "competencia": data_inicio[:7]}

        except Exception as e:
            log.error(f"[FISCAL] {traceback.format_exc()}")
            return {"ok": False, "erro": str(e)}
        finally:
            liberar_lock(master_path, usuario, host)
