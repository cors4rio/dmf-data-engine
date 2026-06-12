"""
services.py — BuscarXMLService: orquestra os engines sem dependência de PyWebView.

Uso:
    service = BuscarXMLService(base_dir, on_event_cb)
    on_event_cb(evento: str, dados: dict) recebe todos os eventos de progresso,
    conclusão e log que o frontend consumiria via window._onCallback / window._onLog.
"""

import os
import sys
import json
import threading
import logging
import hashlib

# Garante que imports internos (bx_config.*, bx_engine.*) funcionem.
# Namespace exclusivo (bx_) evita colisão com os pacotes engine/ e config/
# da raiz da Central DMF, que carregam primeiro e ficam cacheados em sys.modules.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from bx_config.config_manager import ConfigManager
from bx_engine.daemon_manager import DaemonManager


class BuscarXMLService:
    """
    Interface pública do Buscador XML sem PyWebView.
    on_event_cb(evento, dados) substitui window.evaluate_js para todos os callbacks.
    """

    def __init__(self, base_dir: str, on_event_cb):
        self._base_dir     = base_dir
        self._on_event     = on_event_cb
        self._config       = ConfigManager(base_dir)
        self._daemons      = DaemonManager()
        self._running: dict = {}
        self._download_dir = os.path.join(base_dir, "downloads")
        os.makedirs(self._download_dir, exist_ok=True)
        self._setup_logging(base_dir)

    # ── logging ──────────────────────────────────────────────────────────────

    def _setup_logging(self, base_dir: str):
        """Configura file handler + handler de callback para o frontend."""
        root = logging.getLogger()
        if root.handlers:
            # já inicializado; apenas adiciona o handler de callback se necessário
            for h in root.handlers:
                if isinstance(h, _CallbackHandler):
                    h._cb = self._on_event
                    return
        else:
            root.setLevel(logging.INFO)
            logs_dir = os.path.join(base_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            fh = logging.FileHandler(os.path.join(logs_dir, "app.log"), encoding="utf-8")
            fh.setLevel(logging.INFO)
            fh.setFormatter(fmt)
            root.addHandler(fh)

        cb_handler = _CallbackHandler(self._on_event)
        cb_handler.setLevel(logging.INFO)
        root.addHandler(cb_handler)

    # ── callback helper ───────────────────────────────────────────────────────

    def _cb(self, evento: str, dados: dict = None):
        try:
            self._on_event(evento, dados or {})
        except Exception as e:
            logging.warning(f"_cb falhou ({evento}): {e}")

    # ── config com download_dir injetado ──────────────────────────────────────

    def _cfg(self) -> dict:
        """Carrega config e injeta _download_dir para que os daemons usem o caminho correto."""
        cfg = self._config.load()
        cfg["_download_dir"] = self._download_dir
        return cfg

    # ── NF-e Saída ────────────────────────────────────────────────────────────

    def executar_nfe(self, lojas: list, periodo: dict):
        if "nfe" in self._running:
            return {"ok": False, "msg": "NF-e já em execução"}
        stop = threading.Event()
        self._running["nfe"] = stop
        threading.Thread(target=self._run_nfe, args=(lojas, periodo, stop), daemon=True).start()
        return {"ok": True}

    def _run_nfe(self, lojas, periodo, stop):
        try:
            from bx_engine.nfe_disparo import executar_nfe
            cfg = self._cfg()

            progress_cb = lambda pct, msg, loja="": self._cb(
                "nfe_progress", {"pct": pct, "msg": msg, "loja": loja}
            )

            self._daemons.start(
                "emails", cfg,
                on_idle_cb=lambda: self._cb("daemon_idle_stop", {"nome": "emails"}),
            )
            self._daemons.start("arquivos", cfg)
            progress_cb(5, "Daemons 'emails' e 'arquivos' iniciados.", "")

            resultado = executar_nfe(
                lojas=lojas, periodo=periodo, stop_flag=stop, config=cfg,
                progress_cb=progress_cb,
            )

            if resultado.get("aguardando_email") and not stop.is_set():
                wait_res = self._aguardar_arquivos_nfe(
                    resultado.get("lojas_aguardando", []), periodo, cfg, stop, progress_cb,
                )
                resultado.update(wait_res)
                resultado["aguardando_email"] = False

            self._cb("nfe_done", {"ok": True, **resultado})
        except Exception as e:
            import traceback as _tb
            msg = str(e) or f"{type(e).__name__} (sem mensagem)"
            logging.error(f"NF-e falhou: {msg}\n{_tb.format_exc()}")
            self._cb("nfe_done", {"ok": False, "msg": msg})
        finally:
            self._running.pop("nfe", None)

    def _aguardar_arquivos_nfe(self, lojas_aguardando, periodo, cfg, stop, progress_cb) -> dict:
        import time as _t
        pasta_z     = cfg.get("paths", {}).get("nfe", r"Z:\#ROTINA AUTOMATICA NF\NFe")
        mes_ano     = periodo.get("mes_ano", "")
        timeout_min = int(cfg.get("nfe", {}).get("timeout_aguardo_min", 30))
        intervalo_s = int(cfg.get("nfe", {}).get("intervalo_check_s", 10))

        pendentes = {l["codigo"]: l for l in lojas_aguardando if l.get("codigo")}
        total = len(pendentes)
        if total == 0:
            progress_cb(100, "Nenhuma loja com NF-e no período — nada a aguardar.", "")
            return {"recebidos": 0, "pendentes": [], "timeout": False}

        deadline = _t.time() + timeout_min * 60
        progress_cb(55, f"Aguardando {total} ZIP(s) (timeout: {timeout_min}min)...", "")

        while pendentes and not stop.is_set():
            if _t.time() > deadline:
                pend_list = [l["apelido"] for l in pendentes.values()]
                progress_cb(None, f"⚠ TIMEOUT ({timeout_min}min): {len(pendentes)} loja(s) sem ZIP — {', '.join(pend_list)}", "")
                break

            try:
                if not self._daemons.get_status("emails").get("alive"):
                    self._daemons.start("emails", cfg, on_idle_cb=lambda: self._cb("daemon_idle_stop", {"nome": "emails"}))
                    progress_cb(None, "↻ Daemon 'emails' reiniciado.", "")
                if not self._daemons.get_status("arquivos").get("alive"):
                    self._daemons.start("arquivos", cfg)
                    progress_cb(None, "↻ Daemon 'arquivos' reiniciado.", "")
            except Exception as ex:
                logging.warning(f"Watchdog daemons falhou: {ex}")

            if os.path.isdir(pasta_z):
                for codigo, loja in list(pendentes.items()):
                    try:
                        for obj in os.listdir(pasta_z):
                            if obj.startswith(f"{codigo}-") and os.path.isdir(os.path.join(pasta_z, obj)):
                                alvo = os.path.join(pasta_z, obj, mes_ano, f"{mes_ano}.zip")
                                if os.path.isfile(alvo):
                                    recebidos = total - len(pendentes) + 1
                                    pct = 50 + int(50 * recebidos / total)
                                    progress_cb(pct, f"✓ Recebido: {loja['apelido']} ({recebidos}/{total})", loja["apelido"])
                                    del pendentes[codigo]
                                    break
                    except Exception as ex:
                        logging.warning(f"Erro ao checar {codigo}: {ex}")

            if pendentes:
                falta = ", ".join(l["apelido"] for l in pendentes.values())
                progress_cb(None, f"Aguardando {len(pendentes)}/{total}: {falta}", "")
                stop.wait(timeout=intervalo_s)

        recebidos   = total - len(pendentes)
        pend_apelidos = [l["apelido"] for l in pendentes.values()]
        timeout     = _t.time() > deadline and len(pendentes) > 0

        if not pendentes:
            progress_cb(100, f"✓ Concluído: {recebidos} ZIP(s) confirmado(s) na rede.", "")
        else:
            progress_cb(100, f"Parcial: {recebidos}/{total} recebidos. Pendentes: {', '.join(pend_apelidos)}", "")
        return {"recebidos": recebidos, "pendentes": pend_apelidos, "timeout": timeout}

    # ── NFCe ─────────────────────────────────────────────────────────────────

    def executar_nfce(self, lojas: list, periodo: dict):
        if "nfce" in self._running:
            return {"ok": False, "msg": "NFCe já em execução"}
        stop = threading.Event()
        self._running["nfce"] = stop
        threading.Thread(target=self._run_nfce, args=(lojas, periodo, stop), daemon=True).start()
        return {"ok": True}

    def _run_nfce(self, lojas, periodo, stop):
        try:
            from bx_engine.nfce import executar_nfce
            cfg = self._cfg()
            resultado = executar_nfce(
                lojas=lojas, periodo=periodo, stop_flag=stop, config=cfg,
                progress_cb=lambda pct, msg, loja="": self._cb("nfce_progress", {"pct": pct, "msg": msg, "loja": loja}),
            )
            self._cb("nfce_done", {"ok": True, **resultado})
        except Exception as e:
            import traceback as _tb
            msg = str(e) or f"{type(e).__name__} (sem mensagem)"
            logging.error(f"NFCe falhou: {msg}\n{_tb.format_exc()}")
            self._cb("nfce_done", {"ok": False, "msg": msg})
        finally:
            self._running.pop("nfce", None)

    # ── SPED ──────────────────────────────────────────────────────────────────

    def executar_sped(self, lojas: list, periodo: dict):
        if "sped" in self._running:
            return {"ok": False, "msg": "SPED já em execução"}
        stop = threading.Event()
        self._running["sped"] = stop
        threading.Thread(target=self._run_sped, args=(lojas, periodo, stop), daemon=True).start()
        return {"ok": True}

    def _run_sped(self, lojas, periodo, stop):
        try:
            from bx_engine.sped import executar_sped
            cfg = self._cfg()
            resultado = executar_sped(
                lojas=lojas, periodo=periodo, stop_flag=stop, config=cfg,
                progress_cb=lambda pct, msg, loja="": self._cb("sped_progress", {"pct": pct, "msg": msg, "loja": loja}),
            )
            self._cb("sped_done", {"ok": True, **resultado})
        except Exception as e:
            import traceback as _tb
            msg = str(e) or f"{type(e).__name__} (sem mensagem)"
            logging.error(f"SPED falhou: {msg}\n{_tb.format_exc()}")
            self._cb("sped_done", {"ok": False, "msg": msg})
        finally:
            self._running.pop("sped", None)

    # ── TOKAI ─────────────────────────────────────────────────────────────────

    def listar_clientes_tokai(self) -> list:
        try:
            from bx_engine.tokai_adapter import listar_clientes_tokai
            return listar_clientes_tokai()
        except Exception as e:
            logging.error(f"listar_clientes_tokai falhou: {e}")
            return []

    def executar_tokai(self, clientes: list = None, periodo: dict = None):
        if "tokai" in self._running:
            return {"ok": False, "msg": "TOKAI já em execução"}
        stop = threading.Event()
        self._running["tokai"] = stop
        threading.Thread(target=self._run_tokai, args=(stop, clientes, periodo), daemon=True).start()
        return {"ok": True}

    def _run_tokai(self, stop, clientes=None, periodo=None):
        try:
            from bx_engine.tokai_adapter import executar_tokai
            cfg = self._cfg()
            resultado = executar_tokai(
                config=cfg, stop_flag=stop,
                progress_cb=lambda pct, msg: self._cb("tokai_progress", {"pct": pct, "msg": msg}),
                clientes=clientes, periodo=periodo,
            )
            self._cb("tokai_done", {"ok": True, **resultado})
        except Exception as e:
            logging.error(f"TOKAI falhou: {e}")
            self._cb("tokai_done", {"ok": False, "msg": str(e)})
        finally:
            self._running.pop("tokai", None)

    def compactar_tokai(self, clientes: list = None, periodo: dict = None):
        if "tokai-zip" in self._running:
            return {"ok": False, "msg": "Compactação TOKAI já em execução"}
        if "tokai" in self._running:
            return {"ok": False, "msg": "Download TOKAI em execução — aguarde concluir antes de compactar"}
        stop = threading.Event()
        self._running["tokai-zip"] = stop
        threading.Thread(target=self._run_tokai_zip, args=(stop, clientes, periodo), daemon=True).start()
        return {"ok": True}

    def _run_tokai_zip(self, stop, clientes=None, periodo=None):
        try:
            from bx_engine.tokai_adapter import compactar_tokai
            cfg = self._cfg()
            resultado = compactar_tokai(
                config=cfg, stop_flag=stop,
                progress_cb=lambda pct, msg: self._cb("tokai_zip_progress", {"pct": pct, "msg": msg}),
                clientes=clientes, periodo=periodo,
            )
            self._cb("tokai_zip_done", {"ok": True, **resultado})
        except Exception as e:
            logging.error(f"Compactação TOKAI falhou: {e}")
            self._cb("tokai_zip_done", {"ok": False, "msg": str(e)})
        finally:
            self._running.pop("tokai-zip", None)

    # ── Controle de execução ──────────────────────────────────────────────────

    def cancelar(self, modulo: str):
        stop = self._running.get(modulo)
        if stop:
            stop.set()
            # Encerra IMEDIATAMENTE: mata o navegador (Playwright) e o 7-Zip em
            # andamento. Sem isso, o stop_flag é cooperativo e a thread só para no
            # próximo checkpoint — durante um download/extração longos ela vira
            # "fantasma" rodando por minutos. Cirúrgico: só a nossa árvore de processos.
            try:
                from bx_engine.bx_playwright_compat import matar_processos_filhos
                matar_processos_filhos()
            except Exception as e:
                logging.warning(f"Falha ao encerrar processos no cancelamento: {e}")
            return {"ok": True, "msg": f"{modulo} cancelado."}
        return {"ok": False, "msg": f"{modulo} não está em execução"}

    def get_status(self):
        return {"executando": list(self._running.keys()), "daemons": self._daemons.get_all_status()}

    # ── Daemons ───────────────────────────────────────────────────────────────

    def start_daemon(self, nome: str):
        cfg = self._cfg()
        idle_cb = (lambda: self._cb("daemon_idle_stop", {"nome": nome})) if nome == "emails" else None
        return self._daemons.start(nome, cfg, on_idle_cb=idle_cb)

    def stop_daemon(self, nome: str):
        return self._daemons.stop(nome)

    def restart_daemon(self, nome: str):
        self._daemons.stop(nome)
        return self._daemons.start(nome, self._cfg())

    def get_status_daemons(self):
        return self._daemons.get_all_status()

    # ── Configuração ──────────────────────────────────────────────────────────

    def carregar_config(self):
        return self._config.load()

    def salvar_config(self, dados: dict):
        existente = self._config.load()
        for chave in ("admin",):
            if chave in existente and chave not in dados:
                dados[chave] = existente[chave]
            elif chave in existente and isinstance(existente[chave], dict):
                for sub in existente[chave]:
                    dados.setdefault(chave, {})[sub] = dados.get(chave, {}).get(sub) or existente[chave][sub]
        return self._config.save(dados)

    def verificar_senha_adm(self, senha: str) -> dict:
        cfg = self._config.load()
        hash_salvo = cfg.get("admin", {}).get("senha_hash", "")
        if not hash_salvo:
            return {"ok": True, "sem_senha": True}
        return {"ok": hashlib.sha256(senha.encode()).hexdigest() == hash_salvo, "sem_senha": False}

    def alterar_senha_adm(self, senha_atual: str, nova_senha: str) -> dict:
        cfg = self._config.load()
        hash_salvo = cfg.get("admin", {}).get("senha_hash", "")
        if hash_salvo and hashlib.sha256(senha_atual.encode()).hexdigest() != hash_salvo:
            return {"ok": False, "msg": "Senha atual incorreta"}
        cfg.setdefault("admin", {})["senha_hash"] = hashlib.sha256(nova_senha.encode()).hexdigest() if nova_senha else ""
        self._config.save(cfg)
        return {"ok": True, "msg": "Senha alterada com sucesso"}

    def testar_conexao_erp(self):
        try:
            from bx_engine.nfe_disparo import testar_login
            return testar_login(self._config.load())
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def verificar_disco_z(self):
        cfg = self._config.load()
        base_z = cfg.get("paths", {}).get("base_z", r"Z:\#ROTINA AUTOMATICA NF")
        drive, _ = os.path.splitdrive(base_z)
        drive_root = (drive + os.sep) if drive else os.sep
        return {"ok": os.path.isdir(drive_root), "path": base_z, "drive": drive_root}

    # ── Deletar competência (ação global do módulo, por grupo) ────────────────

    def _pastas_base_por_grupo(self, grupo: str, cfg: dict) -> list:
        """
        Retorna as pastas-raiz onde ficam as subpastas {loja}/{MMAAAA} de cada
        grupo. AGROMIX/ATACADÃO → NF-e, NFCe, SPED. TOKAI → network_path.
        Cada item: (rotulo, caminho_raiz).
        """
        paths = cfg.get("paths", {})
        if grupo == "tokai":
            net = cfg.get("tokai", {}).get("network_path", "").strip() \
                or os.environ.get("NETWORK_DRIVE_Z", "").strip().strip('"')
            return [("TOKAI", net)] if net else []
        # agromix/atacadão
        return [
            ("NF-e", paths.get("nfe",  r"Z:\#ROTINA AUTOMATICA NF\NFe")),
            ("NFCe", paths.get("nfce", r"Z:\#ROTINA AUTOMATICA NF\NFCe")),
            ("SPED", paths.get("sped", r"Z:\#ROTINA AUTOMATICA NF\SPED")),
        ]

    def _coletar_pastas_competencia(self, grupo: str, competencia: str) -> list:
        """
        Varre cada pasta-raiz do grupo e localiza as subpastas {loja}/{competencia}.
        competencia = 'MMAAAA' (ex: '052026'). Retorna lista de dicts:
        {modulo, loja, caminho, arquivos}.
        """
        cfg = self._cfg()
        encontrados = []
        for rotulo, raiz in self._pastas_base_por_grupo(grupo, cfg):
            if not raiz or not os.path.isdir(raiz):
                continue
            for loja in os.listdir(raiz):
                pasta_loja = os.path.join(raiz, loja)
                if not os.path.isdir(pasta_loja):
                    continue
                alvo = os.path.join(pasta_loja, competencia)
                if os.path.isdir(alvo):
                    try:
                        n = sum(len(fs) for _, _, fs in os.walk(alvo))
                    except Exception:
                        n = 0
                    encontrados.append({
                        "modulo": rotulo, "loja": loja,
                        "caminho": alvo, "arquivos": n,
                    })
        return encontrados

    def previa_deletar_competencia(self, grupo: str, competencia: str) -> dict:
        """Dry-run: conta o que seria apagado, sem remover nada."""
        if not competencia or len(competencia) != 6 or not competencia.isdigit():
            return {"ok": False, "msg": "Competência inválida (esperado MMAAAA)."}
        try:
            itens = self._coletar_pastas_competencia(grupo, competencia)
            total_arq = sum(i["arquivos"] for i in itens)
            return {
                "ok": True, "grupo": grupo, "competencia": competencia,
                "pastas": len(itens), "arquivos": total_arq, "itens": itens,
            }
        except Exception as e:
            logging.error(f"Prévia deletar competência falhou: {e}")
            return {"ok": False, "msg": str(e)}

    def deletar_competencia(self, grupo: str, competencia: str,
                            confirmacao: str = "", caminhos: list = None) -> dict:
        """
        Apaga as subpastas {loja}/{competencia} do grupo atual.
        Exige confirmacao == competencia para evitar engano. Usa a lixeira
        (send2trash) quando disponível; caso contrário shutil.rmtree.

        caminhos: lista opcional de caminhos específicos a apagar (empresas
        escolhidas pelo usuário). None/vazio = todas as do grupo. Como trava
        de segurança, só caminhos presentes na varredura do grupo/competência
        são aceitos — a UI nunca apaga algo fora desse escopo.
        """
        if not competencia or len(competencia) != 6 or not competencia.isdigit():
            return {"ok": False, "msg": "Competência inválida (esperado MMAAAA)."}
        if confirmacao != competencia:
            return {"ok": False, "msg": "Confirmação não confere com a competência."}
        try:
            itens = self._coletar_pastas_competencia(grupo, competencia)
            if not itens:
                return {"ok": True, "removidas": 0, "msg": "Nenhuma pasta encontrada para esta competência."}

            # Filtra pelas empresas escolhidas (se houver). Trava: só aceita
            # caminhos que a varredura realmente encontrou.
            if caminhos:
                permitidos = {os.path.normpath(c) for c in caminhos}
                itens = [it for it in itens if os.path.normpath(it["caminho"]) in permitidos]
                if not itens:
                    return {"ok": False, "msg": "Nenhuma empresa válida selecionada para exclusão."}

            try:
                from send2trash import send2trash
                _remover = lambda p: send2trash(p)
                modo = "lixeira"
            except Exception:
                import shutil
                _remover = lambda p: shutil.rmtree(p, ignore_errors=False)
                modo = "definitivo"

            removidas, erros = 0, []
            for it in itens:
                try:
                    _remover(it["caminho"])
                    removidas += 1
                    logging.info(f"[DELETE] {modo}: {it['caminho']}")
                except Exception as e:
                    erros.append(f"{it['modulo']}/{it['loja']}: {e}")
                    logging.error(f"[DELETE] falhou {it['caminho']}: {e}")

            self._cb("competencia_deletada", {
                "grupo": grupo, "competencia": competencia,
                "removidas": removidas, "erros": len(erros), "modo": modo,
            })
            return {
                "ok": len(erros) == 0, "removidas": removidas,
                "total": len(itens), "erros": erros, "modo": modo,
            }
        except Exception as e:
            logging.error(f"Deletar competência falhou: {e}")
            return {"ok": False, "msg": str(e)}

    def mapear_disco_z(self):
        import subprocess
        unc = r"\\srvdmf\CELULAS 2013"
        try:
            subprocess.run(["net", "use", "Z:", "/delete", "/yes"], capture_output=True, timeout=10)
        except Exception:
            pass
        try:
            r = subprocess.run(
                ["net", "use", "Z:", unc, "/persistent:yes"],
                capture_output=True, text=True, encoding="cp850", errors="replace", timeout=30,
            )
            if r.returncode == 0 or os.path.isdir("Z:\\"):
                return {"ok": True, "msg": f"Drive Z: mapeado para {unc}"}
            return {"ok": False, "msg": (r.stdout + r.stderr).strip() or "Falha ao mapear Z:"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "msg": "Tempo esgotado ao mapear drive Z:"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ── Dados e logs ──────────────────────────────────────────────────────────

    def listar_lojas(self):
        try:
            from bx_config.lojas import LOJAS_CADASTRO
        except ImportError as e:
            # Não engolir silenciosamente: este import falhar no exe (bx_config fora
            # do _internal) foi a causa da "lista de lojas vazia". Logar sempre.
            logging.error(f"[BX] listar_lojas: import de bx_config.lojas falhou — "
                          f"lojas não serão exibidas. Detalhe: {e}")
            return []
        resultado = []
        for codigo, loja in LOJAS_CADASTRO.items():
            apelido = loja.get("apelido", "")
            grupo = "ATACADAO" if "ATACAD" in apelido.upper() else "AGROMIX"
            resultado.append({
                "codigo":      codigo,
                "apelido":     apelido,
                "nome":        loja.get("nome", ""),
                "cnpj":        loja.get("cnpj", ""),
                "grupo":       grupo,
                "id_bluesoft": loja.get("id_bluesoft"),
                "id_nfce":     loja.get("id_nfce"),
                "tem_nfe":     loja.get("id_bluesoft") is not None,
                "tem_nfce":    loja.get("id_nfce") is not None,
                "tem_sped":    loja.get("id_bluesoft") is not None,
            })
        return resultado

    def get_logs(self, modulo: str = "", limite: int = 200):
        log_file = os.path.join(self._base_dir, "logs", "app.log")
        if not os.path.exists(log_file):
            return []
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                linhas = f.readlines()
            if modulo:
                linhas = [l for l in linhas if modulo.upper() in l.upper()]
            result = []
            for l in linhas[-limite:]:
                parts = l.rstrip().split(" - ", 3)
                level = parts[2] if len(parts) >= 3 else "INFO"
                msg   = parts[3] if len(parts) >= 4 else l.rstrip()
                result.append({"level": level, "msg": msg})
            return result
        except Exception:
            return []

    def get_historico(self):
        csv_file = os.path.join(self._base_dir, "relatorio_execucao.csv")
        if not os.path.exists(csv_file):
            return []
        try:
            with open(csv_file, "r", encoding="utf-8", errors="replace") as f:
                return [l.rstrip() for l in f.readlines()[-100:]]
        except Exception:
            return []

    def limpar_logs(self):
        log_file = os.path.join(self._base_dir, "logs", "app.log")
        try:
            open(log_file, "w").close()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

# ── Handler interno de logging → callback ─────────────────────────────────────

class _CallbackHandler(logging.Handler):
    def __init__(self, cb):
        super().__init__()
        self._cb = cb

    def emit(self, record):
        try:
            self._cb("_log", {
                "time":   self.formatTime(record, "%H:%M:%S"),
                "level":  record.levelname,
                "msg":    record.getMessage(),
                "modulo": record.name,
            })
        except Exception:
            pass
