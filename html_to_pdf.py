#!/usr/bin/env python3
"""
html_to_pdf.py — Converte HTML em PDF com fidelidade visual total.

Usa Playwright (Chromium headless) para tirar screenshots de cada seção
do HTML e depois combina tudo em um PDF usando Pillow.

Dependências:
    pip install playwright Pillow
    python -m playwright install chromium

Uso:
    # Auto-detecta seções (section, header, main, footer, [data-section])
    python html_to_pdf.py pagina.html

    # Especifica seletores CSS manualmente
    python html_to_pdf.py pagina.html -s ".hero" ".about" ".pricing" "footer"

    # Configura largura do viewport e escala
    python html_to_pdf.py pagina.html --width 1440 --scale 2

    # Define o nome do PDF de saída
    python html_to_pdf.py pagina.html -o proposta.pdf

    # Mantém os screenshots temporários
    python html_to_pdf.py pagina.html --keep-screenshots
"""

import argparse
import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Erro: playwright não está instalado.")
    print("Instale com: pip install playwright && python -m playwright install chromium")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Erro: Pillow não está instalado.")
    print("Instale com: pip install Pillow")
    sys.exit(1)


# CSS/JS injetado para forçar visibilidade de todos os elementos
FORCE_VISIBLE_SCRIPT = """
() => {
    // 1. Força elementos com classe .reveal, .hidden, .invisible, [data-aos], etc.
    const hiddenSelectors = [
        '.reveal', '.hidden', '.invisible', '.fade-in', '.fade-up',
        '.slide-in', '.slide-up', '.animate-on-scroll', '.scroll-reveal',
        '[data-aos]', '[data-scroll]', '[data-animate]', '[data-reveal]',
        '.wow', '.sr', '.is-hidden', '.not-visible'
    ];

    hiddenSelectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            el.classList.add('visible', 'active', 'show', 'shown', 'appeared', 'in-view', 'aos-animate');
            el.style.opacity = '1';
            el.style.visibility = 'visible';
            el.style.transform = 'none';
            el.style.transition = 'none';
        });
    });

    // 2. Pausa todas as animações CSS
    document.querySelectorAll('*').forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.animationName && style.animationName !== 'none') {
            el.style.animationPlayState = 'paused';
            el.style.animationDelay = '0s';
            el.style.animationDuration = '0s';
        }
    });

    // 3. Remove scroll-behavior smooth (evita problemas)
    document.documentElement.style.scrollBehavior = 'auto';

    // 4. Garante que elementos com opacity em transition ficam visíveis
    document.querySelectorAll('[style*="opacity: 0"], [style*="opacity:0"]').forEach(el => {
        el.style.opacity = '1';
    });

    // 5. Desfixa navbars e elementos fixed/sticky (evita sobreposição no PDF)
    document.querySelectorAll('*').forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.position === 'fixed' || style.position === 'sticky') {
            el.style.position = 'relative';
            el.style.top = 'auto';
            el.style.left = 'auto';
            el.style.right = 'auto';
            el.style.bottom = 'auto';
            el.style.zIndex = 'auto';
        }
    });
}
"""

# Script para auto-detectar seções do HTML
AUTO_DETECT_SCRIPT = """
() => {
    const candidates = [];

    // Prioridade 1: elementos com data-section
    document.querySelectorAll('[data-section]').forEach(el => {
        candidates.push({ selector: `[data-section="${el.dataset.section}"]`, top: el.getBoundingClientRect().top });
    });
    if (candidates.length > 0) return candidates.map(c => c.selector);

    // Prioridade 2: filhos diretos do body que são seções semânticas ou divs grandes
    const validTags = new Set(['SECTION', 'HEADER', 'MAIN', 'FOOTER', 'NAV', 'ARTICLE']);
    const directChildren = Array.from(document.body.children);

    const sections = directChildren.filter(el => {
        if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'LINK') return false;
        const rect = el.getBoundingClientRect();
        // Ignora elementos invisíveis ou muito pequenos
        if (rect.height < 20) return false;
        return true;
    });

    return sections.map((el, i) => {
        // Tenta gerar um seletor CSS único
        if (el.id) return `#${el.id}`;
        if (el.className && typeof el.className === 'string') {
            const cls = el.className.trim().split(/\\s+/)[0];
            if (cls) {
                const matches = document.querySelectorAll(`.${CSS.escape(cls)}`);
                if (matches.length === 1) return `.${cls}`;
            }
        }
        // Fallback: nth-child
        return `body > ${el.tagName.toLowerCase()}:nth-of-type(${
            Array.from(document.body.querySelectorAll(':scope > ' + el.tagName.toLowerCase())).indexOf(el) + 1
        })`;
    });
}
"""


async def detect_sections(page):
    """Auto-detecta os seletores das seções do HTML."""
    selectors = await page.evaluate(AUTO_DETECT_SCRIPT)
    # Valida que cada seletor realmente encontra um elemento
    valid = []
    for sel in selectors:
        count = await page.locator(sel).count()
        if count > 0:
            valid.append(sel)
    return valid


