"""Entry point — run with: python main.py"""
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from config.settings import settings
from src.bot import create_app

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)


def _start_health_server() -> None:
    """Bind to $PORT so Render's Web Service health-check passes (polling mode)."""
    port = int(os.environ.get("PORT", 8080))

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, *args):  # silence access logs
            pass

    server = HTTPServer(("0.0.0.0", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logging.getLogger(__name__).info("Health-check server listening on port %s", port)


if __name__ == "__main__":
    import asyncio

    settings.validate()
    app = create_app()
    # Python 3.12+ / 3.14 requires an explicit event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    port = int(os.environ.get("PORT", 8080))
    if settings.webhook_url:
        # Webhook mode wakes quickly on Render when Telegram sends a request.
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=settings.webhook_path,
            webhook_url=f"{settings.webhook_url.rstrip('/')}/{settings.webhook_path.lstrip('/')}",
            drop_pending_updates=True,
            secret_token=settings.webhook_secret or None,
        )
    else:
        # Polling fallback for local/dev usage.
        _start_health_server()
        app.run_polling(drop_pending_updates=True)
