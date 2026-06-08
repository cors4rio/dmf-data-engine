"""
engine/nfe_arquivos.py
Daemon de processamento de ZIPs de NF-e — extrai XMLs e roteia para Z:.
Fonte: AGROMIX_ATACADAO/DOWNLOAD NFE/arquivos.py
Adições: stop_flag (threading.Event), config como parâmetro.
PRESERVADO: tempdir atômico, copyfile sem metadados, retry em arquivo em uso,
            zipar_pasta_mes() flat, derivação robusta de mes_ano, extração de CNPJ,
            resolução de pasta existente no Z:.
NÃO ALTERADO: lógica de escrita em rede (velocidade Z: já resolvida).
"""

import os
import re
import sys
import time
import zipfile
import shutil
import logging
import threading
import unicodedata
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime

log = logging.getLogger("NFE_Arquivos")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── utilitários ──────────────────────────────────────────────────────────────

def _remover_acentos(texto: str) -> str:
    try:
        nfkd = unicodedata.normalize("NFKD", texto)
        s = "".join(c for c in nfkd if not unicodedata.combining(c))
        return re.sub(r"[^a-zA-Z0-9\-\_\ ]", "", s)
    except Exception:
        return texto


def _extrair_cnpj(caminho_zip: str):
    ns = {"ns": "http://www.portalfiscal.inf.br/nfe"}
    try:
        with zipfile.ZipFile(caminho_zip, "r") as z:
            for nome in z.namelist():
                if nome.endswith(".xml"):
                    try:
                        with z.open(nome) as xf:
                            cnpj = ET.parse(xf).getroot().find(".//ns:emit/ns:CNPJ", ns)
                            if cnpj is not None:
                                return cnpj.text
                    except Exception:
                        continue
    except Exception as e:
        log.error(f"Erro ao ler CNPJ de {caminho_zip}: {e}")
    return None


def _derivar_mes_ano(caminho_zip: str, nome_arq: str) -> str:
    base = os.path.splitext(nome_arq)[0]

    m = re.search(r"[_\-](\d{1,2})[_\-](20\d{2})(?:[_\-]|$)", base)
    if m:
        mes, ano = int(m.group(1)), int(m.group(2))
        if 1 <= mes <= 12:
            return f"{mes:02d}{ano}"

    m = re.search(r"[_\-](0[1-9]|1[0-2])(20\d{2})(?:[_\-]|$)", base)
    if m:
        return m.group(1) + m.group(2)

    ns = {"ns": "http://www.portalfiscal.inf.br/nfe"}
    try:
        with zipfile.ZipFile(caminho_zip, "r") as z:
            for arq in z.namelist():
                if arq.endswith(".xml"):
                    try:
                        with z.open(arq) as f:
                            dh = ET.parse(f).getroot().find(".//ns:dhEmi", ns)
                            if dh is not None and dh.text:
                                partes = dh.text[:10].split("-")
                                if len(partes) == 3:
                                    return f"{partes[1]}{partes[0]}"
                    except Exception:
                        continue
    except Exception as e:
        log.error(f"Fallback mes_ano falhou: {e}")

    agora = datetime.now()
    return f"{agora.month:02d}{agora.year}"


def _zipar_pasta_mes(caminho_pasta: str, mes_ano: str) -> bool:
    """Consolida todos os arquivos não-ZIP/não-tmp da pasta em MMYYYY.zip (flat, sem subpastas).
    Após criar o ZIP, remove os arquivos soltos (mantém só o ZIP final)."""
    nome_zip  = f"{mes_ano}.zip"
    dest_zip  = os.path.join(caminho_pasta, nome_zip)
    tmp_zip   = dest_zip + ".tmp"

    # Cleanup proativo: remove .tmp órfãos da pasta antes de zipar
    for f in os.listdir(caminho_pasta):
        if f.endswith(".tmp"):
            try:
                os.remove(os.path.join(caminho_pasta, f))
                log.info(f"Removido .tmp órfão: {f}")
            except Exception as ex:
                log.warning(f"Não removeu .tmp órfão {f}: {ex}")

    # Inclui só arquivos reais: ignora .zip e .tmp (evita .zip.tmp inflar tudo)
    arquivos = [
        f for f in os.listdir(caminho_pasta)
        if os.path.isfile(os.path.join(caminho_pasta, f))
        and not f.endswith(".zip")
        and not f.endswith(".tmp")
    ]
    if not arquivos:
        return False

    try:
        with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for arq in arquivos:
                zf.write(os.path.join(caminho_pasta, arq), arcname=arq)
        if os.path.exists(dest_zip):
            os.remove(dest_zip)
        os.rename(tmp_zip, dest_zip)
        log.info(f"ZIP criado: {dest_zip} ({len(arquivos)} arquivo(s))")

        # Após zipar com sucesso, remove os arquivos soltos (mantém só o ZIP)
        removidos = 0
        for arq in arquivos:
            try:
                os.remove(os.path.join(caminho_pasta, arq))
                removidos += 1
            except Exception as ex:
                log.warning(f"Não removeu solto {arq}: {ex}")
        if removidos:
            log.info(f"Limpeza: {removidos} arquivo(s) solto(s) removido(s).")
        return True
    except Exception as e:
        log.error(f"Falha ao criar ZIP: {e}")
        if os.path.exists(tmp_zip):
            try:
                os.remove(tmp_zip)
            except Exception:
                pass
        return False


# ── processamento ─────────────────────────────────────────────────────────────

