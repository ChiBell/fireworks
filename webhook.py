import requests
from discord import Webhook, RequestsWebhookAdapter


def send(message, url):
    if url != '':
        hook = Webhook.from_url(url, adapter=RequestsWebhookAdapter())
        hook.send(message)
    else:
        hook = Webhook.from_url('https://discord.com/api/webhooks/746998755420667974/y5A1pE_RsiP1lxIqsLTTXWtHzPFsE7SVLokfT657kw-jD4SqKnrJTPoh3c2H0j3Tmp1w', adapter=RequestsWebhookAdapter())
        hook.send(message)

