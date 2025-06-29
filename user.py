from telethon import functions, TelegramClient, events
import datetime
import json
import arrow
import asyncio
import config, parser
import signal
import socket
import urllib.request
client = TelegramClient("telega", config.api_id, config.api_hash) #api_id and api_hash variables from config.py file
@client.on(events.NewMessage(chats = "me", from_users = "me", pattern = "test")) #triggers on specific text in specific chat from specific user
async def trigger(event): #answer with specific text
    await event.reply("test") #or without reply #await client.send_message("me", "test")
async def par():
    signal.signal(signal.SIGINT, signal.SIG_DFL) #this restores the default Ctrl+C signal handler, which just kills the process
    a = 0
    while True:
        b = parser.main()
        if a == 0 and b == 0:
            pass
        elif a == 0 and b == 1:
            a = 1
            await client.send_message("me", "New action!", schedule = datetime.datetime.now() + datetime.timedelta(seconds=10))
        elif a == 1 and b == 1:
            pass
        elif a == 1 and b == 0:
            a = 0
        await asyncio.sleep(20)
async def main(): #updating bio to text + local time with nice font
    prew_date = "0"
    while True:
        utc = arrow.utcnow()
        local = utc.to("Europe/Warsaw") #Kiev or Warsaw
        local_date = local.format('H:mm')
        local_date = local_date.translate(local_date.maketrans("0123456789","ghijklmnop"))
        r = [['g', '\\uD835\\uDFEC'], ['h', '\\uD835\\uDFED'], ['i', '\\uD835\\uDFEE'], ['j', '\\uD835\\uDFEF'], ['k', '\\uD835\\uDFF0'], ['l', '\\uD835\\uDFF1'], ['m', '\\uD835\\uDFF2'], ['n', '\\uD835\\uDFF3'], ['o', '\\uD835\\uDFF4'], ['p', '\\uD835\\uDFF5']]
        for e in r:
            local_date=local_date.replace(e[0],e[1])
        if local_date != prew_date:
            await client(functions.account.UpdateProfileRequest(about="The risk was calculated, but I'm bad at math. My time - " + json.loads('\"'+local_date+'\"')))
            prew_date = local_date
        await asyncio.sleep(1)
async def downdetector():
    while True:
        try:
            urllib.request.urlopen("https://hc-ping.com/" + config.hc_id, timeout=10)
        except socket.error as e:
            print("Ping failed: %s" % e)
        await asyncio.sleep(30)
with client:
    loop = asyncio.get_event_loop()
    client.loop.create_task(par())
    client.loop.create_task(main())
    client.loop.create_task(downdetector())
    client.loop.run_forever()
