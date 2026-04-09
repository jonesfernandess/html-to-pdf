# HTML to PDF

Converte arquivos HTML ou sites online em PDF preservando 100% da aparência visual: gradientes, sombras, backdrop-filter, fontes web, layouts complexos.

## Como funciona

Em vez de renderizadores PDF tradicionais (que perdem estilos visuais), esta ferramenta:

1. Abre o **HTML local ou URL remota** num **Chromium real** via Playwright
2. Aguarda **fontes web** carregarem
3. **Força visibilidade** de elementos animados (scroll-reveal, AOS, GSAP, fade-in, etc.)
4. **Desfixa elementos sticky/fixed** (navbars, botões flutuantes, banners) para evitar sobreposição
5. **Auto-detecta seções** do HTML (`<section>`, `<header>`, `<footer>`, `[data-section]`)
6. **Tira screenshot** de cada seção individualmente
7. **Combina em PDF** via Pillow (uma página por seção)

## Instalação

```bash
pip install playwright Pillow
python -m playwright install chromium
```

## Uso

### Arquivo local

```bash
# Auto-detecta seções
python html_to_pdf.py pagina.html

# Define nome do PDF de saída
python html_to_pdf.py pagina.html -o proposta.pdf

# Especifica seções manualmente via seletores CSS
python html_to_pdf.py pagina.html -s ".hero" ".about" ".pricing" "footer"
```

### Site online (URL)

```bash
# Converte um site online para PDF
python html_to_pdf.py https://exemplo.com -o exemplo.pdf

# Sem -o, o PDF é nomeado pelo domínio (ex: www_exemplo_com.pdf)
python html_to_pdf.py https://exemplo.com
```

### Qualidade e viewport

```bash
# Viewport mais largo com escala máxima
python html_to_pdf.py pagina.html --width 1920 --scale 3

# Viewport padrão (1440px, escala 2x)
python html_to_pdf.py pagina.html
```

### Screenshots

Por padrão, os screenshots são **temporários** — criados numa pasta temp e deletados após gerar o PDF.

```bash
# Mantém screenshots na pasta "screenshots/" ao lado do PDF
python html_to_pdf.py pagina.html --keep-screenshots

# Salva screenshots em diretório específico
python html_to_pdf.py pagina.html --screenshot-dir ./minhas-imagens
```

## Opções

| Argumento            | Padrão | Descrição                                    |
|----------------------|--------|----------------------------------------------|
| `html`               | —      | Caminho do arquivo HTML ou URL (obrigatório) |
| `-o`, `--output`     | auto   | Caminho do PDF de saída                      |
| `-s`, `--sections`   | auto   | Seletores CSS das seções                     |
| `-w`, `--width`      | 1440   | Largura do viewport (px)                     |
| `--scale`            | 2      | Device pixel ratio                           |
| `--font-wait`        | 3000   | Espera para fontes web (ms)                  |
| `--keep-screenshots` | false  | Mantém screenshots temporários               |
| `--screenshot-dir`   | temp   | Diretório para screenshots                   |

## Exemplo completo

```bash
python html_to_pdf.py proposta.html \
  -s ".hero" ".features" ".pricing" ".cta" "footer" \
  -o proposta-final.pdf \
  --width 1440 --scale 2
```
