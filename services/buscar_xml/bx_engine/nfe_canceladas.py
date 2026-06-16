"""
engine/nfe_canceladas.py
Baixa o XML da NOTA que foi cancelada (o <enviNFe> autorizado) no ERP Bluesoft.

Motivação: o disparo por e-mail (nfe_disparo + enviarVariasNotasPorEmail) NÃO entrega o
XML das notas CANCELADAS — só o XML do evento de cancelamento já vem por outra via. Este
módulo cobre essa lacuna, reusando a sessão autenticada do disparo (requests puro, sem
Playwright).

Cadeia mapeada (ver memória do projeto / Fase 0):
  1. Pesquisar a loja/período → lista de nfKeys (mesma pesquisa do nfe_disparo).
  2. GET visualizar.action?nfKey=<nfKey> → HTML. Se a nota é cancelada (span .cancelada),
     na aba Ocorrências (tabela tableOcorrenciasNfe) a linha cujo "Tipo de envio" é
     "Transmissão de Lote de NF-e" tem onclick=verXmlRemessa('<KEY>'). Essa KEY é o XML
     da NOTA. (A linha "Cancelamento de NFe" é o evento — ignorada, já vem pela rotina.)
  3. GET verXmlRemessa.action?arquivoNfeRemessaKey=<KEY> → text/xml cru → salvar.

Os XMLs baixados são empacotados num ZIP em downloads/ no MESMO formato dos e-mails, de
modo que o daemon nfe_arquivos.processar_arquivos roteia por CNPJ/competência ao Z:
automaticamente — sem duplicar a lógica de destino.
"""

import os
import re
import logging
import threading
import zipfile

from .nfe_disparo import URL_PESQUISA, HEADERS

log = logging.getLogger("NFE_Canceladas")

_BASE_ERP = "https://erp.bluesoft.com.br/agromixatalaia"
URL_VISUALIZAR = _BASE_ERP + "/comercial/consultaNotaFiscal/visualizar.action"
URL_VERXML = _BASE_ERP + "/comercial/consultaNotaFiscal/verXmlRemessa.action"

# Texto que identifica, na aba Ocorrências, a linha cujo XML é o da NOTA (não o evento).
_TIPO_ENVIO_NOTA = "Transmissão de Lote de NF-e"


def _payload_pesquisa(loja_key: str, dt_ini: str, dt_fim: str) -> dict:
    """Mesma pesquisa do disparo (nfe_disparo._disparar_loja). statusCancelamento=TODOS
    (o valor 'CANCELADAS' não existe no ERP → HTTP 400); o filtro de canceladas é feito
    nota a nota pelo marcador no HTML do visualizar.action."""
    return {
        "lgpdExibirDadosPessoais": "",
        "ordenacaoParaEntrada": "nf.dataEmissao asc, notaFiscalTotal.valorTotalNota asc",
        "ordenacaoParaSaida": "nf.dataEmissao asc, notaFiscalTotal.valorTotalNota asc",
        "tabNumero": "0", "tipoConsulta": "1",
        "selecionaEntradaRecebimnetoDeMercadorias": "false",
        "lojaKey": str(loja_key), "nomeDestinatario": "",
        "dataInicial": dt_ini, "dataFinal": dt_fim,
        "chave": "", "nfNumero": "", "valor": "0,00",
        "cfopKey": "0", "notaFiscalTipoKey": "0",
        "statusReferencia": "TODAS", "statusCancelamento": "TODOS",
        "statusCartaDeCorrecao": "0", "tipoStatusNfeKey": "0",
        "protocoloAutorizacao": "", "statusEmail": "0",
        "statusEmailNotaFiscalCancelada": "0",
        "ordenar": "nf.dataEmissao,notaFiscalTotal.valorTotalNota",
    }


def _listar_nfkeys_canceladas(sessao, loja_key: str, dt_ini: str, dt_fim: str) -> list:
    """Pesquisa NF-e da loja/período e retorna SÓ as nfKeys das notas CANCELADAS.

    O filtro é feito na própria LISTAGEM (não abrindo cada nota): cada linha da tabela
    é <tr id="nfNNNNN"> e traz um marcador de status — class="infotip cancelada"
    com title="Nota fiscal cancelada em ..." (as normais têm "naoCancelada" /
    "Nota fiscal não cancelada"). Assim abrimos o visualizar.action só das poucas
    canceladas, em vez de TODAS as notas do período. Sem isso, uma loja com centenas
    de notas (ex.: MATRIZ com 211) faria centenas de requisições e a etapa ficava
    lenta demais / não concluía — o que fazia parecer que "não baixava canceladas".
    """
    try:
        r = sessao.post(URL_PESQUISA, data=_payload_pesquisa(loja_key, dt_ini, dt_fim), timeout=90)
    except Exception as e:
        log.error(f"Canceladas: erro na pesquisa (loja {loja_key}): {e}")
        return []
    if r.status_code != 200:
        log.warning(f"Canceladas: pesquisa HTTP {r.status_code} (loja {loja_key})")
        return []
    html = r.text or ""

    canceladas = []
    # Cada nota é um bloco <tr id="nfNNNNN"> ... </tr>. Dentro dele, o título
    # "Nota fiscal cancelada" (sem "não") marca a cancelada de forma inequívoca.
    for m in re.finditer(r'<tr id="nf(\d+)">(.*?)</tr>', html, re.DOTALL):
        nfkey, bloco = m.group(1), m.group(2)
        if re.search(r'title="Nota fiscal cancelada', bloco):
            canceladas.append(nfkey)

    # Fallback de robustez: se o parsing por <tr> não casar (mudança de layout),
    # detecta pelo title em todo o HTML e associa ao nfKeys mais próximo.
    if not canceladas and 'title="Nota fiscal cancelada' in html:
        log.warning("Canceladas: parsing por <tr> não casou; usando fallback por proximidade.")
        for m in re.finditer(r'value="(\d+)"\s+class="nfKeys"(.*?)title="Nota fiscal cancelada',
                             html, re.DOTALL):
            # só aceita se o trecho entre a key e o title for curto (mesma linha)
            if len(m.group(2)) < 4000:
                canceladas.append(m.group(1))

    return sorted(set(canceladas))


