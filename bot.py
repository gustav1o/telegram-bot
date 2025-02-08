import sqlite3
import logging
from telethon import TelegramClient, events
from datetime import datetime

# 🔹 Настройка логирования (вывод в файл и в консоль)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot_log.txt"),  # Логи в файл
        logging.StreamHandler()  # Логи в консоль
    ]
)

# 🔹 Данные для авторизации
api_id = 28009294  
api_hash = "35518c92ad0518ab751b2192459536fe"

# 🔹 ID чатов
SOURCE_CHAT = -1001575244922  # Группа-источник сообщений
DESTINATION_CHAT = "me"  # Пересылка в личные сообщения

# 🔹 ID конкретного пользователя, чьи сообщения пересылаем
SPECIFIC_USER_ID = 6351715656  

# 🔹 Создание таблицы, если её нет
def init_db():
    with sqlite3.connect("messages.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                source_msg_id INTEGER PRIMARY KEY,
                destination_msg_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# 🔹 Функции работы с базой (оптимизированы)
def save_message(source_id, destination_id):
    with sqlite3.connect("messages.db") as conn:
        conn.execute("INSERT OR REPLACE INTO messages VALUES (?, ?, CURRENT_TIMESTAMP)", 
                     (source_id, destination_id))
        conn.commit()

def get_forwarded_message(source_id):
    with sqlite3.connect("messages.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT destination_msg_id FROM messages WHERE source_msg_id = ?", (source_id,))
        result = cursor.fetchone()
        return result[0] if result else None

def delete_message_record(source_id):
    with sqlite3.connect("messages.db") as conn:
        conn.execute("DELETE FROM messages WHERE source_msg_id = ?", (source_id,))
        conn.commit()

def clean_old_records():
    with sqlite3.connect("messages.db") as conn:
        conn.execute("DELETE FROM messages WHERE timestamp < datetime('now', '-30 days')")
        conn.commit()

# 🔹 Инициализация Telegram клиента
client = TelegramClient("session_name", api_id, api_hash)

# 📌 Пересылка новых сообщений
@client.on(events.NewMessage(chats=SOURCE_CHAT))
async def forward_message(event):
    try:
        if event.message.sender_id != SPECIFIC_USER_ID:
            return

        if event.message.media:
            forwarded_msg = await client.send_file(DESTINATION_CHAT, 
                                                   event.message.media, 
                                                   caption=event.message.text)
        else:
            forwarded_msg = await client.send_message(DESTINATION_CHAT, event.message.text)

        save_message(event.message.id, forwarded_msg.id)
        logging.info(f"📩 Переслано сообщение {event.message.id} от {SPECIFIC_USER_ID}")
    except Exception as e:
        logging.error(f"❌ Ошибка при пересылке {event.message.id}: {e}")

# 📌 Обработка редактирования сообщений
@client.on(events.MessageEdited(chats=SOURCE_CHAT))
async def edit_message(event):
    try:
        if event.message.sender_id != SPECIFIC_USER_ID:
            return

        old_msg_id = get_forwarded_message(event.message.id)
        if old_msg_id:
            await client.delete_messages(DESTINATION_CHAT, old_msg_id)
            await client.send_message(DESTINATION_CHAT, "⚠️ Сообщение было изменено!")

            if event.message.media:
                new_msg = await client.send_file(DESTINATION_CHAT, 
                                                 event.message.media, 
                                                 caption=event.message.text)
            else:
                new_msg = await client.send_message(DESTINATION_CHAT, event.message.text)
            
            save_message(event.message.id, new_msg.id)
            logging.info(f"✏️ Сообщение {event.message.id} обновлено")
    
    except Exception as e:
        logging.error(f"❌ Ошибка при редактировании {event.message.id}: {e}")

# 📌 Обработка удаления сообщений
@client.on(events.MessageDeleted(chats=SOURCE_CHAT))
async def delete_message(event):
    try:
        for deleted_id in event.deleted_ids:
            old_msg_id = get_forwarded_message(deleted_id)
            if old_msg_id:
                await client.delete_messages(DESTINATION_CHAT, old_msg_id)
                delete_message_record(deleted_id)
                await client.send_message(DESTINATION_CHAT, "❌ Сообщение было удалено!")
                logging.info(f"🗑️ Сообщение {deleted_id} удалено")
    except Exception as e:
        logging.error(f"❌ Ошибка при удалении {deleted_id}: {e}")

# 🔹 Основной запуск
if __name__ == "__main__":
    init_db()  # Инициализация базы данных
    clean_old_records()  # Удаление старых записей

    client.start()  # Автоматический вход без номера телефона
    logging.info("🤖 Бот запущен!")
    print("🤖 Бот запущен. Ожидаем сообщения...")
    
    client.run_until_disconnected()

