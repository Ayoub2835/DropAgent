"""Generador de landing pages HTML optimizadas para conversión.

Por cada producto aprobado (creado con éxito en Shopify), genera una
página de aterrizaje HTML independiente y autocontenida (CSS/JS inline,
sin dependencias externas), con hero section, descripción persuasiva,
precio con descuento simulado, botón de compra hacia Shopify, beneficios,
testimonios generados por IA, garantía y urgencia. Se guarda en
`landing_pages/<slug>.html`.

Este generador no depende de ninguna API externa de pago: los testimonios
usan Claude si está configurado (con plantilla local de respaldo), así
que siempre puede ejecutarse sin gastar en APIs.
"""

from __future__ import annotations

import html
import random
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional

from .aliexpress_scraper import Product
from .claude_generator import ClaudeDescriptionGenerator, GeneratedCopy
from .config import config
from .notifier import notifier
from .shopify_manager import ShopifyResult
from .utils import slugify

DEFAULT_BENEFITS = [
    "Envío rápido y seguimiento incluido en todos los pedidos",
    "Calidad verificada por miles de clientes satisfechos",
    "Pago 100% seguro y protegido",
    "Atención al cliente disponible para cualquier duda",
]

PAGE_TEMPLATE = Template("""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>
  :root {
    --accent: #ff5722;
    --accent-dark: #e64a19;
    --bg: #ffffff;
    --text: #1a1a1a;
    --muted: #6b7280;
    --card-bg: #f8f9fb;
    --success: #16a34a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: var(--text);
    background: var(--bg);
    line-height: 1.5;
  }
  img { max-width: 100%; display: block; }
  .container { max-width: 640px; margin: 0 auto; padding: 0 20px; }

  .urgency-banner {
    background: var(--accent);
    color: #fff;
    text-align: center;
    padding: 10px 16px;
    font-weight: 600;
    font-size: 14px;
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .hero { padding: 32px 0 16px; text-align: center; }
  .hero img {
    border-radius: 16px;
    margin: 0 auto 20px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  }
  .hero h1 { font-size: 26px; margin-bottom: 12px; }
  .description { color: var(--muted); font-size: 16px; margin-bottom: 20px; text-align: left; }
  .description ul { padding-left: 20px; margin-top: 8px; }

  .price-box {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 10px;
    margin: 16px 0;
  }
  .price-original { color: var(--muted); text-decoration: line-through; font-size: 18px; }
  .price-final { color: var(--accent-dark); font-size: 34px; font-weight: 800; }
  .discount-badge {
    background: #fee2e2;
    color: #dc2626;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
  }

  .countdown {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin: 16px 0;
    font-variant-numeric: tabular-nums;
  }
  .countdown div { background: var(--text); color: #fff; border-radius: 8px; padding: 8px 12px; min-width: 56px; text-align: center; }
  .countdown span { display: block; font-size: 22px; font-weight: 700; }
  .countdown small { font-size: 10px; color: #ccc; }

  .cta-button {
    display: block;
    width: 100%;
    text-align: center;
    background: var(--accent);
    color: #fff;
    font-weight: 700;
    font-size: 18px;
    padding: 16px 24px;
    border-radius: 12px;
    text-decoration: none;
    margin: 20px 0 8px;
    transition: background 0.2s ease;
  }
  .cta-button:hover { background: var(--accent-dark); }
  .stock-note { text-align: center; color: var(--muted); font-size: 13px; margin-bottom: 24px; }

  section { padding: 28px 0; border-top: 1px solid #eee; }
  section h2 { font-size: 20px; margin-bottom: 16px; text-align: center; }

  .benefits { list-style: none; }
  .benefits li { display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; font-size: 15px; }
  .benefits li::before { content: "\\2713"; color: var(--success); font-weight: 900; }

  .testimonials { display: grid; gap: 14px; }
  .testimonial { background: var(--card-bg); border-radius: 12px; padding: 16px; }
  .testimonial .stars { color: #f59e0b; margin-bottom: 6px; }
  .testimonial p { font-style: italic; margin-bottom: 8px; }
  .testimonial .name { font-size: 13px; color: var(--muted); font-weight: 600; }

  .guarantee { text-align: center; background: #ecfdf5; border-radius: 12px; padding: 20px; }
  .guarantee h3 { color: #047857; margin-bottom: 6px; }
  .guarantee p { color: var(--muted); font-size: 14px; }

  footer { text-align: center; padding: 24px 0; color: var(--muted); font-size: 12px; }

  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14161a; --text: #f2f2f2; --muted: #a3a3a3; --card-bg: #1f2229;
    }
    section { border-top-color: #2a2d35; }
    .discount-badge { background: #451a1a; color: #fca5a5; }
    .guarantee { background: #0d2b21; }
    .guarantee h3 { color: #34d399; }
  }
</style>
</head>
<body>
  <div class="urgency-banner">Oferta especial termina pronto - envio gratis hoy</div>

  <div class="container">
    <div class="hero">
      <img src="$image_url" alt="$title">
      <h1>$title</h1>
      <div class="description">$description_html</div>

      <div class="price-box">
        <span class="price-original">$$$original_price</span>
        <span class="price-final">$$$final_price</span>
        <span class="discount-badge">-$discount_percent%</span>
      </div>

      <div class="countdown" id="countdown">
        <div><span id="cd-hours">24</span><small>HORAS</small></div>
        <div><span id="cd-minutes">00</span><small>MIN</small></div>
        <div><span id="cd-seconds">00</span><small>SEG</small></div>
      </div>

      <a class="cta-button" href="$buy_url" target="_blank" rel="noopener">Comprar ahora</a>
      <p class="stock-note">Solo quedan $stock_left unidades a este precio</p>
    </div>

    <section>
      <h2>Beneficios</h2>
      <ul class="benefits">$benefits_html</ul>
    </section>

    <section>
      <h2>Lo que dicen nuestros clientes</h2>
      <div class="testimonials">$testimonial_cards</div>
    </section>

    <section>
      <div class="guarantee">
        <h3>Garantia de 30 dias</h3>
        <p>Si no quedas satisfecho, te devolvemos tu dinero. Sin preguntas.</p>
      </div>
    </section>

    <footer>Generado automáticamente por DropAgent</footer>
  </div>

  <script>
    (function () {
      var deadline = Date.now() + 24 * 60 * 60 * 1000;
      function update() {
        var diff = Math.max(0, deadline - Date.now());
        var h = Math.floor(diff / 3600000);
        var m = Math.floor((diff % 3600000) / 60000);
        var s = Math.floor((diff % 60000) / 1000);
        document.getElementById('cd-hours').textContent = String(h).padStart(2, '0');
        document.getElementById('cd-minutes').textContent = String(m).padStart(2, '0');
        document.getElementById('cd-seconds').textContent = String(s).padStart(2, '0');
      }
      update();
      setInterval(update, 1000);
    })();
  </script>
</body>
</html>
""")


