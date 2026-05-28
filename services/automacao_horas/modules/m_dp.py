"""
dmf_engine/modules/m_dp.py
DPModule — adaptador do módulo Departamento Pessoal para o sistema de plugins DMF Engine.

Fluxo em 2 fases:
  - fase=1 (importar_carol): síncrono — abre file dialog, lê planilha Carol
  - fase=2 (injetar_master): threaded — calcula DP e grava coluna Q na master

O ThreadRunner chama execute() em thread separada. Para a fase 1 (síncrona),
execute() retorna imediatamente com o resultado do file dialog.
"""
import os
import logging
import traceback
from datetime import datetime

from modules.base import BaseModule, ModuleMeta

log = logging.getLogger("DPModule")


class DPModule(BaseModule):

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="dp",
            nome="Departamento Pessoal",
            desc="Cálculo e lançamento de horas do DP via planilha Carol + Domínio.",
            setor="DP",
            icon="ti-users",
            color="#2A7A45",
            papeis=["admin", "dp"],
        )

    def execute(self, opcoes: dict) -> dict:
        fase = opcoes.get("fase", 2)
        if fase == 1:
            return self._fase1_importar_carol(opcoes)
        return self._fase2_injetar_master(opcoes)

    # ── Fase 1: importar planilha Carol (síncrono) ───────────────────────────

    def _fase1_importar_carol(self, opcoes: dict) -> dict:
        import webview
        from engine.excel_parser import ExcelParser

        import compat as _main
        estado_sh = _main.estado_sh
        PROJECT_ROOT = _main.PROJECT_ROOT
        window = _main.window

        cfg = self._config.load()
        sessao = self.sessao()
        usuario = sessao.get("usuario", "desconhecido")
        host = os.environ.get("COMPUTERNAME", "unknown")

        data_inicio = opcoes.get("data_inicio")
        if not data_inicio:
            return {"ok": False, "erro": "Competência ausente."}

        tipos = ["Planilha Carol (*.xls;*.xlsx;*.xlsm)", "Todos os arquivos (*.*)"]
        result = window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=False, file_types=tipos
        )
        if not result or not result[0]:
            return {"ok": False, "cancelado": True}

        caminho = result[0]
        nome = os.path.basename(caminho)
        mes, ano = data_inicio[5:7], data_inicio[:4]
        alvos = [f"{mes}{ano}", f"{mes}.{ano}", f"{mes}/{ano}", f"{mes}-{ano}", f"{mes}_{ano}"]
        aviso = None
        if not any(a in nome for a in alvos):
            aviso = (f"O nome do arquivo ('{nome}') não contém a competência "
                     f"{mes}/{ano}. Confirme se é a Carol correta.")

        dados = ExcelParser.ler_planilha_carol(caminho)
        if dados is None:
            return {"ok": False, "erro": f"Falha ao ler a planilha em {caminho}."}

        total_empresas = len(dados)
        com_ativos = sum(1 for v in dados.values() if v.get("total_ativos", 0) > 0)
        competencia = data_inicio[:7]
        master_path = cfg.get("master_path") or os.path.join(PROJECT_ROOT, "CONTROLE DE HORAS DMF.xlsm")

        estado_sh.marcar(master_path, "dp", competencia, "carol_importada",
                         por=usuario, host=host,
                         total=total_empresas, com_ativos=com_ativos)
        estado_sh.remover(master_path, "dp", competencia, evento="lancado")
        self._config.save({
            f"dp_carol_path_{competencia}": caminho,
            f"dp_carol_importado_{competencia}": True,
            f"dp_carol_importado_em_{competencia}": datetime.now().strftime("%d/%m/%Y %H:%M"),
            f"dp_carol_total_{competencia}": total_empresas,
            f"dp_carol_com_ativos_{competencia}": com_ativos,
            f"dp_lancado_{competencia}": False,
        })

        return {
            "ok": True, "fase": 1,
            "caminho": caminho, "nome": nome,
            "total": total_empresas, "com_ativos": com_ativos,
            "sem_ativos": total_empresas - com_ativos,
            "aviso": aviso,
        }

    # ── Fase 2: injetar na master (threaded via ThreadRunner) ────────────────

    def _fase2_injetar_master(self, opcoes: dict) -> dict:
        from modulos.dp import extrair_e_preencher_dp
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

        data_inicio = opcoes.get("data_inicio")
        data_fim = opcoes.get("data_fim")
        if not data_inicio or not data_fim:
            return {"ok": False, "erro": "Competência ausente."}

        competencia = data_inicio[:7]
        caminho_carol = cfg.get(f"dp_carol_path_{competencia}")
        if not caminho_carol or not os.path.exists(caminho_carol):
            return {"ok": False, "erro": "Importe a planilha Carol antes (Passo 1)."}

        master_path = opcoes.get("master_path") or cfg.get("master_path") or os.path.join(
            PROJECT_ROOT, "CONTROLE DE HORAS DMF.xlsm"
        )
        if not os.path.exists(master_path):
            return {"ok": False, "erro": "Planilha master não encontrada."}

        ok_lock, info_lock = adquirir_lock(master_path, usuario, host, "DP")
        if not ok_lock:
            ocupante = info_lock.get("usuario", "?")
            return {"ok": False, "tipo": "lock", "erro": f"Master em uso por {ocupante}."}

        try:
            lockfile = os.path.join(os.path.dirname(master_path),
                                    "~$" + os.path.basename(master_path))
            if os.path.exists(lockfile):
                return {"ok": False, "tipo": "locked",
                        "erro": "Master aberta no Excel. Feche e tente de novo."}

            self.progress(15, "Conectando ao Domínio (se disponível)...")
            db.connect()

            self.progress(35, "Abrindo master...")
            writer = MasterWriter(master_path)
            if not writer.carregar():
                return {"ok": False, "erro": "Falha ao abrir master."}

            self.progress(60, f"Calculando e gravando DP ({competencia})...")
            ok = extrair_e_preencher_dp(
                writer, data_inicio, data_fim,
                fator_carga=cfg.get("dp_fator_carga", 0.33),
                overhead_fixo=cfg.get("dp_overhead_fixo", 1.5),
                tempo_minimo_minutos=cfg.get("dp_tempo_minimo", 5.0),
                consultoria_horas=cfg.get("dp_consultoria_horas", 1.5),
                tempo_fixo_apenas_socios=cfg.get("dp_apenas_socios", 1.0),
                caminho_carol=caminho_carol,
            )

            if cfg.get("governanca_gravar_zero", True):
                self.progress(82, "Limpando resíduos do mês anterior na col. Q...")
                writer.limpar_nao_tocadas([17])

            self.progress(90, "Recalculando totais...")
            writer.recalcular_totais()

            self.progress(95, "Salvando master...")
            salvo = writer.salvar()
            if not salvo and writer.ultimo_erro:
                return {"ok": False, **writer.ultimo_erro}

            if ok:
                estado_sh.marcar(master_path, "dp", competencia, "lancado",
                                 por=usuario, host=host)
                self._config.save({
                    f"dp_lancado_{competencia}": True,
                    f"dp_lancado_em_{competencia}": datetime.now().strftime("%d/%m/%Y %H:%M"),
                })

            self.progress(100, "Concluído.")
            return {"ok": bool(ok), "fase": 2, "competencia": competencia}

        except Exception as e:
            log.error(f"[DP] {traceback.format_exc()}")
            return {"ok": False, "erro": str(e)}
        finally:
            liberar_lock(master_path, usuario, host)
