from telethon import functions, TelegramClient, events
import arrow
import asyncio
import config
import socket
import urllib.request

client = TelegramClient("telega", config.api_id, config.api_hash)  # api_id and api_hash variables from config.py file


@client.on(events.NewMessage(chats="me", from_users="me", pattern="test"))  # triggers on pattern text in chat from user
async def trigger(event):  # answer with specific text
    await event.reply("test")  # or without reply #await client.send_message("me", "test")


async def main():  # updating bio to text + local time with nice font
    prew_date = "0"
    digits = {
        '0': chr(0x1D7EC), '1': chr(0x1D7ED), '2': chr(0x1D7EE),
        '3': chr(0x1D7EF), '4': chr(0x1D7F0), '5': chr(0x1D7F1),
        '6': chr(0x1D7F2), '7': chr(0x1D7F3), '8': chr(0x1D7F4),
        '9': chr(0x1D7F5),
    }
    while True:
        utc = arrow.utcnow()
        local = utc.to("Europe/Warsaw")  # Kiev or Warsaw
        local_date = local.format('H:mm')
        local_date = ''.join(digits.get(c, c) for c in local_date)
        if local_date != prew_date:
            await client(functions.account.UpdateProfileRequest(
                about=f"The risk was calculated, but I'm bad at math. My time - {local_date}"))
            prew_date = local_date
        await asyncio.sleep(1)


async def downdetector():
    while True:
        try:
            urllib.request.urlopen("https://hc-ping.com/" + config.hc_id, timeout=10)  # hc_id variable from config.py
        except socket.error as e:
            print(f"Ping failed: {e}")
        await asyncio.sleep(30)


with client:
    client.loop.create_task(main())
    client.loop.create_task(downdetector())
    client.run_until_disconnected()
