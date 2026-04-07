"""
Application wiring and the central process_job coroutine.

process_job is defined here (not in handlers) because it needs access to
download_queue and the bot instance — both of which live at this level.
"""
import logging
import asyncio

from telegram import Message
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config.settings import settings
from helper.file_utils import cleanup_files, get_user_download_dir
from helper.user_store import get_lang
from src.downloader import download_audio, download_video
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

    async def _keep_uploading(bot, chat_id: int, action, stop_event: asyncio.Event):
        """Send chat action every 4s until stop_event is set."""
        while not stop_event.is_set():
            try:
                await bot.send_chat_action(chat_id=chat_id, action=action)
            except Exception:
                pass
            await asyncio.sleep(4)

    async def process_job(job: DownloadJob) -> None:
        bot = bot_app.bot
        lang = await get_lang(job.user_id)
        msg = Msg(lang)
        status_msg: Message = await bot.send_message(
            chat_id=job.chat_id,
            text=(
                msg.downloading_audio(job.label)
                if job.quality == "audio"
                else msg.downloading(job.label, job.quality)
            ),
        )
        try:
            # Batch save-locally jobs use the user-chosen folder; single jobs use temp dir
            output_dir = (
                job.save_dir
                if job.save_locally and job.save_dir
                else get_user_download_dir(job.user_id)
            )

            # Show continuous upload action while downloading
            stop_action = asyncio.Event()
            action = ChatAction.RECORD_VOICE if job.quality == "audio" else ChatAction.UPLOAD_VIDEO
            action_task = asyncio.create_task(
                _keep_uploading(bot, job.chat_id, action, stop_action)
            )

            try:
                if job.quality == "audio":
                    audio_path = await download_audio(job.url, output_dir)
                else:
                    files, content_type = await download_video(job.url, job.quality, output_dir)
            finally:
                stop_action.set()
                action_task.cancel()

            if job.quality == "audio":
                if job.save_locally:
                    await bot.send_message(
                        chat_id=job.chat_id,
                        text=msg.saved_file(job.label, output_dir),
                        parse_mode="Markdown",
                    )
                else:
                    with open(audio_path, "rb") as f:
                        await bot.send_audio(
                            chat_id=job.chat_id,
                            audio=f,
                            caption=msg.audio_caption(job.label),
                        )
                    cleanup_files([audio_path])
            else:
                if job.save_locally:
                    await bot.send_message(
                        chat_id=job.chat_id,
                        text=msg.saved_file(job.label, output_dir),
                        parse_mode="Markdown",
                    )
                elif content_type == "photo":
                    await bot.send_message(
                        chat_id=job.chat_id,
                        text=msg.sending_photos(job.label, len(files)),
                    )
                    from telegram import InputMediaPhoto
                    media = [
                        InputMediaPhoto(
                            media=open(p, "rb"),
                            caption=msg.photo_caption(job.label, i, len(files)),
                        )
                        for i, p in enumerate(files, start=1)
                    ]
                    await bot.send_media_group(chat_id=job.chat_id, media=media)
                    for m in media:
                        m.media.close()  # type: ignore[union-attr]
                    cleanup_files(files)
                elif len(files) == 1:
                    with open(files[0], "rb") as f:
                        await bot.send_video(
                            chat_id=job.chat_id,
                            video=f,
                            caption=msg.video_caption(job.label, job.quality),
                            supports_streaming=True,
                        )
                    cleanup_files(files)
                else:
                    await bot.send_message(
                        chat_id=job.chat_id,
                        text=msg.sending_parts(job.label, len(files)),
                    )
                    for idx, part in enumerate(files, start=1):
                        with open(part, "rb") as f:
                            await bot.send_video(
                                chat_id=job.chat_id,
                                video=f,
                                caption=msg.part_caption(job.label, idx, len(files), job.quality),
                                supports_streaming=True,
                            )
                    cleanup_files(files)

        except Exception as exc:
            logger.exception("process_job failed for %s: %s", job.job_id, exc)
            await bot.send_message(
                chat_id=job.chat_id,
                text=msg.download_failed(job.label, str(exc)),
            )
        finally:
            try:
                await status_msg.delete()
            except Exception:
                pass

    return process_job


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> Application:
    from src.handlers.commands import cmd_start, cmd_status, cmd_stats
    from src.handlers.messages import handle_text, handle_document
    from src.handlers.callbacks import handle_quality_callback, handle_folder_callback
    from src.handlers.language import cmd_language, handle_language_callback

    app = Application.builder().token(settings.bot_token).build()

    # Wire the real process_job closure (has bot reference)
    _process_job = _make_process_job(app)

    # Patch the module-level reference used by callbacks.py
    import src.bot as _self
    _self.process_job = _process_job  # type: ignore[assignment]

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), handle_document))
    app.add_handler(CallbackQueryHandler(handle_quality_callback, pattern=r"^quality_"))
    app.add_handler(CallbackQueryHandler(handle_folder_callback, pattern=r"^folder_"))
    app.add_handler(CallbackQueryHandler(handle_language_callback, pattern=r"^lang_"))

    # Lifecycle hooks
    async def on_startup(application: Application) -> None:
        await download_queue.start()
        from telegram import BotCommand
        await application.bot.set_my_commands([
            BotCommand("start", "Show welcome message & instructions"),
            BotCommand("status", "Show how many downloads are in progress"),
            BotCommand("stats", "Show total users and downloads"),
            BotCommand("language", "Change language / ប្ដូរភាសា"),
        ])
        if settings.broadcast_on_start:
            from helper.user_store import get_all_users, get_lang as _get_lang
            users = await get_all_users()
            logger.info("Broadcasting back-online message to %d users", len(users))
            for user in users:
                uid = user.get("_id") or user.get("user_id")
                if not uid:
                    continue
                try:
                    lang = await _get_lang(uid)
                    from ui.templates import Msg as _Msg
                    await application.bot.send_message(
                        chat_id=uid,
                        text=_Msg(lang).BACK_ONLINE,
                        parse_mode="Markdown",
                    )
                    await asyncio.sleep(0.05)  # stay within Telegram rate limits
                except Exception as e:
                    logger.warning("Broadcast failed for user %s: %s", uid, e)

    async def on_shutdown(application: Application) -> None:
        await download_queue.stop()

    app.post_init = on_startup      # type: ignore[method-assign]
    app.post_shutdown = on_shutdown  # type: ignore[method-assign]

    return app
