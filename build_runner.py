#!/usr/bin/env python3
"""
Build runner para DMF Engine — executa PyInstaller com dmf_engine.spec
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path

def main():
    print("="*70)
    print("DMF Engine Build Runner")
    print("="*70)

    # Verificar pre-requisitos
    print("\n[1] Verificando pre-requisitos...")
    if not shutil.which("pyinstaller"):
        print("  ERRO: PyInstaller nao encontrado")
        print("  Instale: py -3-32 -m pip install pyinstaller")
        return 1
    print("  OK: PyInstaller encontrado")

    # Executar PyInstaller
    print("\n[2] Executando PyInstaller...")
    spec_file = Path("dmf_engine.spec")
    if not spec_file.exists():
        print(f"  ERRO: {spec_file} nao encontrado")
        return 1

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "-y", str(spec_file)],
        cwd=Path.cwd()
    )

    if result.returncode != 0:
        print("  ERRO: PyInstaller falhou")
        return 1

    print("  OK: Build completado")

    # Verificar resultado
    print("\n[3] Verificando arquivos de saida...")
    dist_path = Path("dist/DMF Engine")
    exe_path = dist_path / "DMF Engine.exe"

    if not exe_path.exists():
        print(f"  ERRO: {exe_path} nao foi criado")
        return 1

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"  OK: DMF Engine.exe criado ({size_mb:.1f} MB)")

    # Copiar arquivos adicionais
    print("\n[4] Copiando arquivos de configuracao...")
    config_src = Path("config/nao_faz_setor")
    config_dst = dist_path / "config/nao_faz_setor"

    if config_src.exists():
        config_dst.mkdir(parents=True, exist_ok=True)
        for txt_file in config_src.glob("*.txt"):
            shutil.copy(txt_file, config_dst / txt_file.name)
            print(f"  OK: {txt_file.name}")

    # Copiar instalador
    print("\n[5] Copiando instalador...")
    installer = Path("Instalar DMF Engine.bat")
    if installer.exists():
        shutil.copy(installer, dist_path / installer.name)
        print(f"  OK: {installer.name}")

    # Remover arquivos sensíveis
    print("\n[6] Removendo arquivos sensíveis...")
    sensitive_files = [
        dist_path / "config.json",
        dist_path / "supervisores.json",
        dist_path / "dmf_engine.log",
        dist_path / "dmf_engine_errors.log",
    ]
    for f in sensitive_files:
        if f.exists():
            f.unlink()
            print(f"  OK: {f.name} removido")

    print("\n" + "="*70)
    print("BUILD CONCLUIDO COM SUCESSO!")
    print(f"Executavel: {exe_path}")
    print(f"Tamanho: {size_mb:.1f} MB")
    print("="*70)

    return 0

if __name__ == "__main__":
    sys.exit(main())
