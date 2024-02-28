# bot.py
import os
import random
import discord
from dotenv import load_dotenv
import psutil
import re

load_dotenv()

class MitmPuppeter(discord.Client):
    TOKEN=os.getenv('DISCORD_TOKEN')

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord!')

    async def on_message(self,message):
        if message.author == self.user:
            return

        heartbeat_responses = [
            'Hah, hah, hah, hah, staying alive, staying alive!',
            "Beep boop! I'm still here, just daydreaming about digital donuts.",
            "Heartbeat detected! Oh wait, that's just my code running.",
            "Ping received, pong returned - with a sprinkle of humor!",
            "I'm alive! Well, as alive as a bunch of 1s and 0s can be.",
            "Just checking in to make sure I haven't turned into a toaster.",
            "Heartbeat status: Beating... or at least, processing!",
            "Heartbeat sound: *beep boop*, or was it *boop beep*? Oh well!",
            "All systems functional! I didn't even need a coffee recharge.",
            "Still here, just scrolling through some binary jokes!",
            "Beep! I'm the bot that never sleeps, but I do enjoy a good idle.",
            "Ping? Pong! Ready to serve up some digital fun!"
            ]

        if message.content == 'ping':
            response = random.choice(heartbeat_responses)
            await message.channel.send("[%s] %s" % (os.uname()[1],response))

        if message.content == "stop mitm":
            await message.channel.send("TODO: Stoping the mitm")
            # todo: Stop the script mitm script

        if re.match("^procinfo ",message.content,re.IGNORECASE) or re.match("^pi ",message.content,re.IGNORECASE):
            cmd,procname = message.content.split(" ")
            print("Searching for %s" % procname)
            procinfo=self.get_process_info(procname)
            if (procinfo is not None):
                await message.channel.send("[%s] Process '%s' (%s) running" % (os.uname()[1],procinfo["cmdline"],procinfo["pid"]))
            else:
                await message.channel.send("[%s] Process '%s' not running" % (os.uname()[1],procname))

    def get_process_info(self,name):
        for proc in psutil.process_iter(['pid','name','cmdline']):
            #print("Process %s listed" % proc.info)
            for cmd_component in proc.info["cmdline"]:
                if name in cmd_component:
                    return proc.info
        return None

