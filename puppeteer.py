#!/usr/bin/env python

from DiscordBot import MitmPuppeter
import discord

def init_bot():
	intents = discord.Intents.default()
	intents.message_content = True

	client = MitmPuppeter(intents=intents)
	client.run(client.TOKEN)

init_bot() 