import logging
import os

from common.nats_server import nc
from services.telegram import TelegramBot as t
from services.openai_manager import openai_manager as o
from services.ffmpeg_manager import FFmpegManager as f

logger = logging.getLogger(__name__)

@nc.sub("file.received")
async def handle_file(data: dict = {}):

    message_id = data.get("message_id")
    from_id = data.get("from_id")
    file_path = data.get("file_path")

    audio_path = await f.save_audio(file_path)
    transcription = await o.transcribe(audio_path)

    if not transcription:
        data['error'] = "Oops! Couldn't get that one."
        await nc.pub(
            "send.affirmation",
            data
        )

    data['transcription'] = transcription
    await nc.pub(
        "send.transcription",
        data
    )

    await f.delete_audio(audio_path)

@nc.sub("send.transcription")
async def handle_transcription(data: dict = {}):

    message_id = data.get("message_id")
    from_id = data.get("from_id")
    transcription = data.get("transcription")

    await t.send_message(
        chat_id = from_id,
        text = transcription,
        reply_parameters = {
            "message_id": message_id
        }
    )

@nc.sub("send.affirmation")
async def handle_affirmation(data: dict = {}):

    message_id = data.get("message_id")
    from_id = data.get("from_id")
    affirmation = await o.affirmation()

    await t.send_message(
        chat_id = from_id,
        text = affirmation,
        reply_parameters = {
            "message_id": message_id
        }
    )