async def screenshot_sections(html_path, selectors, viewport_width, scale, screenshot_dir, font_wait_ms):
    """Abre o HTML e tira screenshot de cada seção."""
    html_uri = Path(html_path).resolve().as_uri()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": viewport_width, "height": 900},
            device_scale_factor=scale,
        )

        print(f"Abrindo: {html_uri}")
        await page.goto(html_uri, wait_until="networkidle")

        # Aguarda fontes carregarem
        print(f"Aguardando fontes ({font_wait_ms}ms)...")
        await page.wait_for_timeout(font_wait_ms)

        # Força visibilidade de todos os elementos
        print("Forçando visibilidade de elementos animados...")
        await page.evaluate(FORCE_VISIBLE_SCRIPT)
        await page.wait_for_timeout(300)

        # Auto-detecta seções se não foram informadas
        if not selectors:
            print("Auto-detectando seções...")
            selectors = await detect_sections(page)
            if not selectors:
                print("Nenhuma seção encontrada. Tirando screenshot da página inteira.")
                path = os.path.join(screenshot_dir, "00_fullpage.png")
                await page.screenshot(path=path, full_page=True)
                await browser.close()
                return [path]
            print(f"Seções encontradas: {len(selectors)}")
            for s in selectors:
                print(f"  - {s}")

        # Screenshot de cada seção
        paths = []
        for i, selector in enumerate(selectors):
            locator = page.locator(selector).first
            try:
                visible = await locator.is_visible()
                if not visible:
                    # Tenta forçar visibilidade
                    await locator.evaluate("el => { el.style.opacity = '1'; el.style.visibility = 'visible'; }")

                safe_name = selector.replace(".", "").replace("#", "").replace(" ", "_").replace(">", "").replace(":", "_").strip("_")
                filename = f"{i:02d}_{safe_name}.png"
                filepath = os.path.join(screenshot_dir, filename)

                await locator.screenshot(path=filepath)
                paths.append(filepath)
                print(f"  [{i+1}/{len(selectors)}] {selector}")
            except Exception as e:
                print(f"  [{i+1}/{len(selectors)}] ERRO em {selector}: {e}")

        await browser.close()
        return paths


def combine_to_pdf(screenshot_paths, output_path):
    """Combina screenshots em um PDF."""
    if not screenshot_paths:
        print("Nenhum screenshot para combinar.")
        return False

    images = []
    for path in screenshot_paths:
        img = Image.open(path).convert("RGB")
        images.append(img)

    images[0].save(
        output_path,
        "PDF",
        resolution=150,
        save_all=True,
        append_images=images[1:],
    )
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Converte HTML em PDF com fidelidade visual total usando screenshots.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("html", help="Caminho para o arquivo HTML")
    parser.add_argument("-o", "--output", help="Caminho do PDF de saída (padrão: mesmo nome do HTML com .pdf)")
    parser.add_argument("-s", "--sections", nargs="+", help="Seletores CSS das seções (auto-detecta se omitido)")
    parser.add_argument("-w", "--width", type=int, default=1440, help="Largura do viewport em pixels (padrão: 1440)")
    parser.add_argument("--scale", type=int, default=2, help="Fator de escala / device pixel ratio (padrão: 2)")
    parser.add_argument("--font-wait", type=int, default=3000, help="Tempo de espera para fontes em ms (padrão: 3000)")
    parser.add_argument("--keep-screenshots", action="store_true", help="Mantém a pasta de screenshots temporários")
    parser.add_argument("--screenshot-dir", help="Diretório para salvar screenshots (padrão: pasta temporária)")

    args = parser.parse_args()

    # Valida input
    html_path = os.path.abspath(args.html)
    if not os.path.isfile(html_path):
        print(f"Erro: arquivo não encontrado: {html_path}")
        sys.exit(1)

    # Define output
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        output_path = os.path.splitext(html_path)[0] + ".pdf"

    # Diretório de screenshots
    if args.screenshot_dir:
        screenshot_dir = os.path.abspath(args.screenshot_dir)
        os.makedirs(screenshot_dir, exist_ok=True)
        cleanup = False
    elif args.keep_screenshots:
        screenshot_dir = os.path.join(os.path.dirname(output_path), "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        cleanup = False
    else:
        screenshot_dir = tempfile.mkdtemp(prefix="html2pdf_")
        cleanup = True

    print(f"HTML:        {html_path}")
    print(f"PDF:         {output_path}")
    print(f"Viewport:    {args.width}px (scale {args.scale}x)")
    print(f"Screenshots: {screenshot_dir}")
    print()

    # Executa
    paths = asyncio.run(
        screenshot_sections(
            html_path=html_path,
            selectors=args.sections,
            viewport_width=args.width,
            scale=args.scale,
            screenshot_dir=screenshot_dir,
            font_wait_ms=args.font_wait,
        )
    )

    print()
    if combine_to_pdf(paths, output_path):
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"PDF gerado com sucesso!")
        print(f"  Arquivo: {output_path}")
        print(f"  Paginas: {len(paths)}")
        print(f"  Tamanho: {size_mb:.1f} MB")
    else:
        print("Falha ao gerar o PDF.")
        sys.exit(1)

    # Cleanup
    if cleanup:
        shutil.rmtree(screenshot_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
