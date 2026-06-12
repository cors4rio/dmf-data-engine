import os
import zipfile
import subprocess
import threading
import time
from loguru import logger


# ---------------------------------------------------------------
# Constantes de Extração
# ---------------------------------------------------------------
# Baseline: 20 segundos por MB. Mínimo 15 min, máximo 90 min.
# Justificativa: extração em drive de rede com milhares de arquivos pequenos
# é limitada por I/O por arquivo, não por MB. 18.5 MB com 4607 XMLs levou
# 255s reais (13.8s/MB) — baseline de 6s/MB subestimava por 2x.
# Com baseline 20s/MB: 18.5 MB → 370s (~6 min), suficiente com margem.
TIMEOUT_BASELINE_POR_MB = 20
TIMEOUT_MIN = 900      # 15 minutos
TIMEOUT_MAX = 5400     # 90 minutos


def _calcular_timeout(file_path: str) -> int:
    """
    Calcula timeout dinâmico baseado no tamanho do arquivo.

    Tabela de referência (baseline 20s/MB, mín 15 min, máx 90 min):
        < 45 MB  →  15 min  (900s, mínimo)
        50 MB    →  ~17 min (1000s)
        100 MB   →  ~33 min (2000s)
        200 MB   →  ~67 min (4000s)
        > 270 MB →  90 min  (5400s, cap)
    """
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        timeout = max(TIMEOUT_MIN, min(TIMEOUT_MAX, int(size_mb * TIMEOUT_BASELINE_POR_MB)))
        logger.info(
            f"Timeout dinâmico calculado: {timeout}s "
            f"(arquivo: {size_mb:.1f} MB, baseline: {TIMEOUT_BASELINE_POR_MB}s/MB)"
        )
        return timeout
    except Exception:
        logger.warning("Não foi possível calcular o tamanho do arquivo. Usando timeout padrão de 600s.")
        return 600


def _validar_zip(file_path: str) -> bool:
    """
    Testa integridade do arquivo ZIP sem extrair (verifica CRC de todos os membros).
    Retorna True se íntegro ou se não foi possível verificar (falha suave).
    """
    try:
        logger.info("Verificando integridade do ZIP (CRC test)...")
        with zipfile.ZipFile(file_path, 'r') as zf:
            bad_file = zf.testzip()
            if bad_file is not None:
                logger.error(f"ZIP corrompido! Primeiro arquivo com CRC inválido: '{bad_file}'")
                return False
        logger.success("ZIP íntegro — CRC OK em todos os membros.")
        return True
    except zipfile.BadZipFile as e:
        logger.error(f"Arquivo ZIP inválido (não é um ZIP válido): {e}")
        return False
    except Exception as e:
        logger.warning(f"Não foi possível verificar integridade do ZIP ({e}). Tentando extrair assim mesmo...")
        return True  # Falha suave — tenta mesmo sem garantia


