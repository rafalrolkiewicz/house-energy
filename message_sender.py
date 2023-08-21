"""
Program for sending messages via Telegram.
"""

import telegram
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def send_message_async(text):
    """
    Sends a message asynchronously to the specified chat ID
    using the Telegram bot API.

    Parameters:
    text (str): The message to be sent.

    Returns:
    None
    """
    bot = telegram.Bot(token=TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text)


def send_message(text):
    """
    Sends a message until complete to the specified chat ID
    using send_message_async function.

    Parameters:
    text (str): The message to be sent.

    Returns:
    None
    """
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_message_async(text))

    except:
        print(
            f"{datetime.now().replace(microsecond=0)} \
                Error while sending telegram message"
        )