def _extrair_chave_remessa_da_nota(html: str) -> str | None:
    """No HTML do visualizar.action, acha a arquivoNfeRemessaKey da linha cujo tipo de
    envio é 'Transmissão de Lote de NF-e' — essa é a remessa do XML da NOTA.

    IMPORTANTE: a aba Ocorrências tem VÁRIAS linhas (Transmissão de Lote = a nota;
    Cancelamento de NFe = o evento; Manifestação do Destinatário = etc.), CADA UMA com
    sua própria verXmlRemessa. Só a de 'Transmissão de Lote' é o XML da nota. Antes havia
    um fallback que pegava a PRIMEIRA verXmlRemessa quando a âncora não casava — isso
    baixava o XML ERRADO (evento de cancelamento ou manifestação), que depois falhava na
    extração de CNPJ e ia para quarentena (bug visto na loja 0011-91 / nota 106227, que
    só tinha 'Manifestação do Destinatário'). Agora: SEM fallback — se não há linha de
    'Transmissão de Lote', a nota não tem o XML da nota nessa aba e retornamos None."""
    if not html:
        return None
    idx = html.find(_TIPO_ENVIO_NOTA)
    if idx < 0:
        return None  # sem 'Transmissão de Lote' → não há XML da nota; NÃO pegar outro
    m = re.search(r"verXmlRemessa\('(\d+)'\)", html[idx:])
    return m.group(1) if m else None


def _xml_chave_nfe(xml_text: str) -> str | None:
    """Extrai a chave de 44 dígitos do XML (Id='NFe...') para nomear o arquivo."""
    m = re.search(r'Id="NFe(\d{44})"', xml_text or "")
    return m.group(1) if m else None


def _baixar_xml_nota_cancelada(sessao, nfkey: str) -> tuple:
    """Para uma nfKey: verifica se é cancelada e, se for, baixa o XML da nota.
    Retorna (status, xml_text|None, chave_nfe|None):
      status ∈ {"baixado", "nao_cancelada", "sem_remessa", "erro"}.
    """
    try:
        r = sessao.get(URL_VISUALIZAR, params={"nfKey": nfkey}, timeout=90)
    except Exception as e:
        log.warning(f"Canceladas: erro ao abrir nota {nfkey}: {e}")
        return ("erro", None, None)
    if r.status_code != 200:
        return ("erro", None, None)
    html = r.text or ""

    # Marcador de cancelada no HTML (span class="cancelada">(Cancelada)).
    if 'class="cancelada"' not in html and "(Cancelada)" not in html:
        return ("nao_cancelada", None, None)

    chave_remessa = _extrair_chave_remessa_da_nota(html)
    if not chave_remessa:
        # Cancelada, mas sem linha 'Transmissão de Lote de NF-e' na aba Ocorrências —
        # o XML da nota não está disponível aqui (ex.: nota com só 'Manifestação do
        # Destinatário'). NÃO baixamos outro tipo no lugar.
        log.info(f"Canceladas: nota {nfkey} sem 'Transmissão de Lote' — XML da nota "
                 f"indisponível nesta nota; pulando.")
        return ("sem_remessa", None, None)

    try:
        rx = sessao.get(URL_VERXML, params={"arquivoNfeRemessaKey": chave_remessa}, timeout=90)
    except Exception as e:
        log.warning(f"Canceladas: erro ao baixar XML remessa {chave_remessa} (nota {nfkey}): {e}")
        return ("erro", None, None)
    if rx.status_code != 200 or "xml" not in rx.headers.get("content-type", "").lower():
        log.warning(f"Canceladas: remessa {chave_remessa} retornou {rx.status_code} / "
                    f"{rx.headers.get('content-type','')}")
        return ("erro", None, None)

    xml_text = rx.text
    # Defesa extra: garante que é o XML da NOTA (enviNFe/NFe), não um evento
    # (<envEvento>/<procEventoNFe>) nem manifestação. Sem o emit/CNPJ correto, o
    # daemon de arquivos mandaria para QUARENTENA_SEM_CNPJ.
    if "<enviNFe" not in xml_text and "<NFe" not in xml_text:
        log.warning(f"Canceladas: remessa {chave_remessa} (nota {nfkey}) não é XML de NOTA "
                    f"(provável evento/manifestação) — descartado.")
        return ("sem_remessa", None, None)

    chave_nfe = _xml_chave_nfe(xml_text) or chave_remessa
    return ("baixado", xml_text, chave_nfe)


