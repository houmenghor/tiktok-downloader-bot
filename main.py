"""Entry point — run with: python main.py"""
import logging

from config.settings import settings
from src.bot import create_app

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)

if __name__ == "__main__":
    settings.validate()
    app = create_app()
    app.run_polling(drop_pending_updates=True)
