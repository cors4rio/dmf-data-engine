"""
dmf_engine/modules/m_contabil.py
ContabilModule — adaptador do módulo Contábil para o sistema de plugins DMF Engine.

Fluxo em 2 fases:
  - fase=2 (processar): threaded — consulta Domínio e grava HORAS CONTABEIS.xlsx
  - fase=5 (injetar):   threaded — lê coluna R validada e grava coluna R na master
"""
import os
import logging
import traceback
from datetime import datetime

from modules.base import BaseModule, ModuleMeta

log = logging.getLogger("ContabilModule")


class ContabilModule(BaseModule):

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="contabil",
            nome="Contábil",
            desc="Processamento e lançamento de horas contábeis via Domínio.",
            setor="CONTABIL",
            icon="ti-building-bank",
            color="#185FA5",
            papeis=["admin", "contabil"],
        )

    def execute(self, opcoes: dict) -> dict:
        fase = opcoes.get("fase", 2)
        if fase == 5:
            return self._fase5_injetar_master(opcoes)
        return self._fase2_processar(opcoes)

    # ── Fase 2: processar HORAS CONTABEIS ───────────────────────────────────

    def _fase2_processar(self, opcoes: dict) -> dict:
        from modulos.contabil_preenchedor import preencher_horas_contabeis

        import compat as _main
        db = _main.db
        estado_sh = _main.estado_sh
        PROJECT_ROOT = _main.PROJECT_ROOT

        cfg = self._config.load()
        sessao = self.sessao()
        usuario = sessao.get("usuario", "desconhecido")
        host = os.environ.get("COMPUTERNAME", "unknown")

        caminho = opcoes.get("caminho") or cfg.get("contabil_origem_path")
        data_inicio = opcoes.get("data_inicio")
        data_fim = opcoes.get("data_fim")

        if not caminho or not os.path.exists(caminho):
            return {"ok": False, "erro": "Selecione a planilha HORAS CONTABEIS.xlsx."}
        if not data_inicio or not data_fim:
            return {"ok": False, "erro": "Competência ausente."}

        try:
            self.progress(10, "Conectando ao Domínio...")
            if not db.connect():
                return {"ok": False, "erro": "Falha na conexão ODBC com o Domínio."}

            self.progress(30, "Consultando lançamentos / faturamento / folha...")
            resultado = preencher_horas_contabeis(caminho, data_inicio, data_fim,
                                                  raiz_relatorios=PROJECT_ROOT)
            self.progress(95, "Finalizando...")

            if resultado.get("ok"):
                competencia = data_inicio[:7]
                master_path = cfg.get("master_path") or os.path.join(
                    PROJECT_ROOT, "CONTROLE DE HORAS DMF.xlsm"
                )
                estado_sh.marcar(master_path, "contabil", competencia, "processado",
                                 por=usuario, host=host)
                estado_sh.remover(master_path, "contabil", competencia, evento="lancado")
                self._config.save({
                    f"contabil_processado_{competencia}": True,
                    f"contabil_processado_em_{competencia}": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    f"contabil_lancado_{competencia}": False,
                })

            self.progress(100, "Concluído.")
            return {**resultado, "fase": 2}

        except Exception as e:
            log.error(f"[CONTÁBIL-FASE2] {traceback.format_exc()}")
            return {"ok": False, "erro": str(e)}

    # ── Fase 5: injetar na master ────────────────────────────────────────────

    def _fase5_injetar_master(self, opcoes: dict) -> dict:
        from modulos.contabil_integrador import injetar_contabil_na_master
        from engine.master_writer import MasterWriter
        from engine.lock_master import adquirir_lock, liberar_lock

        import compat as _main
        estado_sh = _main.estado_sh
        PROJECT_ROOT = _main.PROJECT_ROOT

        cfg = self._config.load()
        sessao = self.sessao()
        usuario = sessao.get("usuario", "desconhecido")
        host = os.environ.get("COMPUTERNAME", "unknown")

        caminho = opcoes.get("caminho") or cfg.get("contabil_origem_path")
        master_path = opcoes.get("master_path") or cfg.get("master_path") or os.path.join(
            PROJECT_ROOT, "CONTROLE DE HORAS DMF.xlsm"
        )
        data_inicio = opcoes.get("data_inicio")
        data_fim = opcoes.get("data_fim")

        if not all([caminho, data_inicio, data_fim]):
            return {"ok": False, "erro": "Parâmetros incompletos (caminho/competência)."}
        if not os.path.exists(caminho):
            return {"ok": False, "erro": "Planilha HORAS CONTABEIS não encontrada."}
        if not os.path.exists(master_path):
            return {"ok": False, "erro": "Planilha master não encontrada."}

        ok_lock, info_lock = adquirir_lock(master_path, usuario, host, "Contábil (lançamento)")
        if not ok_lock:
            ocupante = info_lock.get("usuario", "?")
            return {"ok": False, "tipo": "lock", "erro": f"Master em uso por {ocupante}."}

        try:
            lockfile = os.path.join(os.path.dirname(master_path),
                                    "~$" + os.path.basename(master_path))
            if os.path.exists(lockfile):
                return {"ok": False, "tipo": "locked",
                        "erro": "Master está aberta no Excel. Feche o arquivo."}

            self.progress(20, "Abrindo planilha master...")
            writer = MasterWriter(master_path)
            if not writer.carregar():
                return {"ok": False, "erro": "Falha ao abrir master."}

            self.progress(50, "Lendo horas validadas e lançando na master...")
            resultado = injetar_contabil_na_master(writer, caminho, data_inicio, data_fim)

            self.progress(80, "Recalculando totais...")
            writer.recalcular_totais()

            self.progress(95, "Salvando master...")
            salvo = writer.salvar()
            if not salvo and writer.ultimo_erro:
                return {"ok": False, **writer.ultimo_erro}

            if resultado.get("ok"):
                competencia = data_inicio[:7]
                estado_sh.marcar(master_path, "contabil", competencia, "lancado",
                                 por=usuario, host=host)
                self._config.save({
                    f"contabil_lancado_{competencia}": True,
                    f"contabil_lancado_em_{competencia}": datetime.now().strftime("%d/%m/%Y %H:%M"),
                })

            self.progress(100, "Concluído.")
            return {**resultado, "fase": 5}

        except Exception as e:
            log.error(f"[CONTÁBIL-FASE5] {traceback.format_exc()}")
            return {"ok": False, "erro": str(e)}
        finally:
            liberar_lock(master_path, usuario, host)