@dataclass
class LandingPageResult:
    success: bool
    file_path: Optional[str] = None
    url_slug: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "file_path": self.file_path,
            "url_slug": self.url_slug,
            "error": self.error,
        }


class LandingPageGenerator:
    """Genera landing pages HTML persuasivas por producto."""

    def __init__(self):
        self.output_dir = Path(config.landing_pages_output_dir)
        self.generator = ClaudeDescriptionGenerator()

    def generate(
        self,
        product: Product,
        copy: GeneratedCopy,
        shopify_result: ShopifyResult,
        buy_url: str,
    ) -> LandingPageResult:
        try:
            testimonials = self.generator.generate_testimonials(product, count=3)
            original_price, final_price, discount_percent = self._pricing(shopify_result.price)
            stock_left = random.randint(3, max(4, config.landing_page_max_stock))

            html_content = self._render(
                product=product,
                copy=copy,
                buy_url=buy_url,
                original_price=original_price,
                final_price=final_price,
                discount_percent=discount_percent,
                stock_left=stock_left,
                testimonials=testimonials,
            )

            self.output_dir.mkdir(parents=True, exist_ok=True)
            slug = slugify(copy.title or product.title)
            file_path = self.output_dir / f"{slug}.html"
            file_path.write_text(html_content, encoding="utf-8")

            notifier.success(
                "landing_page",
                f"Landing page generada para '{copy.title}' -> {file_path}",
            )
            return LandingPageResult(success=True, file_path=str(file_path), url_slug=slug)
        except Exception as exc:  # noqa: BLE001 - degradar sin romper el pipeline
            notifier.error(
                "landing_page",
                f"Error al generar landing page para '{copy.title}': {exc}",
            )
            return LandingPageResult(success=False, error=str(exc))

    @staticmethod
    def _pricing(final_price: float):
        discount_percent = config.landing_page_discount_percent
        divisor = 1 - (discount_percent / 100)
        original_price = round(final_price / divisor, 2) if divisor > 0 else final_price
        return original_price, final_price, discount_percent

    def _render(
        self,
        *,
        product: Product,
        copy: GeneratedCopy,
        buy_url: str,
        original_price: float,
        final_price: float,
        discount_percent: float,
        stock_left: int,
        testimonials: List[Dict[str, Any]],
    ) -> str:
        title = html.escape(copy.title or product.title)
        image_url = html.escape(product.image_url or "https://via.placeholder.com/600x600?text=Producto")
        safe_buy_url = html.escape(buy_url, quote=True)

        benefits_html = "".join(f"<li>{html.escape(b)}</li>" for b in DEFAULT_BENEFITS)

        testimonial_cards = "".join(
            f'<div class="testimonial">'
            f'<div class="stars">{"&#9733;" * int(t.get("rating", 5))}{"&#9734;" * (5 - int(t.get("rating", 5)))}</div>'
            f'<p>&ldquo;{html.escape(str(t.get("text", "")))}&rdquo;</p>'
            f'<span class="name">{html.escape(str(t.get("name", "Cliente verificado")))}</span>'
            f"</div>"
            for t in testimonials
        )

        return PAGE_TEMPLATE.substitute(
            title=title,
            image_url=image_url,
            description_html=copy.description_html,
            original_price=f"{original_price:.2f}",
            final_price=f"{final_price:.2f}",
            discount_percent=int(discount_percent),
            buy_url=safe_buy_url,
            stock_left=stock_left,
            benefits_html=benefits_html,
            testimonial_cards=testimonial_cards,
        )


def get_landing_page_generator() -> LandingPageGenerator:
    return LandingPageGenerator()
