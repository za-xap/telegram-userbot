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
        local = utc.to("Europe/Warsaw")  # Kyiv or Warsaw
        local_date = local.format('H:mm')
        local_date = ''.join(digits.get(c, c) for c in local_date)
        if local_date != prew_date:
            await client(functions.account.UpdateProfileRequest(
                about=f"The risk was calculated, but I'm bad at math. My time - {local_date}"))
            prew_date = local_date
        await asyncio.sleep(1)


async def log():  # logger of deleted messages, first group for all incoming messages and second only for deleted
    @client.on(events.NewMessage(incoming=True))
    async def on_new(event):
        try:
            sender = await event.get_sender()
        except Exception:
            return
        me = await client.get_me()
        if sender.bot or event.is_channel or event.sender_id == me.id:
            return
        forwarded = await client.forward_messages(config.LOG_TMP, event.message, silent=True)
        try:
            if sender and sender.id:
                link = f"<a href=\"tg://user?id={sender.id}\">{sender.id}</a>"
                if sender.username:
                    link += f" | @{sender.username}"
                elif sender.first_name or sender.last_name:
                    name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                    link += f" | {name}"
        except Exception:
            link = "unknown"
        await client.send_message(config.LOG_TMP, f"#orig-{event.message.id}\n{link}",  reply_to=forwarded.id,
                                  parse_mode="html", link_preview=False, silent=True)
        await client(functions.account.UpdateStatusRequest(offline=True))

    @client.on(events.MessageDeleted())
    async def on_deleted(event):
        for orig_msg_id in event.deleted_ids:
            msgs = await client.get_messages(config.LOG_TMP, search=f"#orig-{orig_msg_id}", limit=1)
            if not msgs:
                continue
            lines = (msgs[0].message or "").split("\n", 1)
            if "unknown" in lines[1] or not msgs[0].reply_to_msg_id:
                continue
            orig = await client.get_messages(int(lines[1].split()[0]), ids=orig_msg_id)
            if orig:
                continue
            await asyncio.sleep(1.5)  # this and second get_messages below should help with the false positives
            orig = await client.get_messages(int(lines[1].split()[0]), ids=orig_msg_id)
            if orig:
                continue
            await client.forward_messages(config.LOG_FINAL, [msgs[0].reply_to_msg_id, msgs[0].id],
                                          from_peer=config.LOG_TMP)
            await client(functions.account.UpdateStatusRequest(offline=True))


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
    client.loop.create_task(log())
    client.run_until_disconnected()
