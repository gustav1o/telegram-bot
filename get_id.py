from telethon.sync import TelegramClient

api_id = 28009294 # Ваш API ID
api_hash = "35518c92ad0518ab751b2192459536fe"  # Ваш API Hash
phone = "+380950759374"  # Ваш номер телефона

client = TelegramClient("session_name", api_id, api_hash)
client.start(phone)

dialogs = client.get_dialogs()
for chat in dialogs:
    print(f"Название: {chat.name}, ID: {chat.id}")

client.disconnect()

