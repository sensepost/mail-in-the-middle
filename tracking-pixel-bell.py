#!/usr/bin/env python

from discord_webhook import DiscordWebhook, DiscordEmbed
from dotenv import load_dotenv
import os
from time import sleep

load_dotenv()

SLEEP=15
LOG_FILE="/var/log/apache2/forensic_log-10080.log"
KEYWORDS=["customerid","productid"]
WEBHOOK=os.getenv('DISCORD_WEBHOOK')

def LastNlines(fname, N):
     
    assert N >= 0
    pos = N + 1
    lines = []
    
    with open(fname) as f:
        while len(lines) <= N:
            try:
                f.seek(-pos, 2)
            except IOError:
                f.seek(0)
                break
            finally:
                lines = list(f)
             
            pos *= 2
             
    return lines[-N:]


def bell_discord(webhook_url,line):
	text="\n".join(line.split("|"))
	webhook = DiscordWebhook(url=webhook_url)
	embed = DiscordEmbed(title="Ding Ding Ding! Email opened!", color="03b2f8")
	embed.set_description(text)
	webhook.add_embed(embed)
	response = webhook.execute()

def count_lines(file):
    with open(file, 'r') as fp:
        lines = sum(1 for line in fp)
    return lines

# Monitor the last lines of a log file to send a webhook message if we find a specific keyword in it
def main():
    prev_nlines=count_lines(LOG_FILE)
    while(1):
        curr_nlines=count_lines(LOG_FILE)
        if (curr_nlines>prev_nlines):
            new_nlines=curr_nlines-prev_nlines
            print("Exploring %s new lines added to the log" % new_nlines)
            new_lines=LastNlines(LOG_FILE,new_nlines)
            for line in new_lines:
                for keyword in KEYWORDS:
                    if (keyword in line):
                        bell_discord(WEBHOOK,line)
        # This also covers the case when the log rotates 
        # and the current number of lines is lower than the previous number of lines
        prev_nlines=curr_nlines
        print("Sleeping")
        sleep(SLEEP)

main()