def baixar_canceladas_loja(sessao, loja: dict, periodo: dict, stop_flag: threading.Event,
                           progress_cb, download_dir: str, pct: int = 50) -> dict:
    """Baixa o XML das notas canceladas de UMA loja e gera o ZIP em download_dir.
    Usado tanto pelo modo INTERCALADO (callback após cada disparo) quanto pelo loop
    de todas as lojas. Retorna {"notas_canceladas","xmls_salvos","erros"}."""
    os.makedirs(download_dir, exist_ok=True)
    try:
        sessao.headers.update(HEADERS)
    except Exception:
        pass

    mes_ano = periodo.get("mes_ano", "")
    dt_ini = periodo["data_inicio"]
    dt_fim = periodo["data_fim"]
    nome = loja.get("apelido", loja.get("codigo", "?"))
    loja_key = loja.get("id_bluesoft")

    res = {"notas_canceladas": 0, "xmls_salvos": 0, "erros": 0}
    if not loja_key or stop_flag.is_set():
        return res

    # Lista SÓ as canceladas (filtradas na própria pesquisa) — abrimos o
    # visualizar.action de poucas notas, não de todas. Garante velocidade
    # uniforme em TODAS as lojas, independente do volume de notas.
    nfkeys = _listar_nfkeys_canceladas(sessao, loja_key, dt_ini, dt_fim)
    if not nfkeys:
        log.info(f"Canceladas: {nome} — nenhuma nota cancelada no período.")
        return res
    log.info(f"Canceladas: {nome} — {len(nfkeys)} nota(s) cancelada(s) na pesquisa.")
    progress_cb(pct, f"Canceladas: {nome} — {len(nfkeys)} cancelada(s), baixando XML...", nome)

    xmls_loja: list = []  # (nome_arquivo, xml_bytes)
    for nfk in nfkeys:
        if stop_flag.is_set():
            break
        status, xml_text, chave_nfe = _baixar_xml_nota_cancelada(sessao, nfk)
        if status == "baixado":
            res["notas_canceladas"] += 1
            xmls_loja.append((f"{chave_nfe}.xml", xml_text.encode("utf-8")))
            log.info(f"Canceladas: {nome} — XML da nota {chave_nfe} baixado.")
        elif status in ("sem_remessa", "erro"):
            res["erros"] += 1
            log.warning(f"Canceladas: {nome} — nota {nfk} marcada cancelada mas "
                        f"sem XML de remessa ({status}).")

    if xmls_loja:
        # Nome do ZIP carrega o mes_ano para o _derivar_mes_ano acertar a competência.
        zip_nome = f"canceladas_{loja.get('codigo','')}_{mes_ano}.zip"
        zip_path = os.path.join(download_dir, zip_nome)
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for arc, data in xmls_loja:
                    zf.writestr(arc, data)
            res["xmls_salvos"] += len(xmls_loja)
            progress_cb(pct, f"Canceladas: {nome} — {len(xmls_loja)} XML(s) de cancelada(s) salvos.", nome)
            log.info(f"Canceladas: {nome} — ZIP {zip_nome} com {len(xmls_loja)} XML(s).")
        except Exception as e:
            res["erros"] += 1
            log.error(f"Canceladas: falha ao gerar ZIP de {nome}: {e}")

    return res


def baixar_canceladas(sessao, lojas: list, periodo: dict, stop_flag: threading.Event,
                      progress_cb, download_dir: str, config: dict = None) -> dict:
    """
    Versão que percorre TODAS as lojas (modo não-intercalado). Para cada loja chama
    baixar_canceladas_loja. Mantida para uso direto/testes; o fluxo do app usa o modo
    intercalado (callback por loja no executar_nfe).
    Retorna {"notas_canceladas", "xmls_salvos", "erros"}.
    """
    total_lojas = len(lojas)
    notas_canceladas = xmls_salvos = erros = 0

    for i, loja in enumerate(lojas):
        if stop_flag.is_set():
            progress_cb(None, "Canceladas: cancelado pelo usuário.", "")
            break
        pct = 50 + int((i / max(total_lojas, 1)) * 45)
        r = baixar_canceladas_loja(sessao, loja, periodo, stop_flag, progress_cb, download_dir, pct)
        notas_canceladas += r["notas_canceladas"]
        xmls_salvos += r["xmls_salvos"]
        erros += r["erros"]

    log.info(f"Canceladas: concluído — {notas_canceladas} nota(s) cancelada(s), "
             f"{xmls_salvos} XML(s) salvos, {erros} erro(s).")
    return {"notas_canceladas": notas_canceladas, "xmls_salvos": xmls_salvos, "erros": erros}
