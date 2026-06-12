"""
teste_manual.py
---------------
Script de teste para rodar as extrações MANUALMENTE com o mês ATUAL (ou o especificado).
NÃO altera nenhum código fonte — apenas importa e chama os módulos existentes
com datas sobrescritas via monkey-patch.

Uso:
    python teste_manual.py              -> Menu interativo
    python teste_manual.py executa      -> Roda com o mês atual (em vez do M-1 padrão) 
    python teste_manual.py executa --mes 4 --ano 2026 -> Roda para Abril de 2026

Pré-requisitos:
    Estar com o .env configurado corretamente.
"""

import os
import sys
import argparse
import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

load_dotenv()

# Adiciona o diretório raiz ao path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ===========================================================================
# VALIDAÇÕES BÁSICAS
# ===========================================================================

def validar_ambiente():
    erros = []
    if not os.getenv("EMAIL_USER"):
        erros.append("EMAIL_USER não configurada. Verifique o arquivo .env.")
    if not os.getenv("SHAREPOINT_BASE_URL"):
        erros.append("SHAREPOINT_BASE_URL não configurada no .env.")

    mapa_ano = datetime.datetime.now().year
    if not os.path.exists(os.path.join(BASE_DIR, "config", f"sharepoint_map_{mapa_ano}.json")):
        print(f"[AVISO] Mapa sharepoint_map_{mapa_ano}.json não encontrado em config/. Pode gerar erro no teste.")

    if erros:
        for e in erros:
            print(f"[ERRO] {e}")
        sys.exit(1)


# ===========================================================================
# MONKEY-PATCH DATETIME
# ===========================================================================

class FalsoDatetime(datetime.datetime):
    _data_falsa = None
    
    @classmethod
    def now(cls, tz=None):
        return cls._data_falsa if cls._data_falsa else datetime.datetime.now(tz)

class MockDatetimeModule:
    # Este mock substitui o módulo datetime no escopo do use_case,
    # permitindo que nosso FalsoDatetime controle a função now().
    datetime = FalsoDatetime


# ===========================================================================
# PROCESSO DE TESTE
# ===========================================================================

def testar_execucao(mes=None, ano=None, unidade_alvo=None):
    agora = datetime.datetime.now()
    if ano is None: ano = agora.year
    if mes is None: mes = agora.month

    print("\n" + "=" * 60)
    print(f"  TESTE MANUAL — AUTO TOKAI (Referência: {mes:02d}/{ano})")
    print("=" * 60)

    # A lógica original do projeto calcula a data alvo voltando 1 mês:
    #   hoje = datetime.now()
    #   mes_alvo = hoje - 1 mês
    # Para forçarmos o processamento *do mês solicitado*, engamos o código
    # retornando "now() = mês solicitado + 1 mês".
    data_alvo_desejada = datetime.datetime(ano, mes, 15)
    data_falsa = data_alvo_desejada + relativedelta(months=1)
    
    print(f"\n[INFO] Simulando data atual como {data_falsa.strftime('%d/%m/%Y')}.")
    print(f"       Isso forçará a automação a extrair os XMLs de '{mes:02d}/{ano}'.\n")
    
    # Aplica o Monkey-Patch no módulo Use Case
    import src.application.use_cases.download_sharepoint_files as use_case_mod
    
    FalsoDatetime._data_falsa = data_falsa
    use_case_mod.datetime = MockDatetimeModule

    # Desativa a trava de segurança de idade do e-mail (permite rodar meses antigos no modo manual)
    os.environ["MAX_EMAIL_AGE_DAYS"] = "365"

    print("Disparando automação...\n")
    
    notifier = None
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from src.infrastructure.notifications.notificador_service import NotificadorService
        notifier = NotificadorService()
        notifier.modulo += " (Manual)"
        notifier.notify_start(periodo=f"{mes:02d}/{ano}")

    try:
        use_case = use_case_mod.DownloadSharePointFilesUseCase()
        ok, erro, lista_erros = use_case.execute(unidade_alvo=unidade_alvo)
        
        print("\n" + "-" * 30)
        print("RESUMO DA EXECUÇÃO")
        print(f"  Sucessos: {ok}")
        print(f"  Erros:    {erro}")
        if lista_erros:
            print("\n  Lista de Erros:")
            for e in lista_erros[:10]:
                print(f"    - {e}")
        print("-" * 30)

        if notifier:
            notifier.notify_end(sucessos=ok, erros=erro, lista_erros=lista_erros)

        print("\n[RESULTADO] Execução manual concluída!")
    except Exception as e:
        print(f"\n[FALHA CRÍTICA] Erro durante a execução: {e}")
        if notifier:
            notifier.notify_error(f"Erro inesperado no teste manual: {str(e)}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n[FALHA CRÍTICA] Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()

# ===========================================================================
# MENU INTERATIVO
# ===========================================================================

def menu_interativo():
    print("\n" + "=" * 60)
    print("  AUTO TOKAI — MENU DE TESTE MANUAL")
    print("=" * 60)
    
    agora = datetime.datetime.now()
    mes_sugestao = agora.month
    ano_sugestao = agora.year
    
    print(f"\nConfiguração do Período:")
    in_mes = input(f"  Mês alvo (1-12) [Padrão {mes_sugestao:02d}]: ").strip()
    in_ano = input(f"  Ano alvo (YYYY) [Padrão {ano_sugestao}]: ").strip()
    in_unidade = input(f"  Unidade alvo (ex: LOTTI, deixe vazio para todas): ").strip()
    
    mes = int(in_mes) if in_mes else mes_sugestao
    ano = int(in_ano) if in_ano else ano_sugestao
    unidade_alvo = in_unidade if in_unidade else None
    
    print(f"\n--- Período Definido ---")
    print(f"  Referência (Mês/Ano): {mes:02d}/{ano}")
    if unidade_alvo:
        print(f"  Unidade Alvo: {unidade_alvo}")
    else:
        print(f"  Unidade Alvo: TODAS")
    print("-" * 25)
    
    print("\nEste teste executa a rotina inteira para o mês selecionado.")
    print("Certifique-se de que o Mapa Json engloba este mês e que o Drive Z: está MAPEADO.")
    print("\n  [1] Executar Automação")
    print("  [0] Sair\n")

    escolha = input("Opção: ").strip()

    if escolha == "1":
        testar_execucao(mes, ano, unidade_alvo)
    elif escolha == "0":
        print("Saindo.")
        sys.exit(0)
    else:
        print("Opção inválida.")

# ===========================================================================
# ENTRYPOINT
# ===========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste manual com Mês Atual ou especificado.")
    parser.add_argument("comando", nargs="?", choices=["executa"], help="Use 'executa' para rodar diretamente sem menu.")
    parser.add_argument("--mes", type=int, help="Mês alvo manual (1-12)")
    parser.add_argument("--ano", type=int, help="Ano alvo manual (YYYY)")
    parser.add_argument("--unidade", type=str, help="Filtra a execução por uma unidade específica (ex: LOTTI)")
    
    args = parser.parse_args()

    validar_ambiente()
    
    mes_final = args.mes if args.mes else datetime.datetime.now().month
    ano_final = args.ano if args.ano else datetime.datetime.now().year
    unidade_final = args.unidade if args.unidade else None

    if args.comando == "executa":
        testar_execucao(mes_final, ano_final, unidade_final)
    else:
        menu_interativo()
