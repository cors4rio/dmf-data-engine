#!/usr/bin/env python3
"""
generate_map.py — Gerador Dinâmico de Mapa do SharePoint
=========================================================

Este script lê o arquivo `config_clientes.json` e gera automaticamente
o `sharepoint_map_{ano}.json` com todos os 12 meses do ano escolhido,
aplicando as exceções (overrides) definidas por mês.

Uso:
    python scripts/generate_map.py --ano 2026
    python scripts/generate_map.py --ano 2027
    python scripts/generate_map.py          # usa o ano atual

Como funciona:
    1. Para cada mês de 01 a 12, usa a lista padrão de clientes por regional.
    2. Se houver um 'override' para aquele mês específico, aplica as remoções
       e adições definidas para cada regional.
    3. Salva o resultado no arquivo `sharepoint_map_{ano}.json`.

Para adicionar uma nova empresa:
    1. Edite `config_clientes.json`.
    2. Adicione o cliente ao array da regional correta em `regioes_padrao`.
    3. Se a empresa só entra a partir de determinado mês, use `overrides`
       para `remover` ela dos meses anteriores (ou use `adicionar` se preferir
       a abordagem inversa — comece sem ela no padrão e adicione por override).
    4. Execute este script novamente.
"""

import json
import copy
import argparse
import datetime
import os
import sys


# Caminho base do projeto (sempre relativo à localização deste script)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config_clientes.json")


def carregar_config() -> dict:
    """Carrega e valida o arquivo de configuração de clientes."""
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERRO] Arquivo '{CONFIG_PATH}' não encontrado.")
        print("       Crie o config_clientes.json no diretorio 'config/' antes de continuar.")
        sys.exit(1)

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if "regioes_padrao" not in config:
        print("[ERRO] Chave 'regioes_padrao' ausente em config_clientes.json.")
        sys.exit(1)

    return config


def aplicar_overrides(mes_chave: str, regioes_base: dict, overrides_ano: dict) -> dict:
    """
    Aplica as exceções (overrides) definidas para um mês específico.

    Args:
        mes_chave:    String no formato 'MM-AAAA' (ex: '03-2026').
        regioes_base: Dicionário regional padrão {regional: [clientes...]}.
        overrides_ano: Seção de overrides para o ano atual.

    Returns:
        Dicionário regional final para o mês, com overrides aplicados.
    """
    resultado = copy.deepcopy(regioes_base)

    if mes_chave not in overrides_ano:
        return resultado  # Sem exceções para este mês

    override_mes = overrides_ano[mes_chave]
    regioes_modificadas = []

    for regional, modificacoes in override_mes.items():
        if regional not in resultado:
            # Regional nova que não existe no padrão — adicionar do zero
            resultado[regional] = modificacoes.get("adicionar", [])
            regioes_modificadas.append(f"  + Regional nova '{regional}': {resultado[regional]}")
            continue

        remover = modificacoes.get("remover", [])
        adicionar = modificacoes.get("adicionar", [])

        for cliente in remover:
            if cliente in resultado[regional]:
                resultado[regional].remove(cliente)
                regioes_modificadas.append(f"  - Removido '{cliente}' de '{regional}'")
            else:
                print(f"  [AVISO] Override tenta remover '{cliente}' de '{regional}', mas ele não está na lista padrão.")

        for cliente in adicionar:
            if cliente not in resultado[regional]:
                resultado[regional].append(cliente)
                regioes_modificadas.append(f"  + Adicionado '{cliente}' em '{regional}'")
            else:
                print(f"  [AVISO] Override tenta adicionar '{cliente}' em '{regional}', mas ele já está na lista padrão.")

    if regioes_modificadas:
        print(f"  [OVERRIDE aplicado em {mes_chave}]")
        for log in regioes_modificadas:
            print(f"    {log}")

    return resultado


