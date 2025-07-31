import discord
import requests
import json
import datetime
import os
import random


CREDENTIAL_FILE = 'credentials.json'
EVENT_FILE = 'event_date.json'

vault_messages = [
    "The Vault is locked.",
    "Your trinket sounds like it was buzzing for a second...",
    "Have you found the Key yet?",
    "The Vaultkeeper is watching.",
    "The Vaultkeeper might add a !lore command if you ask nicely.",
    "The Vaultkeeper is busy, but will return soon."
]

token = ''
owner_id = 0
reminder_channel = 0
event_date = None
sent_monday = False
sent_day_before = False

def load_credentials():
    global token, owner_id, reminder_channel
    if not os.path.exists(CREDENTIAL_FILE):
        raise FileNotFoundError(f"Credentials file '{CREDENTIAL_FILE}' not found.")
    with open(CREDENTIAL_FILE, "r") as f:
        data = json.load(f)
        token = data.get('token')
        owner_id = data.get('owner_id')
        reminder_channel = data.get('reminder_channel')


def is_authorized(id):
    try:
        if owner_id == id:
            return True
        else:
            raise ValueError("Invalid owner ID.")
    except FileNotFoundError:
        print(f"Credentials file '{CREDENTIAL_FILE}' not found. Please create it with the required fields.")
        return True
    except Exception as e:
        print(f"Error checking credentials: {e}")

def load_event_date():
    global event_date, sent_monday, sent_day_before
    if not os.path.exists(EVENT_FILE):
        return None
    with open(EVENT_FILE, "r") as f:
        data = json.load(f)
        event_date = data.get("event_date", None)
        if event_date is not None:
            event_date = datetime.datetime.strptime(event_date, "%Y-%m-%d").date()
        sent_monday = data.get("sent_monday", False)
        sent_day_before = data.get("sent_day_before", False)

def get_meme():
    try:
        response = requests.get('https://meme-api.com/gimme/dndmemes', timeout=5)
        json_data = response.json()
        return json_data['url']
    except Exception as e:
        print(f"Error fetching meme: {e}")
        return "Failed to retrieve meme."

def save_event_date(date_obj, sent_monday=False, sent_day_before=False):
    with open(EVENT_FILE, "w") as f:
        json.dump({
            "event_date": date_obj.strftime("%Y-%m-%d"),
            "sent_monday": sent_monday,
            "sent_day_before": sent_day_before
        }, f)

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged in as {0}'.format(self.user))
        if not hasattr(self, 'reminder_task_started'):
            self.reminder_task_started = True
            self.loop.create_task(self.reminder_task())

    async def on_message(self, message):
        global event_date
        if message.author == self.user:
            return

        if message.content.startswith('!hello'):
            await message.channel.send(random.choice(vault_messages))
        elif message.content.startswith('!meme'):
            await message.channel.send(get_meme())
        elif message.content.startswith('!schedule'):
            if not is_authorized(message.author.id):
                await message.channel.send('You do not hold the keys to the Vault.')
                return
            parts = message.content.split(maxsplit=1)
            if len(parts) != 2:
                await message.channel.send('Put it in right, Vaultkeeper. Use YYYY-MM-DD.')
                return
            try:
                event_date = datetime.datetime.strptime(parts[1], '%Y-%m-%d').date()
                save_event_date(event_date)
                await message.channel.send(f'Event scheduled for {event_date}.')
            except ValueError:
                await message.channel.send('Put it in right, Vaultkeeper. Use YYYY-MM-DD.')
        elif message.content.startswith('!remind'):
            next_session = event_date
            random_vault_message = random.choice(vault_messages)
            if next_session is None:
                await message.channel.send('It hasn\'t been decided upon. Alert the Vaultkeeper!')
                return
            else:
                now = datetime.date.today()
                if next_session < now:
                    await message.channel.send('The vault has closed for now.... A day soon must be decided upon')
                    return
                days_left = (next_session - now).days
                if days_left == 0:
                    await message.channel.send('Greetings Operatives... Your next mission is today')
                elif days_left == 1:
                    await message.channel.send('The vault opens tomorrow! Prepare yourselves!')
                else:
                    await message.channel.send(f'The vault opens in {days_left} days. {random_vault_message}!')
        elif message.content.startswith('!lore'):
            await message.channel.send("Under Construction, go look at !meme for now")

    async def reminder_task(self):
        global sent_monday, sent_day_before
        await self.wait_until_ready()
        channel = self.get_channel(reminder_channel)
        while not self.is_closed():
            now = datetime.datetime.utcnow() 
            target = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now >= target:
                target += datetime.timedelta(days=1)
            await discord.utils.sleep_until(target)
            next_session = event_date
            if next_session:
                today = datetime.datetime.utcnow().date()
                monday_of_week = next_session - datetime.timedelta(days=next_session.weekday())
                # Monday of event week
                if today == monday_of_week and not sent_monday:
                    if channel:
                        await channel.send("Reminder: The Vault Opens this Friday! 🎉")
                    save_event_date(next_session, sent_monday=True, sent_day_before=sent_day_before)
                    sent_monday = True
                # Day before event
                if today == (next_session - datetime.timedelta(days=1)) and not sent_day_before:
                    if channel:
                        await channel.send("Reminder: The Vault is Opening tomorrow! 🎉")
                    sent_day_before = True
                    save_event_date(next_session, sent_monday=sent_monday, sent_day_before=True)
                # Reset flags if event date changes or new week
                if today > next_session:
                    sent_monday = False
                    sent_day_before = False
                    save_event_date(next_session, sent_monday=False, sent_day_before=False)
            
intents = discord.Intents.default()
intents.message_content = True
load_credentials()
load_event_date()

client = MyClient(intents=intents)
client.run(token)
