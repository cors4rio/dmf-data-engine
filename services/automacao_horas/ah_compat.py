"""
Shim de compatibilidade para os módulos do service automacao_horas.

Os módulos obtinham db, estado_sh, PROJECT_ROOT e window via:
    import dmf_engine.main as _main

Aqui fornecemos as mesmas refs sem depender do dmf_engine. Apenas troque:
    import dmf_engine.main as _main  →  import compat as _main
"""
import os

from ah_engine.database import db                        # noqa: F401
from ah_engine import estado_compartilhado as estado_sh  # noqa: F401

# Raiz do projeto: este arquivo está em services/automacao_horas/
# services/automacao_horas/compat.py → automacao_horas/ → services/ → repo root (3 dirname)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Preenchido por main.py após webview.create_window() — referência mutável
# que os módulos acessam em tempo de execução (não no import).
window = None