def processar_arquivos(config: dict = None, download_dir: str = "") -> tuple:
    """Processa ZIPs pendentes na pasta downloads/. Retorna (suc, err, lista_erros)."""
    config  = config or {}
    _dl_dir = download_dir or config.get("_download_dir") or os.path.join(BASE_DIR, "downloads")
    pasta_z = config.get("paths", {}).get("nfe", r"Z:\#ROTINA AUTOMATICA NF\NFe")

    # Importa mapeamento de lojas
    try:
        sys.path.insert(0, BASE_DIR)
        from bx_config.lojas import MAPEAMENTO_CNPJ
    except ImportError:
        MAPEAMENTO_CNPJ = {}

    os.makedirs(_dl_dir, exist_ok=True)

    # Valida acesso à rede — verifica o drive/raiz do caminho configurado
    drive, _ = os.path.splitdrive(pasta_z)
    drive_root = (drive + os.sep) if drive else os.sep
    if not os.path.isdir(drive_root):
        return 0, 0, [f"Drive inacessível: {drive_root}"]

    zips = [a for a in os.listdir(_dl_dir) if a.endswith(".zip")]
    suc = err = 0
    erros = []

    for arq in zips:
        caminho = os.path.join(_dl_dir, arq)
        try:
            mes_ano  = _derivar_mes_ano(caminho, arq)
            cnpj     = _extrair_cnpj(caminho)

            if not cnpj:
                log.warning(f"CNPJ não encontrado em {arq} — movendo para quarentena.")
                q = os.path.join(pasta_z, "QUARENTENA_SEM_CNPJ")
                os.makedirs(q, exist_ok=True)
                shutil.move(caminho, os.path.join(q, arq))
                err += 1
                erros.append(f"{arq}: CNPJ não encontrado")
                continue

            pasta_num = MAPEAMENTO_CNPJ.get(cnpj, f"Desconhecido_CNPJ_{cnpj}")
            sem_ac    = _remover_acentos(pasta_num)
            cod_loja  = sem_ac.split("-")[0]

            # Resolve pasta existente no Z: (preserva nomenclatura antiga)
            pasta_final = sem_ac
            try:
                if os.path.exists(pasta_z):
                    canditas = [
                        (len(os.listdir(os.path.join(pasta_z, obj))), obj)
                        for obj in os.listdir(pasta_z)
                        if obj.startswith(f"{cod_loja}-")
                        and os.path.isdir(os.path.join(pasta_z, obj))
                    ]
                    if canditas:
                        pasta_final = sorted(canditas, reverse=True)[0][1]
            except Exception as ex:
                log.warning(f"Falha ao checar pastas existentes: {ex}")

            destino = os.path.join(pasta_z, pasta_final, mes_ano)

            # Log rastreabilidade: ZIP com subpastas?
            try:
                with zipfile.ZipFile(caminho, "r") as zf_check:
                    if any("/" in n for n in zf_check.namelist()):
                        log.info(f"{arq}: ZIP de entrada contém subpastas — motor de extração tratará.")
            except Exception:
                pass

            # Extração atômica em tempdir → copia para destino → re-zipa flat
            with tempfile.TemporaryDirectory() as tmp_dir:
                try:
                    with zipfile.ZipFile(caminho, "r") as zf:
                        zf.extractall(tmp_dir)
                except zipfile.BadZipFile as be:
                    log.error(f"ZIP corrompido {arq}: {be}")
                    err += 1
                    erros.append(f"{arq}: ZIP corrompido")
                    continue

                xmls = [f for f in os.listdir(tmp_dir) if f.lower().endswith(".xml")]
                if not xmls:
                    for root, _, files in os.walk(tmp_dir):
                        xmls += [f for f in files if f.lower().endswith(".xml")]

                if not xmls:
                    log.error(f"Sem XMLs em {arq}")
                    err += 1
                    erros.append(f"{arq}: sem XMLs")
                    continue

                os.makedirs(destino, exist_ok=True)

                copiados = 0
                for root_d, _, files in os.walk(tmp_dir):
                    rel = os.path.relpath(root_d, tmp_dir)
                    dst_d = os.path.join(destino, rel) if rel != "." else destino
                    os.makedirs(dst_d, exist_ok=True)
                    for f in files:
                        shutil.copyfile(
                            os.path.join(root_d, f),
                            os.path.join(dst_d, f),
                        )
                        copiados += 1

            log.info(f"Extraído: {arq} → {destino} ({copiados} arquivos)")
            _zipar_pasta_mes(destino, mes_ano)
            suc += 1

            try:
                os.remove(caminho)
            except Exception as e:
                log.warning(f"Não removeu {caminho}: {e}")

        except Exception as e:
            if "used by another process" in str(e) or "PermissionError" in str(e):
                log.warning(f"{arq} em uso — aguardando...")
                time.sleep(2)
                continue
            log.error(f"Falha em {arq}: {e}")
            err += 1
            erros.append(f"{arq}: {e}")

    return suc, err, erros


# ── loop daemon ───────────────────────────────────────────────────────────────

def processar_loop(stop_flag: threading.Event, config: dict = None, download_dir: str = ""):
    log.info("Daemon arquivos iniciado.")
    _drive_erros = 0
    while not stop_flag.is_set():
        suc, err, erros = processar_arquivos(config, download_dir)
        drive_indisponivel = any("Drive inacessível" in e for e in erros)
        if drive_indisponivel:
            _drive_erros += 1
            # Loga apenas na 1ª ocorrência e depois a cada ~5 min (60 ciclos × 5s)
            if _drive_erros == 1 or _drive_erros % 60 == 0:
                log.warning(f"Daemon arquivos: drive inacessível ({_drive_erros}x) — aguardando reconexão.")
            stop_flag.wait(timeout=30)
        else:
            _drive_erros = 0
            if suc > 0 or err > 0:
                log.info(f"Arquivos: {suc} ok, {err} erros")
            stop_flag.wait(timeout=5)
    log.info("Daemon arquivos encerrado.")
