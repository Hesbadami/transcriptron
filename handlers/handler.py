import logging
import os

from common.nats_server import nc
from services.gemini import gemini_manager as g
from services.telegram import TelegramBot as t
from services.openai_manager import openai_manager as o
from services.ffmpeg_manager import FFmpegManager as f

logger = logging.getLogger(__name__)
CHUNK_SIZE = 4000

def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks = []
    while text:
        if len(text) <= size:
            chunks.append(text)
            break
        split = text.rfind(" ", 0, size)
        if split == -1:
            split = size
        chunks.append(text[:split])
        text = text[split:].lstrip()
    return chunks

@nc.sub("file.received")
async def handle_file(data: dict = {}):

    message_id = data.get("message_id")
    from_id = data.get("from_id")
    file_path = data.get("file_path")

    audio_path = await f.save_audio(file_path)
    if not audio_path:
        data['error'] = "Oops! Couldn't get that one."
        await nc.pub("send.affirmation", data)
        return

    transcription = await o.transcribe(audio_path)
    if not transcription:
        data['error'] = "Oops! Couldn't get that one."
        await nc.pub("send.affirmation", data)
        return

    for part in chunk_text(transcription):
        await nc.pub("send.transcription", {**data, "transcription": part})

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

@nc.sub("text.received")
async def handle_text(data: dict = {}):

    message_id = data.get("message_id")
    from_id = data.get("from_id")
    text = data.get("text")

    rewrite = await g.correct_text(text)
    if not rewrite:
        rewrite = "Oops! Couldn't rewrite that one."

    await t.send_message(
        chat_id = from_id,
        text = rewrite,
        reply_parameters = {
            "message_id": message_id
        }
    )