def _validar_rar(file_path: str) -> bool:
    """
    Testa integridade do RAR usando 7z t ou unrar t.
    Retorna True se íntegro ou se não há ferramenta disponível (falha suave).
    """
    cmds_test = [
        ["7z", "t", "-y", file_path],
        [r"C:\Program Files\7-Zip\7z.exe", "t", "-y", file_path],
        ["/usr/bin/unrar", "t", "-y", file_path],
        ["unrar", "t", "-y", file_path],
    ]
    for cmd in cmds_test:
        try:
            logger.info(f"Verificando integridade do RAR: {cmd[0]} t ...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                logger.success("RAR íntegro.")
                return True
            else:
                logger.warning(f"Teste de integridade com {cmd[0]} falhou (code={result.returncode}).")
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout ao verificar integridade do RAR com {cmd[0]}.")
            continue
        except Exception:
            continue

    logger.warning("Nenhuma ferramenta disponível para verificar integridade do RAR. Tentando extrair assim mesmo...")
    return True  # Falha suave


def _extrair_com_7zip(file_path: str, output_dir: str, timeout: int) -> bool:
    """
    Extrai usando 7-Zip via subprocesso com timeout dinâmico e log de progresso a cada 30s.
    Tenta múltiplos caminhos do executável (Windows e Linux/container).
    """
    sz_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        "7z",
    ]

    for sz_path in sz_paths:
        try:
            logger.info(f"Tentando 7-Zip em '{sz_path}' com timeout={timeout}s...")
            process = subprocess.Popen(
                [sz_path, 'x', '-y', f'-o{output_dir}', file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            start_time = time.time()

            # Thread de monitoramento de progresso — loga a cada 30s sem bloquear
            def _monitor():
                last_log = 0
                while process.poll() is None:
                    elapsed = int(time.time() - start_time)
                    if elapsed > 0 and elapsed % 30 == 0 and elapsed != last_log:
                        last_log = elapsed
                        logger.info(f"Extração em andamento via 7-Zip... {elapsed}s decorridos.")
                    time.sleep(5)

            monitor_thread = threading.Thread(target=_monitor, daemon=True)
            monitor_thread.start()

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                elapsed = time.time() - start_time
                if process.returncode == 0:
                    logger.success(f"7-Zip concluído em {elapsed:.1f}s.")
                    return True
                else:
                    logger.warning(
                        f"7-Zip retornou código {process.returncode} após {elapsed:.1f}s. "
                        f"Stderr: {stderr[:300]}"
                    )
                    return False  # Falhou definitivamente com este caminho
            except subprocess.TimeoutExpired:
                logger.error(
                    f"Timeout de {timeout}s atingido para 7-Zip! O arquivo é muito grande ou o "
                    f"disco está lento. Encerrando processo..."
                )
                process.kill()
                process.wait()
                logger.warning("Processo 7-Zip encerrado forçadamente.")
                return False

        except FileNotFoundError:
            continue  # Executável não encontrado neste caminho, tenta o próximo
        except Exception as e:
            logger.warning(f"Erro inesperado ao tentar 7-Zip em '{sz_path}': {e}")
            continue

    logger.warning("7-Zip não encontrado em nenhum caminho conhecido.")
    return False


def _extrair_zip_nativo(file_path: str, output_dir: str) -> bool:
    """
    Extrai ZIP usando Python builtin, um arquivo por vez, com log de progresso.
    Não tem timeout externo pois o progresso é granular — cada arquivo é atômico.
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            members = zf.namelist()
            total = len(members)
            logger.info(f"Extraindo {total} membro(s) via Python zipfile (sem timeout fixo)...")

            for i, member in enumerate(members, 1):
                zf.extract(member, output_dir)
                # Log a cada 200 arquivos ou no último
                if total > 200 and (i % 200 == 0 or i == total):
                    logger.info(f"Progresso zipfile: {i}/{total} ({(i / total) * 100:.1f}%)")

        logger.success(f"Extração ZIP nativa concluída ({total} membro(s)).")
        return True
    except Exception as e:
        logger.warning(f"Falha na extração ZIP nativa: {e}")
        return False


def _extrair_rar_nativo(file_path: str, output_dir: str, timeout: int) -> bool:
    """
    Extrai RAR via unrar (Linux/container) com timeout dinâmico.
    """
    cmds = [
        ["/usr/bin/unrar", "x", "-o+", "-y", file_path, output_dir + "/"],
        ["unrar", "x", "-o+", "-y", file_path, output_dir + "/"],
    ]
    for cmd in cmds:
        try:
            logger.info(f"Tentando unrar: {cmd[0]} com timeout={timeout}s...")
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                if process.returncode == 0:
                    logger.success(f"Extração RAR concluída via {cmd[0]}.")
                    return True
                else:
                    logger.warning(f"unrar retornou código {process.returncode}. Stderr: {stderr[:200]}")
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                logger.error(f"Timeout de {timeout}s atingido para {cmd[0]}.")
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.warning(f"Erro com {cmd[0]}: {e}")

    return False


def _extrair_patool(file_path: str, output_dir: str) -> bool:
    """Último recurso: tenta extração via patool."""
    try:
        import patoolib
        logger.info("Tentando extração via patool...")
        patoolib.extract_archive(file_path, outdir=output_dir, verbosity=-1)
        logger.success("Extração via patool concluída.")
        return True
    except Exception as e:
        logger.error(f"patool também falhou: {e}")
        return False


def _extrair_rarfile(file_path: str, output_dir: str) -> bool:
    """Tenta extração via rarfile (biblioteca Python)."""
    try:
        import rarfile
        logger.info("Tentando extração via rarfile...")
        with rarfile.RarFile(file_path, 'r') as rf:
            rf.extractall(path=output_dir)
        logger.success("Extração via rarfile concluída.")
        return True
    except Exception as e:
        logger.warning(f"rarfile falhou: {e}")
        return False


def extrair_arquivo_robusto(file_path: str, output_dir: str, nome_cliente: str) -> dict:
    """
    Extrai um arquivo compactado de forma robusta e segura, executando:

    1. Validação inicial (arquivo existe, tamanho > 0)
    2. Cálculo de timeout dinâmico baseado no tamanho real
    3. Verificação de integridade (CRC) sem extrair
    4. Cascata de estratégias de extração com progresso e timeout individual
    5. Verificação pós-extração (conta arquivos criados)
    6. Remoção do compactado SOMENTE após confirmação de sucesso

    Args:
        file_path:   Caminho absoluto para o arquivo .zip ou .rar
        output_dir:  Diretório de destino da extração
        nome_cliente: Identificador do cliente (apenas para log)

    Returns:
        dict com chaves:
            'sucesso'           (bool)
            'arquivos_extraidos' (int)
            'xmls_encontrados'  (int)
            'mensagem'          (str)
            'arquivo'           (str — basename do arquivo)
    """
    resultado = {
        'sucesso': False,
        'arquivos_extraidos': 0,
        'xmls_encontrados': 0,
        'mensagem': '',
        'arquivo': os.path.basename(file_path),
    }

    # ===== FASE 1: Validações Iniciais =====
    if not os.path.exists(file_path):
        resultado['mensagem'] = f"Arquivo não encontrado: {file_path}"
        logger.error(resultado['mensagem'])
        return resultado

    tamanho_bytes = os.path.getsize(file_path)
    tamanho_mb = tamanho_bytes / (1024 * 1024)

    if tamanho_bytes == 0:
        resultado['mensagem'] = "Arquivo com tamanho zero — provavelmente download incompleto."
        logger.error(resultado['mensagem'])
        return resultado

    extensao = os.path.splitext(file_path)[1].lower().lstrip('.')
    nome_arquivo = os.path.basename(file_path)

    logger.info(
        f"[{nome_cliente}] --- Extracao Robusta iniciada --- "
        f"Arquivo: {nome_arquivo} | Tamanho: {tamanho_mb:.1f} MB | Formato: .{extensao.upper()}"
    )

    # ===== FASE 2: Timeout Dinâmico =====
    timeout = _calcular_timeout(file_path)

    # ===== FASE 3: Validação de Integridade =====
    if extensao == 'zip':
        integro = _validar_zip(file_path)
    elif extensao == 'rar':
        integro = _validar_rar(file_path)
    else:
        integro = True  # Assume válido para formatos desconhecidos

    if not integro:
        resultado['mensagem'] = (
            f"Arquivo corrompido (CRC inválido). Extração abortada para evitar dados parciais. "
            f"O arquivo compactado foi MANTIDO em: {file_path}"
        )
        logger.error(resultado['mensagem'])
        return resultado

    # ===== FASE 4: Cascata de Estratégias de Extração =====
    os.makedirs(output_dir, exist_ok=True)
    extraido = False

    # Estratégia 1: 7-Zip (prioridade máxima — suporta zip, rar, 7z e tem progresso real)
    extraido = _extrair_com_7zip(file_path, output_dir, timeout)

    # Estratégia 2: Python zipfile nativo (fallback para ZIP — granular, sem timeout rígido)
    if not extraido and extensao == 'zip':
        extraido = _extrair_zip_nativo(file_path, output_dir)

    # Estratégia 3: unrar nativo (fallback para RAR no Linux/container)
    if not extraido and extensao == 'rar':
        extraido = _extrair_rar_nativo(file_path, output_dir, timeout)

    # Estratégia 4: rarfile (biblioteca Python para RAR)
    if not extraido and extensao == 'rar':
        extraido = _extrair_rarfile(file_path, output_dir)

    # Estratégia 5: patool (último recurso universal)
    if not extraido:
        extraido = _extrair_patool(file_path, output_dir)

    # ===== FASE 5: Verificação Pós-Extração =====
    if not extraido:
        resultado['mensagem'] = (
            f"FALHA TOTAL: Nenhuma estratégia conseguiu extrair '{nome_arquivo}'. "
            f"O arquivo compactado foi MANTIDO em: {file_path}"
        )
        logger.error(resultado['mensagem'])
        return resultado

    # Conta arquivos no diretório de saída
    total_extraidos = 0
    xmls_encontrados = 0
    for _, _, files in os.walk(output_dir):
        for f in files:
            total_extraidos += 1
            if f.lower().endswith('.xml'):
                xmls_encontrados += 1

    if total_extraidos == 0:
        resultado['mensagem'] = (
            "Extração reportou sucesso mas NENHUM arquivo foi criado no diretório destino! "
            "Possível falha silenciosa da ferramenta de extração."
        )
        logger.error(resultado['mensagem'])
        return resultado

    logger.success(
        f"[{nome_cliente}] Verificação pós-extração: "
        f"{total_extraidos} arquivo(s) total | {xmls_encontrados} XML(s) | "
        f"Destino: {output_dir}"
    )
    resultado['arquivos_extraidos'] = total_extraidos
    resultado['xmls_encontrados'] = xmls_encontrados

    # ===== FASE 6: Remoção Segura do Compactado =====
    # SOMENTE remove o compactado após confirmar que a extração produziu arquivos
    try:
        os.remove(file_path)
        logger.info(f"Arquivo compactado '{nome_arquivo}' removido com segurança após extração confirmada.")
    except Exception as e:
        logger.warning(
            f"Não foi possível remover o compactado após extração: {e}. "
            f"Isso não afeta os XMLs extraídos — pode ser removido manualmente."
        )

    resultado['sucesso'] = True
    resultado['mensagem'] = (
        f"Sucesso: {total_extraidos} arquivo(s) extraído(s), {xmls_encontrados} XML(s) encontrado(s)."
    )
    logger.success(f"[{nome_cliente}] --- Extracao Robusta CONCLUIDA --- {resultado['mensagem']}")
    return resultado
