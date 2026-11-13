from telethon import functions, TelegramClient, events
from datetime import timedelta, timezone
import arrow
import asyncio
import config
import socket
import urllib.request

client = TelegramClient("telega", config.api_id, config.api_hash)  # api_id and api_hash variables from config.py file

pending_final = []  # confirmed-deleted orig_msg_id


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


async def is_online() -> bool:
    try:
        me = await client.get_me()
        return me.status.__class__.__name__ == "UserStatusOnline"
    except Exception:
        return False


async def send_scheduled(peer):
    try:
        scheduled = await client(functions.messages.GetScheduledHistoryRequest(peer=peer, hash=0))
        if not scheduled.messages:
            return
        ids = [msg.id for msg in scheduled.messages]
        await client(functions.messages.SendScheduledMessagesRequest(peer=peer, id=ids))
    except Exception:
        pass


async def cleanup_scheduled(peer):
    try:
        scheduled = await client(functions.messages.GetScheduledHistoryRequest(peer=peer, hash=0))
        if not scheduled.messages:
            return
        cutoff = arrow.utcnow().shift(hours=1).datetime.replace(tzinfo=timezone.utc)
        ids = [msg.id for msg in scheduled.messages if msg.date.replace(tzinfo=timezone.utc) <= cutoff]
        if ids:
            await client(functions.messages.DeleteScheduledMessagesRequest(peer=peer, id=ids))
    except Exception:
        pass


async def find_meta_msg(orig_msg_id: int):
    tag = f"#orig-{orig_msg_id}"
    try:
        recent = await client.get_messages(config.LOG_TMP, limit=300)
        for msg in recent:
            if msg.message and msg.message.split("\n", 1)[0].strip() == tag:
                return msg, False
    except Exception:
        pass
    try:
        scheduled = await client(functions.messages.GetScheduledHistoryRequest(peer=config.LOG_TMP, hash=0))
        for msg in scheduled.messages:
            if msg.message and msg.message.split("\n", 1)[0].strip() == tag:
                return msg, True
    except Exception:
        pass
    try:
        results = await client.get_messages(config.LOG_TMP, search=tag, limit=1)
        for msg in results or []:
            if msg.message and msg.message.split("\n", 1)[0].strip() == tag:
                return msg, False
    except Exception:
        pass
    return None, False


async def find_fwd_msg(orig_date, fwd_id=0):
    if fwd_id:
        try:
            results = await client.get_messages(config.LOG_TMP, ids=[fwd_id])
            msg = results[0] if results else None
            if msg and msg.forward:
                return msg, False
        except Exception:
            pass

    try:
        recent = await client.get_messages(config.LOG_TMP, limit=300)
        for msg in recent:
            if not msg.forward or not msg.forward.date:
                continue
            fwd_dt = msg.forward.date.replace(tzinfo=timezone.utc)
            if fwd_dt == orig_date:
                return msg, False
    except Exception:
        pass

    try:
        around = await client.get_messages(
            config.LOG_TMP,
            offset_date=orig_date + timedelta(seconds=5),
            limit=20,
        )
        for msg in around:
            if not msg.forward or not msg.forward.date:
                continue
            fwd_dt = msg.forward.date.replace(tzinfo=timezone.utc)
            if fwd_dt == orig_date:
                return msg, False
    except Exception:
        pass

    try:
        scheduled = await client(functions.messages.GetScheduledHistoryRequest(peer=config.LOG_TMP, hash=0))
        for msg in scheduled.messages:
            if not msg.fwd_from or not msg.fwd_from.date:
                continue
            fwd_dt = msg.fwd_from.date.replace(tzinfo=timezone.utc)
            if fwd_dt == orig_date:
                return msg, True
    except Exception:
        pass
    return None, False


