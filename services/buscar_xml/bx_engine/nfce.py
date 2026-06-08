"""
engine/nfce.py
Extração de NFCe via API interna Bluesoft (porta 9091).
"""

import os
import re
import logging
import threading
import zipfile
import unicodedata
import shutil
import requests
from playwright.sync_api import sync_playwright

log = logging.getLogger("NFCe")

_CHUNK_SIZE   = 64 * 1024   # 64 KB por chunk no download streaming
_LOG_INTERVAL = 500         # log de progresso a cada N arquivos


def _remover_acentos(texto: str) -> str:
    try:
        nfkd = unicodedata.normalize("NFKD", texto)
        s    = "".join(c for c in nfkd if not unicodedata.combining(c))
        return re.sub(r"[^a-zA-Z0-9\-\_\ ]", "", s)
    except Exception:
        return texto


# ── Login ─────────────────────────────────────────────────────────────────────

def _capturar_cookies(config: dict, progress_cb) -> requests.Session:
    url_login = config.get("nfce", {}).get("url_base", "http://10.111.246.241:9091/nfx/")
    usuario   = config.get("nfce", {}).get("usuario", "198")
    senha     = config.get("nfce", {}).get("senha",   "123456")

    progress_cb(8, "Autenticando no portal NFCe...", "")
    cookies_dict = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx     = browser.new_context()
        page    = ctx.new_page()
        page.set_default_timeout(30_000)
        try:
            page.goto(url_login)
            page.locator("#user").fill(usuario)
            page.locator("#password").fill(senha)
            page.locator("#btnLogin").click()
            page.wait_for_url("**/nfx/**", timeout=30_000)
            page.wait_for_timeout(2_000)
            for c in ctx.cookies():
                cookies_dict[c["name"]] = c["value"]
        except Exception as e:
            log.error(f"NFCe login falhou: {e}")
        finally:
            browser.close()

    if not cookies_dict:
        raise Exception("Não foi possível capturar cookies do portal NFCe.")

    sessao = requests.Session()
    requests.utils.add_dict_to_cookiejar(sessao.cookies, cookies_dict)
    progress_cb(15, f"Login NFCe OK — {len(cookies_dict)} cookies", "")
    return sessao


# ── Consulta de chaves ────────────────────────────────────────────────────────

def _consultar_chaves(sessao, loja_id, data_inicio, data_fim,
                      url_consulta, headers) -> tuple:
    """Retorna (ok, chaves_list | msg_erro)."""
    payload = {
        "pdv": "", "data": data_inicio, "dataf": data_fim,
        "status": "0", "cpf": "", "cupom": "", "nnf": "", "key": "",
        "checkbox": True, "loja": str(loja_id),
    }
    try:
        r = sessao.post(url_consulta, json=payload, headers=headers, timeout=60)
    except Exception as e:
        return False, f"Erro na consulta: {e}"

    if r.status_code != 200:
        return False, f"HTTP {r.status_code} na consulta"

    chaves = []
    try:
        jd = r.json()
        if "data" in jd and isinstance(jd["data"], list):
            for item in jd["data"]:
                if isinstance(item, dict) and "key" in item:
                    chaves.append(item["key"])
                elif isinstance(item, list):
                    for field in item:
                        m = re.search(r"\b\d{44}\b", str(field))
                        if m:
                            chaves.append(m.group(0))
                            break
    except Exception:
        pass
    if not chaves:
        chaves = list({x for x in re.findall(r"\b\d{44}\b", r.text)})

    return True, chaves


# ── Resolução de pasta da loja ────────────────────────────────────────────────

