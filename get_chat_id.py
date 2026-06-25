"""
Run this once after creating your bot and sending it a message (e.g. "hi").
It will print your chat_id - copy that into config.py
"""

import requests
import sys

if len(sys.argv) < 2:
    print("Usage: python get_chat_id.py <YOUR_BOT_TOKEN>")
    sys.exit(1)

TOKEN = sys.argv[1]
url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
resp = requests.get(url, timeout=10)
data = resp.json()

if not data.get("ok"):
    print("Error from Telegram API:", data)
    sys.exit(1)

results = data.get("result", [])
if not results:
    print("No messages found yet. Did you send a message to your bot on Telegram? Send one and re-run this.")
    sys.exit(1)

seen = set()
for item in results:
    msg = item.get("message", {})
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    name = chat.get("first_name", "") or chat.get("username", "")
    if chat_id and chat_id not in seen:
        seen.add(chat_id)
        print(f"Found chat_id: {chat_id}  (from: {name})")

if not seen:
    print("Could not find a chat_id in the response. Raw response below:")
    print(data)
