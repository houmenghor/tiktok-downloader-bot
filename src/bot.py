"""
Application wiring and the central process_job coroutine.

process_job is defined here (not in handlers) because it needs access to
download_queue and the bot instance — both of which live at this level.
"""
import logging

from telegram import Message
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config.settings import settings
from helper.file_utils import cleanup_files, get_user_download_dir
from src.downloader import download_video
from src.queue_manager import DownloadJob, DownloadQueue
from ui.templates import Msg

logger = logging.getLogger(__name__)

# ── Shared queue (imported by handlers via lazy import) ───────────────────────
download_queue = DownloadQueue(max_workers=settings.max_workers)


# ── Core job processor ────────────────────────────────────────────────────────

async def process_job(job: DownloadJob) -> None:
    """Download a video and send it (or its parts) back to the user's chat."""
    # We get the bot from the running Application instance
    from telegram.ext import Application as _App
    app = _App.builder().token(settings.bot_token).build()
    # Re-use the already-running application's bot instead of building a new one
    # This is injected properly via the callback closure in create_app().
    raise NotImplementedError("Use the closure version from create_app()")


def _make_process_job(bot_app: Application):
    """Factory that closes over the Application so the bot reference is valid."""

    async def process_job(job: DownloadJob) -> None:
        bot = bot_app.bot
        status_msg: Message = await bot.send_message(
            chat_id=job.chat_id,
            text=Msg.downloading(job.label, job.quality),
        )
        try:
            output_dir = get_user_download_dir(job.user_id)
            files = await download_video(job.url, job.quality, output_dir)

            if len(files) == 1:
                with open(files[0], "rb") as f:
                    await bot.send_video(
                        chat_id=job.chat_id,
                        video=f,
                        caption=Msg.video_caption(job.label, job.quality),
                        supports_streaming=True,
                    )
            else:
                await bot.send_message(
                    chat_id=job.chat_id,
                    text=Msg.sending_parts(job.label, len(files)),
                )
                for idx, part in enumerate(files, start=1):
                    with open(part, "rb") as f:
                        await bot.send_video(
                            chat_id=job.chat_id,
                            video=f,
                            caption=Msg.part_caption(job.label, idx, len(files), job.quality),
                            supports_streaming=True,
                        )

            cleanup_files(files)

        except Exception as exc:
            logger.exception("process_job failed for %s: %s", job.job_id, exc)
            await bot.send_message(
                chat_id=job.chat_id,
                text=Msg.download_failed(job.label, str(exc)),
            )
        finally:
            try:
                await status_msg.delete()
            except Exception:
                pass

    return process_job


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> Application:
    from src.handlers.commands import cmd_start, cmd_queue
    from src.handlers.messages import handle_text, handle_document
    from src.handlers.callbacks import handle_quality_callback

    app = Application.builder().token(settings.bot_token).build()

    # Wire the real process_job closure (has bot reference)
    _process_job = _make_process_job(app)

    # Patch the module-level reference used by callbacks.py
    import src.bot as _self
    _self.process_job = _process_job  # type: ignore[assignment]

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("queue", cmd_queue))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), handle_document))
    app.add_handler(CallbackQueryHandler(handle_quality_callback, pattern=r"^quality_"))

    # Lifecycle hooks
    async def on_startup(application: Application) -> None:
        await download_queue.start()

    async def on_shutdown(application: Application) -> None:
        await download_queue.stop()

    app.post_init = on_startup      # type: ignore[method-assign]
    app.post_shutdown = on_shutdown  # type: ignore[method-assign]

    return app
