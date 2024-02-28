import pymsteams
from discord_webhook import DiscordWebhook, DiscordEmbed

class DiscordBell():
    def __init__(self, webhook_url=None) -> None:
        self.webhook_url=webhook_url

    def ring(self,msg,to,action,reason):
        text="===[%s]===\nEmail UID: %s\nFROM: %s\nTO: %s\nSubject: %s\nSize: %s.\nFORWARDED: %s\nREASON: %s" % (msg.date, msg.uid, msg.from_values, to,msg.subject, len(msg.text or msg.html), action, reason)
        webhook = DiscordWebhook(url=self.webhook_url)
        embed = DiscordEmbed(title="Message Forwarded", color="03b2f8")
        embed.set_description(text)
        webhook.add_embed(embed)
        response = webhook.execute()

    def heartbeat(self):
        msg="I'm alive!"
        webhook = DiscordWebhook(url=self.webhook_url,content=msg)
        webhook.execute()

class TeamsBell():
    def __init__(self, webhook_url=None) -> None:
        self.webhook_url=webhook_url

    def get_teams_webhook(self,url):
        return pymsteams.connectorcard(url)
        
    def ring(self,msg,to,action,reason):
        webhook=self.get_teams_webhook(self.webhook_url)
        webhook.title("Email Forwarded")
        text="========[%s]========<br/>Email UID: %s<br/>FROM: %s<br/>TO: %s<br/>Subject: %s<br/>Size: %s.<br/>FORWARDED: %s<br/>REASON: %s" % (msg.date, msg.uid, msg.from_values, to,msg.subject, len(msg.text or msg.html), action, reason)
        webhook.text(text)
        webhook.send()
    
    def heartbeat(self):
        msg="I'm alive!"
        webhook=self.get_teams_webhook(self.webhook_url)
        webhook.title("Heartbeat")
        webhook.text(msg)
        webhook.send()