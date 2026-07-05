#!/usr/bin/env python3
"""DropAgent - Sistema automatizado de dropshipping.

Uso:
    python main.py trending                Busca productos trending en AliExpress
    python main.py create-products          Ejecuta el pipeline completo una vez
                                            (incluye lanzar campaña de TikTok Ads)
    python main.py monitor-ads              Revisa Facebook Ads una sola vez
    python main.py monitor-ads --loop       Revisa Facebook Ads cada 24h (bloqueante)
    python main.py monitor-tiktok-ads       Revisa el ROAS de TikTok Ads una sola vez
    python main.py monitor-tiktok-ads --loop  Revisa TikTok Ads cada 24h (bloqueante)
    python main.py run                      Pipeline completo + ambos monitores en loop
    python main.py history                  Muestra el historial guardado en log.json
"""

from __future__ import annotations

import argparse
import json
import sys

from dropagent.aliexpress_scraper import AliExpressScraper
from dropagent.config import config
from dropagent.facebook_ads_monitor import FacebookAdsMonitor
from dropagent.notifier import notifier
from dropagent.pipeline import DropAgentPipeline
from dropagent.scheduler import run_forever
from dropagent.tiktok_ads_manager import TikTokAdsManager


def cmd_trending(args: argparse.Namespace) -> None:
    scraper = AliExpressScraper()
    keywords = [args.keyword] if args.keyword else config.aliexpress_keywords
    for keyword in keywords:
        products = scraper.get_trending_products(keyword, limit=args.limit)
        for product in products:
            print(f"  - {product.title} | {product.price} {product.currency} "
                  f"| pedidos: {product.orders} | fuente: {product.source}")


def cmd_create_products(args: argparse.Namespace) -> None:
    pipeline = DropAgentPipeline()
    results = pipeline.run_once(max_products=args.max)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_monitor_ads(args: argparse.Namespace) -> None:
    monitor = FacebookAdsMonitor()
    if args.loop:
        monitor.start_scheduler(interval_hours=args.interval, blocking=True)
    else:
        result = monitor.run_check()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_monitor_tiktok_ads(args: argparse.Namespace) -> None:
    manager = TikTokAdsManager()
    if args.loop:
        manager.start_scheduler(interval_hours=args.interval, blocking=True)
    else:
        result = manager.run_check()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_run(args: argparse.Namespace) -> None:
    pipeline = DropAgentPipeline()
    pipeline.run_once()

    fb_monitor = FacebookAdsMonitor()
    fb_monitor.start_scheduler(interval_hours=args.fb_interval, blocking=False)

    tiktok_monitor = TikTokAdsManager()
    tiktok_monitor.start_scheduler(interval_hours=args.tiktok_interval, blocking=False)

    run_forever()


def cmd_history(args: argparse.Namespace) -> None:
    history = notifier.read_history()
    if args.json:
        print(json.dumps(history[-args.limit:], ensure_ascii=False, indent=2))
        return
    for entry in history[-args.limit:]:
        print(f"[{entry['timestamp']}] ({entry['level']}) {entry['event_type']}: {entry['message']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dropagent",
        description="DropAgent - Sistema automatizado de dropshipping",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_trending = subparsers.add_parser("trending", help="Busca productos trending en AliExpress")
    p_trending.add_argument("--keyword", type=str, default=None, help="Palabra clave específica")
    p_trending.add_argument("--limit", type=int, default=5, help="Cantidad de productos a mostrar")
    p_trending.set_defaults(func=cmd_trending)

    p_create = subparsers.add_parser(
        "create-products", help="Busca, describe y publica productos en Shopify"
    )
    p_create.add_argument("--max", type=int, default=None, help="Máximo de productos a crear")
    p_create.add_argument("--json", action="store_true", help="Imprime el resultado en JSON")
    p_create.set_defaults(func=cmd_create_products)

    p_ads = subparsers.add_parser("monitor-ads", help="Revisa el rendimiento de Facebook Ads")
    p_ads.add_argument("--loop", action="store_true", help="Ejecuta en bucle cada N horas")
    p_ads.add_argument("--interval", type=float, default=None, help="Intervalo en horas (default 24)")
    p_ads.add_argument("--json", action="store_true", help="Imprime el resultado en JSON")
    p_ads.set_defaults(func=cmd_monitor_ads)

    p_tiktok = subparsers.add_parser(
        "monitor-tiktok-ads", help="Revisa el ROAS de las campañas de TikTok Ads"
    )
    p_tiktok.add_argument("--loop", action="store_true", help="Ejecuta en bucle cada N horas")
    p_tiktok.add_argument("--interval", type=float, default=None, help="Intervalo en horas (default 24)")
    p_tiktok.add_argument("--json", action="store_true", help="Imprime el resultado en JSON")
    p_tiktok.set_defaults(func=cmd_monitor_tiktok_ads)

    p_run = subparsers.add_parser(
        "run", help="Ejecuta el pipeline completo y deja los monitores de ads corriendo"
    )
    p_run.add_argument("--fb-interval", type=float, default=None,
                        help="Intervalo del monitor de Facebook Ads en horas (default 24)")
    p_run.add_argument("--tiktok-interval", type=float, default=None,
                        help="Intervalo del monitor de TikTok Ads en horas (default 24)")
    p_run.set_defaults(func=cmd_run)

    p_history = subparsers.add_parser("history", help="Muestra el historial de log.json")
    p_history.add_argument("--limit", type=int, default=20, help="Cantidad de eventos a mostrar")
    p_history.add_argument("--json", action="store_true", help="Imprime el resultado en JSON")
    p_history.set_defaults(func=cmd_history)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        notifier.info("dropagent", "Ejecución interrumpida por el usuario")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001 - top-level guard para no romper con traceback
        notifier.error("dropagent", f"Error inesperado: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