def _resolver_pasta_loja(pasta_loja: str, pasta_final_nfce: str) -> str:
    """
    Retorna o NOME DA SUBPASTA (não caminho completo) para a loja dentro de
    pasta_final_nfce.  Usa pasta existente de maior conteúdo se disponível,
    senão usa pasta_loja com acentos removidos.
    """
    pasta_sem_acento = _remover_acentos(pasta_loja)
    codigo_loja      = pasta_sem_acento.split("-")[0].strip()
    pasta_resultado  = pasta_sem_acento

    if codigo_loja and os.path.isdir(pasta_final_nfce):
        try:
            candidatos = [
                (len(os.listdir(os.path.join(pasta_final_nfce, obj))), obj)
                for obj in os.listdir(pasta_final_nfce)
                if obj.startswith(f"{codigo_loja}-")
                and os.path.isdir(os.path.join(pasta_final_nfce, obj))
            ]
            if candidatos:
                pasta_resultado = sorted(candidatos, reverse=True)[0][1]
                log.info(f"NFCe: pasta existente '{pasta_resultado}' (código={codigo_loja})")
        except Exception as e:
            log.warning(f"NFCe: erro ao varrer pastas para código '{codigo_loja}': {e}")

    return pasta_resultado


# ── FASE 1-A: Download streaming para disco ───────────────────────────────────

def _baixar_para_disco(sessao, chaves, caminho_dl_tmp,
                       url_download, headers, stop_flag) -> tuple:
    """
    Faz download do ZIP do servidor em chunks para arquivo temporário em disco.
    Retorna (ok, msg).
    """
    payload_dl     = {"tipo": "xml", "chaves": ",".join(chaves)}
    bytes_baixados = 0

    try:
        with sessao.post(url_download, json=payload_dl, headers=headers,
                         stream=True, timeout=600) as r_dl:
            if r_dl.status_code != 200:
                return False, f"HTTP {r_dl.status_code} no download"

            ct = r_dl.headers.get("Content-Type", "")
            if "text" in ct.lower() or "json" in ct.lower():
                return False, f"Resposta inesperada do servidor: {ct}"

            with open(caminho_dl_tmp, "wb") as f:
                for chunk in r_dl.iter_content(chunk_size=_CHUNK_SIZE):
                    if stop_flag and stop_flag.is_set():
                        return False, "Cancelado durante download"
                    if chunk:
                        f.write(chunk)
                        bytes_baixados += len(chunk)
                        mb_atual = bytes_baixados / (1024 * 1024)
                        if bytes_baixados % (10 * 1024 * 1024) < _CHUNK_SIZE:
                            log.info(f"NFCe: download em andamento — {mb_atual:.0f} MB")
    except Exception as e:
        return False, f"Erro no download: {e}"

    mb = bytes_baixados / (1024 * 1024)
    log.info(f"NFCe: download concluído — {mb:.1f} MB ({bytes_baixados:,} bytes)")
    return True, f"{mb:.1f} MB"


# ── FASE 1-B: Extração completa para pasta temporária em disco ────────────────

