"""Extrai blocos mermaid dos .md em docs/, renderiza via mmdc e insere img após cada bloco."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DOCS = Path(__file__).parent
IMG = DOCS / "img"
IMG.mkdir(exist_ok=True)

MERMAID_BLOCK = re.compile(r'(```mermaid\n(.*?)```)', re.DOTALL)
IMG_TAG = re.compile(r'\n!\[diagrama\]\(img/[^)]+\.svg\)\n', re.DOTALL)

docs = [
    "README.md", "arquitetura.md", "design-patterns.md", "modulos.md",
    "regras-de-negocio.md", "operacoes.md", "onboarding.md",
    "CHANGELOG.md", "ROADMAP.md", "glossario.md",
]

errors = []

for doc in docs:
    path = DOCS / doc
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")

    # remove img tags já inseridos anteriormente
    text = IMG_TAG.sub("\n", text)

    matches = list(MERMAID_BLOCK.finditer(text))
    if not matches:
        continue

    offset = 0
    new_text = text
    for i, m in enumerate(matches):
        slug = doc.replace(".md", "").replace("-", "_")
        svg_name = f"{slug}_{i+1}.svg"
        svg_path = IMG / svg_name

        # arquivo .mmd temporário no diretório temp do Windows
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False,
                                         encoding="utf-8") as tmp:
            tmp.write(m.group(2))
            mmd_path = tmp.name

        result = subprocess.run(
            f'npx @mermaid-js/mermaid-cli -i "{mmd_path}" -o "{svg_path}"',
            shell=True, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ERRO {doc} diagrama {i+1}:\n{result.stderr[-400:]}")
            errors.append((doc, i+1, result.stderr[-400:]))
            continue

        # remove cor de fundo fixa do SVG
        svg_text = svg_path.read_text(encoding="utf-8")
        svg_text = re.sub(r'background(?:-color)?:\s*[^;]+;', "", svg_text)
        svg_path.write_text(svg_text, encoding="utf-8")

        img_tag = f"\n![diagrama](img/{svg_name})\n"
        ins_pos = m.end() + offset
        new_text = new_text[:ins_pos] + img_tag + new_text[ins_pos:]
        offset += len(img_tag)
        print(f"  OK  {doc} -> img/{svg_name}")

    path.write_text(new_text, encoding="utf-8")

if errors:
    print("\nERROS:")
    for doc, n, msg in errors:
        print(f"  {doc} #{n}: {msg}")
    sys.exit(1)
else:
    print("\nTodos os diagramas renderizados com sucesso.")
