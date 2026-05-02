from telethon import functions, TelegramClient, events
from telethon.tl.types import MessageEntityMentionName, Message
from datetime import timedelta, timezone
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
    digits = str.maketrans("0123456789", "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵")
    while True:
        utc = arrow.utcnow()
        local = utc.to("Europe/Warsaw")  # Kyiv or Warsaw
        local_date = local.format('H:mm').translate(digits)
        if local_date != prew_date:
            await client(functions.account.UpdateProfileRequest(
                about=f"The risk was calculated, but I'm bad at math. My time - {local_date}"))
            prew_date = local_date
        await asyncio.sleep(1)


def same_media(a, b) -> bool:
    if not a or not b:
        return False
    if a.photo and b.photo:
        return a.photo.id == b.photo.id
    if a.document and b.document:
        return a.document.id == b.document.id
    return False


async def log():  # logger of deleted messages, first group for all incoming messages and second only for deleted
    @client.on(events.NewMessage(incoming=True))
    async def on_new(event):
        try:
            sender = await event.get_sender()
        except Exception:
            return
        me = await client.get_me()
        if event.is_channel or not hasattr(sender, 'bot') or sender.bot or event.sender_id == me.id:
            return
        forwarded = await client.forward_messages(config.LOG_TMP, event.message, silent=True)
        if sender.username:
            label = f"@{sender.username}"
        elif sender.first_name or sender.last_name:
            label = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
        else:
            label = str(sender.id)
        tag = "#text" if event.message.text else "#media"
        prefix = f"#orig-{event.message.id}\n"
        body = prefix + label + f"\n{tag}\n#{sender.id}"
        mention_offset = len(prefix.encode('utf-16-le')) // 2
        mention_length = len(label.encode('utf-16-le')) // 2
        mention = MessageEntityMentionName(offset=mention_offset, length=mention_length, user_id=sender.id)
        await client.send_message(config.LOG_TMP, body, reply_to=forwarded.id, formatting_entities=[mention],
                                  link_preview=False, silent=True)
        await client(functions.account.UpdateStatusRequest(offline=True))

    @client.on(events.MessageDeleted())
    async def on_deleted(event):
        for orig_msg_id in event.deleted_ids:
            msgs = await client.get_messages(config.LOG_TMP, search=f"#orig-{orig_msg_id}", limit=1)
            if not msgs:
                continue
            lines = (msgs[0].message or "").split("\n")
            if len(lines) < 4 or lines[0].strip() != f"#orig-{orig_msg_id}":
                continue
            if not msgs[0].reply_to_msg_id:
                continue
            is_text = lines[2].strip() == "#text"
            try:
                sender_id = int(lines[3].strip().lstrip("#"))
            except (ValueError, IndexError):
                continue
            try:
                fwd_results = await client.get_messages(config.LOG_TMP, ids=[msgs[0].reply_to_msg_id])
                fwd_msg = fwd_results[0] if fwd_results else None
            except Exception:
                continue
            if not isinstance(fwd_msg, Message) or not fwd_msg.forward or not fwd_msg.forward.date:
                continue
            orig_date = fwd_msg.forward.date.replace(tzinfo=timezone.utc)
            await asyncio.sleep(1.5)
            found = False
            try:
                chat_msgs = await client.get_messages(sender_id, offset_date=orig_date + timedelta(seconds=4), limit=10)
                for msg in (chat_msgs or []):
                    if not msg.date:
                        continue
                    msg_dt = msg.date.replace(tzinfo=timezone.utc)
                    if not (orig_date <= msg_dt <= orig_date + timedelta(seconds=3)):
                        continue
                    if is_text and msg.text and msg.text.strip() == (fwd_msg.text or "").strip():
                        found = True
                        break
                    if not is_text and same_media(fwd_msg, msg):
                        found = True
                        break
            except Exception:
                pass
            if found:
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