def _extrair_para_pasta(caminho_zip_servidor, dir_extracao, stop_flag) -> tuple:
    """
    Extrai TODOS os XMLs do ZIP do servidor para dir_extracao com nomes planos
    (sem subpastas).  Aguarda conclusão total antes de retornar.
    Retorna (ok, lista_nomes_extraídos, msg).
    """
    try:
        with zipfile.ZipFile(caminho_zip_servidor, "r") as zf:
            corrompido = zf.testzip()
            if corrompido:
                return False, [], f"ZIP do servidor corrompido: {corrompido}"

            todas_entradas = zf.infolist()
            entradas_xml   = [
                info for info in todas_entradas
                if not info.filename.endswith("/")
                and info.filename.lower().endswith(".xml")
            ]
            total = len(entradas_xml)
            log.info(
                f"NFCe: ZIP servidor — {total} XMLs "
                f"(total entradas={len(todas_entradas)}) — iniciando extração..."
            )

            os.makedirs(dir_extracao, exist_ok=True)

            extraidos: list = []
            seen:       set  = set()
            erros_ext        = 0

            for idx, info in enumerate(entradas_xml):
                if stop_flag and stop_flag.is_set():
                    return False, extraidos, "Cancelado durante extração"

                # Achata caminho: pega só o nome do arquivo
                flat = os.path.basename(info.filename) or info.filename.replace("/", "_")
                orig, counter = flat, 1
                while flat in seen:
                    base, ext = os.path.splitext(orig)
                    flat = f"{base}_{counter}{ext}"
                    counter += 1
                seen.add(flat)

                dest = os.path.join(dir_extracao, flat)
                try:
                    data = zf.read(info.filename)
                    with open(dest, "wb") as f:
                        f.write(data)
                    extraidos.append(flat)
                except Exception as e:
                    log.warning(f"NFCe: falha ao extrair '{info.filename}': {e}")
                    erros_ext += 1

                if (idx + 1) % _LOG_INTERVAL == 0:
                    log.info(
                        f"NFCe: extraindo... {idx + 1}/{total} "
                        f"({len(extraidos)} OK, {erros_ext} erros)"
                    )

    except zipfile.BadZipFile as e:
        return False, [], f"Não é um ZIP válido: {e}"
    except Exception as e:
        return False, [], f"Erro na extração: {e}"

    log.info(
        f"NFCe: EXTRAÇÃO CONCLUÍDA — {len(extraidos)}/{total} XMLs "
        f"em {dir_extracao} ({erros_ext} erros)"
    )
    return True, extraidos, f"{len(extraidos)} XMLs extraídos"


# ── FASE 2: Compactação em ZIP único ──────────────────────────────────────────

def _compactar_para_zip(dir_extracao, lista_arquivos,
                        caminho_zip_final, stop_flag) -> tuple:
    """
    Lê os arquivos de dir_extracao e os compacta em um único ZIP.
    Usa arquivo .tmp e rename atômico.  Valida o ZIP ao final.
    Retorna (ok, msg).
    """
    caminho_tmp = caminho_zip_final + ".tmp"
    total       = len(lista_arquivos)
    log.info(f"NFCe: iniciando compactação de {total} XMLs → {os.path.basename(caminho_zip_final)}")

    try:
        with zipfile.ZipFile(caminho_tmp, "w",
                             zipfile.ZIP_DEFLATED, allowZip64=True) as zf_out:
            for idx, nome in enumerate(lista_arquivos):
                if stop_flag and stop_flag.is_set():
                    raise Exception("Cancelado durante compactação")
                src = os.path.join(dir_extracao, nome)
                if os.path.isfile(src):
                    zf_out.write(src, nome)
                else:
                    log.warning(f"NFCe: arquivo não encontrado para compactar: '{src}'")
                if (idx + 1) % _LOG_INTERVAL == 0:
                    log.info(f"NFCe: compactando... {idx + 1}/{total}")

        # Rename atômico
        if os.path.exists(caminho_zip_final):
            os.remove(caminho_zip_final)
        os.rename(caminho_tmp, caminho_zip_final)

        # Validação do ZIP final
        with zipfile.ZipFile(caminho_zip_final, "r") as zf_val:
            corrompido = zf_val.testzip()
            if corrompido:
                return False, f"ZIP final corrompido após rename: {corrompido}"
            qtd_final = len([n for n in zf_val.namelist() if n.lower().endswith(".xml")])

        log.info(
            f"NFCe: ZIP VALIDADO — {qtd_final} XMLs em "
            f"{os.path.basename(caminho_zip_final)}"
        )
        return True, f"{qtd_final} XMLs"

    except Exception as e:
        _limpar_arquivo(caminho_tmp)
        return False, f"Erro na compactação: {e}"


# ── Helpers de limpeza ────────────────────────────────────────────────────────

def _limpar_arquivo(caminho: str):
    if caminho and os.path.isfile(caminho):
        try:
            os.remove(caminho)
        except Exception:
            pass


def _limpar_dir(diretorio: str):
    if diretorio and os.path.isdir(diretorio):
        try:
            shutil.rmtree(diretorio)
        except Exception as e:
            log.warning(f"NFCe: falha ao remover dir temp '{diretorio}': {e}")


