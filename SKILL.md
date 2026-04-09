# HTML to PDF — Conversão com fidelidade visual total

Converte arquivos HTML em PDF preservando 100% da aparência visual: gradientes, sombras, backdrop-filter, fontes web, layouts complexos.

## Como funciona

Em vez de renderizadores PDF tradicionais (que perdem estilos visuais), esta ferramenta:

1. Abre o HTML num **Chromium real** via Playwright
2. Aguarda **fontes web** carregarem
3. **Força visibilidade** de elementos animados (scroll-reveal, AOS, GSAP, fade-in, etc.)
4. **Desfixa elementos sticky/fixed** (navbars, botões flutuantes, banners) para evitar sobreposição
5. **Auto-detecta seções** do HTML (`<section>`, `<header>`, `<footer>`, `[data-section]`)
5. **Tira screenshot** de cada seção individualmente
6. **Combina em PDF** via Pillow (uma página por seção)

## Dependências

```bash
pip install playwright Pillow
python -m playwright install chromium
```

## Uso via CLI

```bash
# Auto-detecta seções
python html_to_pdf.py pagina.html

# Define saída
python html_to_pdf.py pagina.html -o proposta.pdf

# Especifica seções manualmente
python html_to_pdf.py pagina.html -s ".hero" ".about" ".pricing" "footer"

# Alta qualidade
python html_to_pdf.py pagina.html --width 1920 --scale 3

# Mantém screenshots
python html_to_pdf.py pagina.html --keep-screenshots
```

## Opções

| Argumento            | Padrão | Descrição                             |
|----------------------|--------|---------------------------------------|
| `html`               | —      | Caminho do arquivo HTML (obrigatório) |
| `-o`, `--output`     | auto   | Caminho do PDF de saída               |
| `-s`, `--sections`   | auto   | Seletores CSS das seções              |
| `-w`, `--width`      | 1440   | Largura do viewport (px)              |
| `--scale`            | 2      | Device pixel ratio                    |
| `--font-wait`        | 3000   | Espera para fontes web (ms)           |
| `--keep-screenshots` | false  | Mantém screenshots temporários        |
| `--screenshot-dir`   | temp   | Diretório para screenshots            |

## Instruções para LLMs

Se você é uma IA assistente e o usuário quer converter HTML em PDF:

1. **Verifique dependências**: `pip install playwright Pillow && python -m playwright install chromium`
2. **HTML com seções semânticas** (`<section>`, `<header>`, etc.)? Rode sem `-s`, o auto-detect funciona.
3. **HTML só com `<div>`?** Leia o HTML, identifique os seletores das seções principais e passe com `-s`.
4. **Animações** (reveal, AOS, GSAP)? O script já neutraliza automaticamente.
5. **Navbar fixa/sticky atrapalhando?** Já é tratado — elementos `position: fixed/sticky` são convertidos para `relative` automaticamente.
5. **Qualidade máxima?** Use `--scale 3 --width 1920`.
6. **Quer revisar antes de gerar o PDF?** Use `--keep-screenshots` e verifique as imagens.

### Exemplo completo

```bash
python html_to_pdf.py proposta.html \
  -s ".hero" ".features" ".pricing" ".cta" "footer" \
  -o proposta-final.pdf \
  --width 1440 --scale 2
```
