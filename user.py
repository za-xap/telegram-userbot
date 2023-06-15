from telethon import functions, types, errors, connection, TelegramClient, events
from time import sleep
import datetime
import json
import arrow
import asyncio
import config, parser
import signal
client = TelegramClient("telega", config.api_id, config.api_hash)
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

 #async def spam(): #write specific comment to new posts in channel with specific message
    #channel_id = 1001418440636
    #channel_entity = await client.get_entity(channel_id)
    #last_message_id = None
    #not_none_message = 0
    #while True:
        #post = await client.get_messages(channel_entity, limit=1)
        #if last_message_id != post[0].id:
            #last_message_id = post[0].id
            #if not_none_message == 0:
                #not_none_message = 1
            #elif not_none_message == 1:
                #await client.send_message(entity = channel_entity, message = "text", comment_to = post[0].id)
        #await asyncio.sleep(10)
async def main(): #updating bio to text + local time with nice font
    prew_date = "0"
    while True:
        utc = arrow.utcnow()
        local = utc.to("Europe/Kiev") #Kiev or Warsaw
        local_date = local.format('H:mm')
        local_date = local_date.translate(local_date.maketrans("0123456789","ghijklmnop"))
        r = [['g', '\\uD835\\uDFEC'], ['h', '\\uD835\\uDFED'], ['i', '\\uD835\\uDFEE'], ['j', '\\uD835\\uDFEF'], ['k', '\\uD835\\uDFF0'], ['l', '\\uD835\\uDFF1'], ['m', '\\uD835\\uDFF2'], ['n', '\\uD835\\uDFF3'], ['o', '\\uD835\\uDFF4'], ['p', '\\uD835\\uDFF5']]
        for e in r:
            local_date=local_date.replace(e[0],e[1])
        if local_date != prew_date:
            await client(functions.account.UpdateProfileRequest(about="The risk was calculated, but I'm bad at math. My time - " + json.loads('\"'+local_date+'\"')))
            prew_date = local_date
        await asyncio.sleep(1)
with client:
    loop = asyncio.get_event_loop()
    client.loop.create_task(par())
    client.loop.create_task(main())
    client.loop.run_forever()
    #client.loop.run_until_complete(main())