# ── Orquestrador por loja ─────────────────────────────────────────────────────

def _processar_loja(sessao: requests.Session, loja_id: str, pasta_loja: str,
                    data_inicio: str, data_fim: str, mes_ano: str,
                    pasta_final_nfce: str, url_consulta: str, url_download: str,
                    stop_flag: threading.Event = None) -> tuple:
    """
    Processa uma loja em duas fases explícitas e sequenciais:
      FASE 1: Download (streaming → disco) + Extração completa → _extract/
      FASE 2: Compactação _extract/ → ZIP único + validação + limpeza
    Retorna (ok, msg).
    """
    headers = {
        "Accept":           "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin":           url_consulta.rsplit("/nfx/", 1)[0],
        "Referer":          url_consulta.rsplit("/data/", 1)[0] + "/main.php",
    }

    # ── Consulta ──────────────────────────────────────────────────────────────
    ok, resultado = _consultar_chaves(
        sessao, loja_id, data_inicio, data_fim, url_consulta, headers
    )
    if not ok:
        return False, resultado
    chaves: list = resultado
    if not chaves:
        return True, "Sem NFCe no período"
    log.info(f"NFCe {loja_id}: {len(chaves)} chaves encontradas")

    # ── Resolução do caminho de destino ───────────────────────────────────────
    pasta_sub     = _resolver_pasta_loja(pasta_loja, pasta_final_nfce)
    caminho_pasta = os.path.normpath(
        os.path.join(pasta_final_nfce, pasta_sub, mes_ano)
    )

    # Salvaguarda: garante que o caminho calculado não escapou do diretório base
    nfce_norm = os.path.normpath(pasta_final_nfce)
    if not (caminho_pasta == nfce_norm or
            caminho_pasta.startswith(nfce_norm + os.sep)):
        msg = (
            f"ERRO DE CAMINHO: '{caminho_pasta}' está fora de '{nfce_norm}'. "
            f"pasta_loja='{pasta_loja}' pasta_sub='{pasta_sub}' mes_ano='{mes_ano}'"
        )
        log.error(msg)
        return False, msg

    nome_zip      = f"{mes_ano}.zip"
    caminho_zip   = os.path.join(caminho_pasta, nome_zip)
    caminho_dl    = os.path.join(caminho_pasta, "_dl.tmp")
    dir_extracao  = os.path.join(caminho_pasta, "_extract")

    log.info(
        f"NFCe {loja_id}: base='{pasta_final_nfce}' | "
        f"sub='{pasta_sub}' | comp='{mes_ano}' | "
        f"destino='{caminho_pasta}'"
    )

    # ── Cria pasta de destino ─────────────────────────────────────────────────
    try:
        os.makedirs(caminho_pasta, exist_ok=True)
    except Exception as e:
        return False, f"Não foi possível criar '{caminho_pasta}': {e}"

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 1-A  Download streaming para _dl.tmp
    # ─────────────────────────────────────────────────────────────────────────
    log.info(f"NFCe {loja_id}: [FASE 1-A] download de {len(chaves)} chaves...")
    ok, msg = _baixar_para_disco(
        sessao, chaves, caminho_dl, url_download, headers, stop_flag
    )
    if not ok:
        _limpar_arquivo(caminho_dl)
        return False, msg

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 1-B  Extração COMPLETA do ZIP servidor → _extract/
    #           Aguarda conclusão total antes de avançar
    # ─────────────────────────────────────────────────────────────────────────
    log.info(f"NFCe {loja_id}: [FASE 1-B] extraindo XMLs — aguardando conclusão total...")
    ok, lista_xml, msg_ext = _extrair_para_pasta(caminho_dl, dir_extracao, stop_flag)
    _limpar_arquivo(caminho_dl)  # download já não é necessário

    if not ok:
        _limpar_dir(dir_extracao)
        return False, msg_ext

    if not lista_xml:
        _limpar_dir(dir_extracao)
        return True, "Sem XMLs no período"

    log.info(
        f"NFCe {loja_id}: [FASE 1-B] CONCLUÍDA — "
        f"{len(lista_xml)} XMLs prontos em {dir_extracao}"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # FASE 2  Compactação em ZIP único + validação
    # ─────────────────────────────────────────────────────────────────────────
    log.info(f"NFCe {loja_id}: [FASE 2] compactando {len(lista_xml)} XMLs → {nome_zip}...")
    ok, msg_zip = _compactar_para_zip(dir_extracao, lista_xml, caminho_zip, stop_flag)
    _limpar_dir(dir_extracao)  # sempre limpa independente do resultado

    if not ok:
        return False, msg_zip

    log.info(f"NFCe {loja_id}: [CONCLUÍDO] {msg_zip} em {caminho_zip}")
    return True, f"{msg_zip} salvo em {nome_zip}"


# ── Ponto de entrada ──────────────────────────────────────────────────────────

def executar_nfce(lojas: list, periodo: dict, stop_flag: threading.Event,
                  progress_cb, config: dict = None) -> dict:
    """
    lojas:  [{"codigo","apelido","id_nfce"}, ...]
    periodo: {"data_inicio":"YYYY-MM-DD","data_fim":"YYYY-MM-DD","mes_ano":"MMYYYY"}
    """
    config       = config or {}
    nfce_cfg     = config.get("nfce", {})
    url_base     = nfce_cfg.get("url_base", "http://10.111.246.241:9091/nfx/")
    url_consulta = url_base.rstrip("/") + "/data/consulta.php"
    url_download = url_base.rstrip("/") + "/data/download.php"
    pasta_final  = config.get("paths", {}).get("nfce", r"Z:\#ROTINA AUTOMATICA NF\NFCe")

    log.info(f"NFCe: pasta destino = '{pasta_final}'")

    # Valida acesso ao drive antes de iniciar o login (falha rápida)
    drive, _   = os.path.splitdrive(pasta_final)
    drive_root = (drive + os.sep) if drive else os.sep
    if not os.path.isdir(drive_root):
        msg = (
            f"Drive de rede inacessível: {drive_root}. "
            f"Configure em Configurações > Caminhos de Rede"
        )
        log.error(msg)
        progress_cb(100, msg, "")
        return {"sucessos": 0, "erros": len(lojas), "msg": msg}

    sessao = _capturar_cookies(config, progress_cb)

    total = len(lojas)
    suc = err = 0

    for i, loja in enumerate(lojas):
        if stop_flag.is_set():
            progress_cb(None, "Cancelado pelo usuário.", "")
            break

        id_nfce = loja.get("id_nfce")
        nome    = loja.get("apelido", loja.get("codigo", "?"))
        pasta   = f"{loja.get('codigo', '?')}-{nome}"

        if not id_nfce:
            log.info(f"NFCe: loja '{nome}' não tem id_nfce — ignorada.")
            continue

        pct = 15 + int((i / total) * 80)
        progress_cb(pct, f"NFCe: processando {nome}...", nome)
        log.info(f"NFCe: === iniciando {nome} (id={id_nfce}) ===")

        try:
            ok, msg = _processar_loja(
                sessao, id_nfce, pasta,
                periodo["data_inicio"], periodo["data_fim"], periodo["mes_ano"],
                pasta_final, url_consulta, url_download,
                stop_flag=stop_flag,
            )
            if ok:
                suc += 1
                log.info(f"NFCe OK: {nome} — {msg}")
            else:
                err += 1
                log.warning(f"NFCe ERRO: {nome} — {msg}")
            progress_cb(pct, f"{nome}: {msg}", nome)
        except Exception as e:
            err += 1
            log.error(f"NFCe FALHA: {nome} — {e}")

        if stop_flag.wait(timeout=1):
            progress_cb(None, "Cancelado pelo usuário.", "")
            break

    progress_cb(100, f"Concluído: {suc} ok, {err} erros", "")
    return {"sucessos": suc, "erros": err}