def gerar_mapa(ano: int) -> dict:
    """
    Gera o mapa completo de 12 meses para o ano informado.

    Args:
        ano: Ano para gerar (ex: 2026).

    Returns:
        Dicionário no formato esperado pelo robô:
        { "AAAA": { "MM-AAAA": { "REGIONAL": ["cliente1", ...] } } }
    """
    config = carregar_config()
    regioes_padrao = config["regioes_padrao"]
    overrides_ano = config.get("overrides", {}).get(str(ano), {})

    mapa_ano = {}
    total_clientes_por_mes = {}

    print(f"\n{'='*60}")
    print(f"  Gerando mapa para o ano {ano}")
    print(f"  Config: {CONFIG_PATH}")
    print(f"{'='*60}")

    for mes in range(1, 13):
        mes_chave = f"{mes:02d}-{ano}"
        regioes_finais = aplicar_overrides(mes_chave, regioes_padrao, overrides_ano)

        # Remove regionais que ficaram vazias após override
        regioes_finais = {reg: clientes for reg, clientes in regioes_finais.items() if clientes}

        mapa_ano[mes_chave] = regioes_finais

        total = sum(len(c) for c in regioes_finais.values())
        total_clientes_por_mes[mes_chave] = total

    print(f"\n  Resumo gerado:")
    for mes_chave, total in total_clientes_por_mes.items():
        override_marker = " [override]" if mes_chave in overrides_ano else ""
        print(f"    {mes_chave}: {total} cliente(s){override_marker}")

    return {str(ano): mapa_ano}


def salvar_mapa(mapa: dict, ano: int) -> str:
    """Salva o mapa gerado no arquivo JSON do projeto."""
    output_path = os.path.join(BASE_DIR, "config", f"sharepoint_map_{ano}.json")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapa, f, ensure_ascii=False, indent=4)

    return output_path


def validar_coerencia(mapa: dict, ano: int, config: dict):
    """
    Verificações de coerência pós-geração.
    Avisa sobre clientes no mapa que não estão no CLIENT_MAPPING do domain/config.py.
    """
    print(f"\n  Verificando coerência com CLIENT_MAPPING...")
    try:
        sys.path.insert(0, BASE_DIR)
        from src.domain.config import CLIENT_MAPPING
        todos_clientes_mapa = set()
        for mes_data in mapa[str(ano)].values():
            for clientes in mes_data.values():
                todos_clientes_mapa.update(clientes)

        sem_mapeamento = [c for c in todos_clientes_mapa if c not in CLIENT_MAPPING]
        if sem_mapeamento:
            print(f"  [AVISO] Os seguintes clientes estao no mapa mas NAO tem mapeamento em")
            print(f"          src/domain/config.py -> CLIENT_MAPPING:")
            for c in sorted(sem_mapeamento):
                print(f"    [!] '{c}'  (sem pasta destino no Drive Z:)")
            print(f"  -> Adicione esses clientes ao CLIENT_MAPPING antes de executar o robo.")
        else:
            print(f"  [OK] Todos os {len(todos_clientes_mapa)} cliente(s) tem mapeamento em CLIENT_MAPPING.")
    except ImportError:
        print("  [AVISO] Não foi possível importar CLIENT_MAPPING para validação. Execute dentro do projeto.")


def main():
    parser = argparse.ArgumentParser(
        description="Gera o mapa mensal do SharePoint para todos os 12 meses de um ano.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/generate_map.py --ano 2026
  python scripts/generate_map.py --ano 2027
  python scripts/generate_map.py              # usa o ano atual

Para adicionar um novo cliente:
  1. Edite config_clientes.json → regioes_padrao → adicione na regional correta.
  2. Se a empresa ainda não existia em meses anteriores, use 'overrides' com 'remover'.
  3. Execute este script novamente para regenerar o JSON.
        """
    )
    parser.add_argument(
        "--ano",
        type=int,
        default=datetime.datetime.now().year,
        help="Ano a gerar (padrão: ano atual)"
    )
    args = parser.parse_args()

    mapa = gerar_mapa(args.ano)
    output_path = salvar_mapa(mapa, args.ano)

    config = carregar_config()
    validar_coerencia(mapa, args.ano, config)

    print(f"\n{'='*60}")
    print(f"  [OK] Mapa gerado com sucesso!")
    print(f"  Arquivo: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
