"""
dmf_engine/modules/m_relatorio_rendimentos.py
Módulo inline (Padrão 0) — Relatório de Rendimentos Isentos.

Importa a lógica de negócio diretamente no processo da Central DMF.
Nenhum subprocess, nenhuma janela nova, nenhum SSO token.
"""
import os
import sys

from dmf_engine.modules.base import BaseModule, ModuleMeta


class RelatorioRendimentosModule(BaseModule):

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="relatorio_rendimentos",
            nome="Relatório de Rendimentos",
            desc="Extrai EFD-Reinf rendimentos isentos do Domínio e gera relatório Excel.",
            setor="CONTÁBIL",
            icon="ti-file-spreadsheet",
            color="#1E7C5A",
            papeis=["admin", "contabil"],
        )

    def execute(self, opcoes: dict) -> dict:
        import traceback
        import logging
        from pathlib import Path

        _svc = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "services", "relatorio_rendimentos")
        )
        if _svc not in sys.path:
            sys.path.insert(0, _svc)

        from modulos.relatorio_rendimentos_isentos import (
            conectar_dominio,
            extrair_dados,
            gerar_excel,
        )

        cfg = self._config.load()
        log = logging.getLogger("RelatorioRendimentos")

        try:
            competencia = opcoes.get("competencia")
            output_dir  = opcoes.get("output_dir") or str(Path.home() / "Downloads")
            codi_emp    = opcoes.get("codi_emp") or None

            if not competencia:
                return {"ok": False, "erro": "Competência não informada."}

            self.progress(10, "Conectando ao Domínio...")
            conn = conectar_dominio(
                dsn=cfg.get("db_dsn"),
                user=cfg.get("db_uid"),
                pwd=cfg.get("db_pwd"),
            )

            self.progress(35, "Extraindo dados...")
            dados = extrair_dados(conn, competencia, codi_emp)
            conn.close()

            if not dados:
                return {"ok": True, "aviso": "Nenhum registro encontrado para a competência.", "total": 0}

            self.progress(70, f"Gerando Excel ({len(dados)} registros)...")
            arquivo = gerar_excel(dados, competencia, Path(output_dir))

            self.progress(100, "Concluído.")
            return {"ok": True, "arquivo": str(arquivo), "total": len(dados)}

        except Exception as e:
            log.error(traceback.format_exc())
            return {"ok": False, "erro": str(e)}