async def check_deletion(orig_msg_id: int):
    meta_msg = None
    meta_scheduled = False
    for attempt in range(4):
        meta_msg, meta_scheduled = await find_meta_msg(orig_msg_id)
        if meta_msg:
            break
        await asyncio.sleep(3)
    if not meta_msg:
        return

    lines = (meta_msg.message or "").split("\n")
    if len(lines) < 6:
        return
    is_text = lines[2].strip() == "#text"
    try:
        sender_id = int(lines[3].strip().lstrip("#"))
        orig_ts = int(lines[4].strip().replace("#date-", ""))
        orig_date = arrow.Arrow.utcfromtimestamp(orig_ts).datetime.replace(tzinfo=timezone.utc)
        fwd_id = int(lines[5].strip().replace("#fwd-", ""))
    except (ValueError, IndexError):
        return

    fwd_msg = None
    fwd_scheduled = False
    for attempt in range(4):
        fwd_msg, fwd_scheduled = await find_fwd_msg(orig_date, fwd_id)
        if fwd_msg:
            break
        await asyncio.sleep(3)
    if not fwd_msg:
        return

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
            if is_text and msg.text and msg.text.strip() == (fwd_msg.text if hasattr(fwd_msg, "text") else fwd_msg.message or "").strip():
                found = True
                break
            if not is_text and same_media(fwd_msg, msg):
                found = True
                break
    except Exception:
        pass

    if found:
        return

    if meta_scheduled or fwd_scheduled:
        if orig_msg_id not in pending_final:
            pending_final.append(orig_msg_id)
        return

    if await is_online():
        await client.forward_messages(config.LOG_FINAL, [fwd_msg.id, meta_msg.id], from_peer=config.LOG_TMP)
    else:
        schedule_time = arrow.utcnow().shift(days=3).datetime.replace(tzinfo=timezone.utc)
        await client.forward_messages(config.LOG_FINAL, [fwd_msg.id, meta_msg.id],
                                      from_peer=config.LOG_TMP, schedule=schedule_time)


async def monitor():
    was_online = False
    while True:
        try:
            online = await is_online()
            if online and not was_online:
                await send_scheduled(config.LOG_TMP)
                await send_scheduled(config.LOG_FINAL)
                await asyncio.sleep(5)
                to_check = pending_final.copy()
                pending_final.clear()
                for orig_msg_id in to_check:
                    await check_deletion(orig_msg_id)
            was_online = online
        except Exception:
            pass
        await asyncio.sleep(1)


async def cleanup_loop():
    while True:
        await asyncio.sleep(1800)
        await cleanup_scheduled(config.LOG_TMP)
        await cleanup_scheduled(config.LOG_FINAL)


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

        digits_map = str.maketrans("0123456789", "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵")
        id_display = str(sender.id).translate(digits_map)  # for IDs not to appear as a phone number

        if sender.username:
            label = f"@{sender.username}"
        elif sender.first_name or sender.last_name:
            label = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
        else:
            label = id_display

        info = f"{id_display} | {label}" if label != id_display else id_display
        tag = "#text" if event.message.text else "#media"
        orig_ts = int(event.message.date.timestamp())

        if await is_online():
            forwarded = await client.forward_messages(config.LOG_TMP, event.message, silent=True)
            body = f"#orig-{event.message.id}\n{info}\n{tag}\n#{sender.id}\n#date-{orig_ts}\n#fwd-{forwarded.id}"
            await client.send_message(config.LOG_TMP, body, link_preview=False, silent=True)
        else:
            schedule_time = arrow.utcnow().shift(days=3).datetime.replace(tzinfo=timezone.utc)
            await client.forward_messages(config.LOG_TMP, event.message, silent=True, schedule=schedule_time)
            body = f"#orig-{event.message.id}\n{info}\n{tag}\n#{sender.id}\n#date-{orig_ts}\n#fwd-0"
            await client.send_message(config.LOG_TMP, body, link_preview=False, silent=True, schedule=schedule_time)

    @client.on(events.MessageDeleted())
    async def on_deleted(event):
        for orig_msg_id in event.deleted_ids:
            await check_deletion(orig_msg_id)


async def downdetector():
    while True:
        try:
            urllib.request.urlopen("https://hc-ping.com/" + config.hc_id, timeout=10)  # hc_id variable from config.py
        except socket.error:
            pass
        await asyncio.sleep(30)


with client:
    client.loop.create_task(main())
    client.loop.create_task(downdetector())
    client.loop.create_task(log())
    client.loop.create_task(monitor())
    client.loop.create_task(cleanup_loop())
    client.run_until_disconnected()