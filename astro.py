import os
import sqlite3
import html
import time

import telebot
from telebot import types


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = "PASTE_YOUR_ASTRO_BOT_TOKEN_HERE"
ADMIN_ID = 1244731064

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.txt")

DATABASE_NAME = "astro_database.db"

DEFAULT_SPONSOR_CHANNELS = [
    {
        "channel": "@tarotiz",
        "link": "https://t.me/tarotiz",
        "title": "МОЙ АСТРО КАНАЛ",
        "insert_position": None
    },
    {
        "channel": "@wbmostril",
        "link": "https://t.me/wbmostril",
        "title": "WB НАХОДКИ",
        "insert_position": None
    },
    {
        "channel": "@ziaaprom",
        "link": "https://t.me/ziaaprom",
        "title": "ПРОМОКОДЫ",
        "insert_position": None
    },
    {
        "channel": "@rrrteww",
        "link": "https://t.me/rrrteww",
        "title": "АКЦИИ ЗЯ",
        "insert_position": None
    }
]

bot = telebot.TeleBot(BOT_TOKEN)

admin_states = {}


# =========================
# БАЗА ДАННЫХ
# =========================

def db_connect():
    return sqlite3.connect(DATABASE_NAME)


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    for column in columns:
        if column[1] == column_name:
            return True

    return False


def init_db():
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sponsor_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            link TEXT NOT NULL,
            title TEXT,
            insert_position INTEGER
        )
    """)

    conn.commit()

    if not column_exists(cursor, "links", "title"):
        cursor.execute("ALTER TABLE links ADD COLUMN title TEXT")

    if not column_exists(cursor, "sponsor_channels", "title"):
        cursor.execute("ALTER TABLE sponsor_channels ADD COLUMN title TEXT")

    if not column_exists(cursor, "sponsor_channels", "insert_position"):
        cursor.execute("ALTER TABLE sponsor_channels ADD COLUMN insert_position INTEGER")

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM sponsor_channels")
    channels_count = cursor.fetchone()[0]

    if channels_count == 0:
        for item in DEFAULT_SPONSOR_CHANNELS:
            cursor.execute("""
                INSERT INTO sponsor_channels (channel, link, title, insert_position)
                VALUES (?, ?, ?, ?)
            """, (
                item["channel"],
                item["link"],
                item["title"],
                item["insert_position"]
            ))

        conn.commit()

    conn.close()


def add_user_to_db(user_id, username, first_name):
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user_id, username, first_name))

    cursor.execute("""
        UPDATE users
        SET username = ?, first_name = ?
        WHERE user_id = ?
    """, (username, first_name, user_id))

    conn.commit()
    conn.close()
def import_users_from_txt():
    if not os.path.exists(USERS_FILE):
        print("users.txt не найден, импорт старых пользователей пропущен")
        return

    imported = 0
    skipped = 0

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            users = file.read().splitlines()

        unique_users = list(set(users))

        for user_id in unique_users:
            user_id = str(user_id).strip()

            if not user_id:
                skipped += 1
                continue

            try:
                numeric_user_id = int(user_id)

                add_user_to_db(
                    numeric_user_id,
                    None,
                    None
                )

                imported += 1

            except Exception:
                skipped += 1

        print(f"Импорт users.txt завершён. Импортировано: {imported}, пропущено: {skipped}")

    except Exception as error:
        print("Ошибка импорта users.txt:", error)

def get_users():
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    conn.close()

    return [user[0] for user in users]


def get_users_count():
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    conn.close()

    return count


def add_link(title, url):
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO links (title, url)
        VALUES (?, ?)
    """, (title, url))

    conn.commit()
    conn.close()


def get_links():
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, url FROM links ORDER BY id ASC")
    links = cursor.fetchall()

    conn.close()

    return links


def clear_links():
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM links")

    conn.commit()
    conn.close()


def add_sponsor_channel(channel, link, title=None, insert_position=None):
    conn = db_connect()
    cursor = conn.cursor()

    if title is None or title.strip() == "":
        title = f"🔥 {channel}"

    cursor.execute("""
        INSERT INTO sponsor_channels (channel, link, title, insert_position)
        VALUES (?, ?, ?, ?)
    """, (channel, link, title, insert_position))

    conn.commit()
    conn.close()


def get_sponsor_channels():
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, channel, link, title, insert_position
        FROM sponsor_channels
        ORDER BY id ASC
    """)

    channels = cursor.fetchall()

    conn.close()

    return channels


def clear_sponsor_channels():
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM sponsor_channels")

    conn.commit()
    conn.close()


def reset_default_sponsor_channels():
    clear_sponsor_channels()

    for item in DEFAULT_SPONSOR_CHANNELS:
        add_sponsor_channel(
            item["channel"],
            item["link"],
            item["title"],
            item["insert_position"]
        )


# =========================
# КЛИКАБЕЛЬНЫЕ ССЫЛКИ
# =========================

def utf16_index_to_py_index(text, utf16_index):
    encoded = text.encode("utf-16-le")
    sliced = encoded[:utf16_index * 2]

    try:
        return len(sliced.decode("utf-16-le"))
    except UnicodeDecodeError:
        return len(sliced.decode("utf-16-le", errors="ignore"))


def extract_clickable_links_from_message(message):
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []

    result = []

    lines = text.splitlines()
    current_offset = 0

    for line in lines:
        clean_line = line.strip()

        if not clean_line:
            current_offset += len(line) + 1
            continue

        line_start = current_offset
        line_end = current_offset + len(line)

        found_url = None

        for entity in entities:
            entity_start = utf16_index_to_py_index(text, entity.offset)
            entity_end = utf16_index_to_py_index(text, entity.offset + entity.length)

            if entity_start >= line_start and entity_end <= line_end:
                if entity.type == "text_link":
                    found_url = entity.url
                    break

                if entity.type == "url":
                    found_url = text[entity_start:entity_end]
                    break

        if found_url:
            result.append({
                "title": clean_line,
                "url": found_url
            })

        current_offset += len(line) + 1

    return result


def build_clickable_links_text(links):
    lines = []

    for item in links:
        title = html.escape(str(item["title"]))
        url = html.escape(str(item["url"]), quote=True)

        lines.append(f'<a href="{url}">{title}</a>')

    return "\n".join(lines)


def get_final_links_with_sponsors():
    main_links = []

    for link_id, title, url in get_links():
        if not title:
            title = url

        main_links.append({
            "title": title,
            "url": url
        })

    sponsor_links = []

    for channel_id, channel, link, title, insert_position in get_sponsor_channels():
        if not title:
            title = f"🔥 {channel}"

        sponsor_links.append({
            "title": title,
            "url": link,
            "position": insert_position
        })

    final_links = main_links.copy()

    sponsors_with_position = []
    sponsors_without_position = []

    for sponsor in sponsor_links:
        if sponsor["position"]:
            sponsors_with_position.append(sponsor)
        else:
            sponsors_without_position.append(sponsor)

    sponsors_with_position.sort(key=lambda item: item["position"])

    offset = 0

    for sponsor in sponsors_with_position:
        position = sponsor["position"]
        insert_index = position - 1 + offset

        if insert_index < 0:
            insert_index = 0

        if insert_index > len(final_links):
            insert_index = len(final_links)

        final_links.insert(insert_index, {
            "title": sponsor["title"],
            "url": sponsor["url"]
        })

        offset += 1

    for sponsor in sponsors_without_position:
        final_links.append({
            "title": sponsor["title"],
            "url": sponsor["url"]
        })

    return final_links


def build_all_links_text():
    final_links = get_final_links_with_sponsors()

    if not final_links:
        return "<i>Список ссылок пока пуст.</i>"

    lines = ["<b>Партнёры:</b>"]

    links_text = build_clickable_links_text(final_links)

    lines.append(links_text)

    return "\n".join(lines)


def send_long_html_message(chat_id, text, reply_markup=None):
    max_length = 3900

    if len(text) <= max_length:
        bot.send_message(
            chat_id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
        return

    parts = []
    current_part = ""

    for line in text.splitlines():
        if len(current_part) + len(line) + 1 > max_length:
            parts.append(current_part)
            current_part = line
        else:
            if current_part:
                current_part += "\n" + line
            else:
                current_part = line

    if current_part:
        parts.append(current_part)

    for index, part in enumerate(parts):
        markup = reply_markup if index == len(parts) - 1 else None

        bot.send_message(
            chat_id,
            part,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=markup
        )


# =========================
# КЛАВИАТУРЫ
# =========================

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.add(types.KeyboardButton("📢 Сделать рассылку"))
    markup.add(types.KeyboardButton("📥 Импорт ссылок"))
    markup.add(types.KeyboardButton("⚙️ Каналы с проверкой"))
    markup.add(types.KeyboardButton("📋 Показать ссылки"))
    markup.add(types.KeyboardButton("📊 Статистика"))
    markup.add(types.KeyboardButton("🗑 Очистить список ссылок"))
    markup.add(types.KeyboardButton("♻️ Сбросить проверочные каналы"))
    markup.add(types.KeyboardButton("❌ Отмена"))

    return markup


def start_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(types.InlineKeyboardButton(
        text="АСТРОРАЗБОР",
        callback_data="astro"
    ))

    markup.add(types.InlineKeyboardButton(
        text="ПРИВОРОТ, МОРОК И Т.Д.",
        callback_data="magic"
    ))

    markup.add(types.InlineKeyboardButton(
        text="ПРАКТИКИ",
        callback_data="practices"
    ))

    markup.add(types.InlineKeyboardButton(
        text="КОД-ПРИВЯЗКА",
        callback_data="code"
    ))

    return markup


def check_subscription_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(types.InlineKeyboardButton(
        text="✅ Я подписался(-ась)",
        callback_data="subscribed"
    ))

    return markup


def not_subscribed_keyboard(unsubscribed_channels):
    markup = types.InlineKeyboardMarkup(row_width=1)

    for channel in unsubscribed_channels:
        markup.add(types.InlineKeyboardButton(
            text=f"Подписаться: {channel['title']}",
            url=channel['link']
        ))

    markup.add(types.InlineKeyboardButton(
        text="✅ Я подписался(-ась), проверить ещё раз",
        callback_data="subscribed"
    ))

    return markup


# =========================
# ПОДПИСКА
# =========================

def get_unsubscribed_channels(user_id):
    unsubscribed_channels = []

    channels = get_sponsor_channels()

    for channel_id, channel, link, title, insert_position in channels:
        try:
            member = bot.get_chat_member(channel, user_id)

            if member.status not in ["member", "administrator", "creator"]:
                unsubscribed_channels.append({
                    "channel": channel,
                    "link": link,
                    "title": title or f"🔥 {channel}"
                })

        except Exception as error:
            print("Ошибка проверки подписки:", error)

            unsubscribed_channels.append({
                "channel": channel,
                "link": link,
                "title": title or f"🔥 {channel}"
            })

    return unsubscribed_channels


# =========================
# ВСПОМОГАТЕЛЬНОЕ
# =========================

def send_typing_message(chat_id, text, delay=3, reply_markup=None, parse_mode="HTML"):
    bot.send_chat_action(chat_id, "typing")
    time.sleep(delay)

    bot.send_message(
        chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup
    )


# =========================
# КОМАНДЫ
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    add_user_to_db(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    bot.send_message(
        message.chat.id,
        text=f"""<b>Привет, {html.escape(message.from_user.first_name or "дорогой пользователь")}!</b> Этот бот поможет тебе узнать:

1. Ответ на вопрос при помощи хорарной астрологии;
2. Подобрать личную практику специально для тебя по твоей дате рождения;
3. Составить личный любовный код для партнера;
4. А также ты можешь здесь оставить свой запрос на морок, привязку, приворот и т.п.🔮

<i>(у тебя есть только одна бесплатная первая попытка, так что выбирай, что для тебя в приоритете)</i>

Для продолжения нажми на кнопку ниже ⬇️""",
        parse_mode="HTML",
        reply_markup=start_keyboard()
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    add_user_to_db(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    bot.send_message(
        message.chat.id,
        "ℹ️ Помощь\n\n"
        "/start — запустить бота\n"
        "/admin — админ-панель"
    )


@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ У тебя нет доступа к админ-панели.")
        return

    bot.send_message(
        message.chat.id,
        "🔐 Админ-панель открыта.\n\nВыбери действие:",
        reply_markup=admin_keyboard()
    )


# =========================
# CALLBACK ОСНОВНОГО БОТА
# =========================

@bot.callback_query_handler(func=lambda call: True)
def main_callback_handler(call):
    add_user_to_db(
        call.from_user.id,
        call.from_user.username,
        call.from_user.first_name
    )

    bot.answer_callback_query(call.id)

    if call.data == "astro":
        bot.send_message(
            call.message.chat.id,
            text="""Перед тем как ты опишешь свою ситуацию, прочитай текст ниже, чтобы лучше понимать, что такое хорарная астрология:

🔮<b><i>Хорарная астрология</i></b> — это часовая или вопросная астрология. Она помогает получить ответ на конкретный вопрос, который волнует человека в данный момент. Карта строится на момент задания вопроса, и по ней можно увидеть развитие ситуации, скрытые обстоятельства, намерения людей и возможный исход.

Хорарная астрология отвечает на любые конкретные вопросы:
- выйду ли я замуж за Пашу,
- куплю ли я эту квартиру,
- поступлю ли я в этот ВУЗ,
- будет ли мне комфортно в этом городе, этой стране и т.д.

Теперь подробно опиши свою ситуацию и задай конкретный вопрос🙏🏻

Для создания твоей индивидуальной астральной карты необходимо <b>твоя дата рождения и город</b> (из которого задаётся вопрос)
❗<u><b>пиши всё в одном сообщении</b></u>❗️.""",
            parse_mode="HTML"
        )

    elif call.data == "magic":
        read_menu = types.InlineKeyboardMarkup(row_width=1)

        read_menu.add(types.InlineKeyboardButton(
            text="Я ПРОЧИТАЛ(-А)",
            callback_data="magic_read"
        ))

        bot.send_message(
            call.message.chat.id,
            text="""Перед тем как выбрать, что тебе нужно, ниже представлено краткое описание оказываемых нами услуг:

🔮<b><i>Морок</i></b>. Его ещё называют оморочка. Воздействие на теменную и головную чакру, с целью внушить жертве какую-то мысль, запутать, что-то внушить.

🔮<b><i>Приворот</i></b> — это энергоинформационная программа, направленная на привлечение какого-то лица к любовному контакту. Без предмета своего обожания больной может сохнуть, страдать, худеет. Буквально тает на глазах.

🔮<b><i>Присушка</i></b> — это любовное воздействие, направленное на появление тоски, интереса, тяги и желания общения у конкретного человека. Человек начинает чаще думать о тебе, скучать и испытывать потребность выйти на контакт.

🔮<b><i>Привязка</i></b> — тоже разновидность приворота, может использоваться для сохранности дружбы, рабочих отношений. Как и все привороты, это создание зависимости: сексуальной, энергетической, физической, психической, сексуальной.

🔮<b><i>Отворот/остуда</i></b> — это энергоинформационная программа, направленная на разрыв какой-то связи между людьми. Ему могут подвергаться пары, партнеры по работе, подруги. Фактически портятся какие-то отношения.

🔮<b><i>Рассорка</i></b> — большие конфликты по мелочам в семье, так что после ссоры супруги думают, с чего вдруг они сорвались. Не видя друг друга, пара скучает, а как только встречаются, готовы друг друга испепелить по несущественным поводам.

🔮<b><i>Дьявольская красота</i></b> — это ритуал для раскрытия личной магнетики, харизмы и уверенности в себе. Он помогает принять свою красоту, почувствовать внутреннюю силу и начать проявляться ярче, благодаря чему человек становится более заметным, притягательным и уверенным в общении.""",
            parse_mode="HTML",
            reply_markup=read_menu
        )

    elif call.data == "magic_read":
        magic_choice_menu = types.InlineKeyboardMarkup(row_width=1)

        magic_choice_menu.add(types.InlineKeyboardButton(text="МОРОК", callback_data="morok"))
        magic_choice_menu.add(types.InlineKeyboardButton(text="ПРИВОРОТ", callback_data="privorot"))
        magic_choice_menu.add(types.InlineKeyboardButton(text="ПРИСУШКА", callback_data="prisushka"))
        magic_choice_menu.add(types.InlineKeyboardButton(text="ПРИВЯЗКА", callback_data="privyazka"))
        magic_choice_menu.add(types.InlineKeyboardButton(text="ОТВОРОТ/ОСТУДА", callback_data="otvorot"))
        magic_choice_menu.add(types.InlineKeyboardButton(text="РАССОРКА", callback_data="rassorka"))
        magic_choice_menu.add(types.InlineKeyboardButton(text="ДЬЯВОЛЬСКАЯ КРАСОТА", callback_data="devil_beauty"))

        bot.send_message(
            call.message.chat.id,
            text="Теперь выбери то, что тебе нужно:",
            reply_markup=magic_choice_menu
        )

    elif call.data == "practices":
        bot.send_message(
            call.message.chat.id,
            text="""Для подбора личной практики напиши одним сообщением:

1. Свое имя;
2. Дату рождения;
3. Время рождения, если знаешь;
4. Город рождения;
5. Какой результат ты хочешь получить от практики.

Например:
<i>Алина
12.03.2003
14:30
Москва
Хочу практику на раскрытие женской энергии, уверенности в себе и усиление привлекательности.</i>

После этого я проведу анализ полученных данных...""",
            parse_mode="HTML"
        )

    elif call.data == "code":
        bot.send_message(
            call.message.chat.id,
            text="""Чтобы создать персональный любовный код-привязку, напиши одним сообщением:

1. Твое имя и дату рождения;
2. Имя и дату рождения человека, на которого создается код.

Например:
<i>Алина 12.03.2003
Иван 13.08.2000</i>

После этого я проведу анализ полученных данных...""",
            parse_mode="HTML"
        )

    elif call.data == "morok":
        bot.send_message(
            call.message.chat.id,
            text="""Ты выбрал(-а): <b>МОРОК</b>.

Теперь опиши свою ситуацию одним сообщением:
1. Твое имя и дату рождения;
2. Имя и дату рождения человека, если знаешь;
3. Какие отношения у вас сейчас;
4. Что именно ты хочешь внушить или изменить;
5. Какой результат ты хочешь получить.

После этого я проведу анализ полученных данных...""",
            parse_mode="HTML"
        )

    elif call.data == "privorot":
        bot.send_message(
            call.message.chat.id,
            text="""Ты выбрал(-а): <b>ПРИВОРОТ</b>.

Теперь опиши свою ситуацию одним сообщением:
1. Твое имя и дату рождения;
2. Имя и дату рождения человека;
3. Какие отношения у вас сейчас;
4. Что между вами произошло;
5. Какой результат ты хочешь получить.

После этого я проведу анализ полученных данных...""",
            parse_mode="HTML"
        )

    elif call.data == "prisushka":
        bot.send_message(
            call.message.chat.id,
            text="""Ты выбрал(-а): <b>ПРИСУШКА</b>.

Теперь опиши свою ситуацию одним сообщением:
1. Твое имя и дату рождения;
2. Имя и дату рождения человека;
3. Общаетесь ли вы сейчас;
4. Как давно знакомы;
5. Какой результат ты хочешь получить.

После этого я проведу анализ полученных данных...""",
            parse_mode="HTML"
        )

    elif call.data == "privyazka":
        bot.send_message(
            call.message.chat.id,
            text="""Ты выбрал(-а): <b>ПРИВЯЗКА</b>.

Теперь опиши свою ситуацию одним сообщением:
1. Твое имя и дату рождения;
2. Имя и дату рождения человека;
3. Какая связь между вами сейчас;
4. Что ты хочешь сохранить или усилить;
5. Какой результат ты хочешь получить.

После этого я проведу анализ полученных данных...""",
            parse_mode="HTML"
        )

    elif call.data == "otvorot":
        bot.send_message(
            call.message.chat.id,
            text="""Ты выбрал(-а): <b>ОТВОРОТ/ОСТУДА</b>.

Теперь опиши свою ситуацию одним сообщением:
1. Кого нужно отдалить друг от друга;
2. Какие отношения между этими людьми;
3. Как давно длится эта связь;
4. Почему ты хочешь сделать отворот/остуду;
5. Какой результат ты хочешь получить.

После этого я проведу анализ полученных данных...""",
            parse_mode="HTML"
        )

    elif call.data == "rassorka":
        bot.send_message(
            call.message.chat.id,
            text="""Ты выбрал(-а): <b>РАССОРКА</b>.

Теперь опиши свою ситуацию одним сообщением:
1. Между кем нужно создать конфликт;
2. Какие отношения между этими людьми;
3. Как давно они общаются;
4. Почему ты хочешь сделать рассорку;
5. Какой результат ты хочешь получить.

После этого я проведу анализ полученных данных...""",
            parse_mode="HTML"
        )

    elif call.data == "devil_beauty":
        bot.send_message(
            call.message.chat.id,
            text="""Ты выбрал(-а): <b>ДЬЯВОЛЬСКАЯ КРАСОТА</b>.

Теперь опиши свою ситуацию одним сообщением:
1. Твое имя и дату рождения;
2. Что именно ты хочешь усилить в себе;
3. Есть ли сейчас неуверенность, зажимы или страх проявляться;
4. Какой результат ты хочешь получить.

После этого я проведу анализ полученных данных...""",
            parse_mode="HTML"
        )

    elif call.data == "show_answer":
        continue_menu = types.InlineKeyboardMarkup(row_width=1)

        continue_menu.add(types.InlineKeyboardButton(
            text="ПРОДОЛЖИТЬ",
            callback_data="continue"
        ))

        bot.send_message(
            call.message.chat.id,
            text="""Перед тем как перейти к следующему шагу, мы обязаны предупредить, что это не совсем бесплатно. Человек (то есть я и моя команда) НЕ МОЖЕТ тратить свою энергию, силы и время просто так, без какой либо "оплаты", поэтому мы требуем лишь подписку!

Спасибо за понимание!💘""",
            reply_markup=continue_menu
        )

    elif call.data == "continue":
        text = f"""<b>❗️ВНИМАНИЕ❗️</b>

Твой запрос на данный момент <b>в обработке</b>!
Потребуется <i>немного времени</i>, чтобы наша команда помогла тебе с ним.

<b>❗️ОТВЕТ ПОЛУЧАТ АБСОЛЮТНО ВСЕ</b>, просто <u>в порядке очереди</u>, поэтому придется немного подождать.

Чтобы получить все <b>бесплатно</b>, тебе необходимо подписаться на наших партнёров
<i>(поймите, полностью бесплатно работать — в ущерб себе, поэтому мы просим лишь подписку 💕)</i>


{build_all_links_text()}


После <u>автоматической проверки подписки</u> в течение нескольких суток вам напишет <b>одна из наших пяти коллег</b>.
<i>Просим вас запастись терпением, так как вас много, а нас всего пятеро.</i>

<b>❗️БЕЗ ПОДПИСКИ НА ВСЕХ СПОНСОРОВ БОТ ВАМ НИЧЕГО НЕ ОТПРАВИТ❗️</b>"""

        send_long_html_message(
            call.message.chat.id,
            text,
            reply_markup=check_subscription_keyboard()
        )

    elif call.data == "subscribed":
        unsubscribed_channels = get_unsubscribed_channels(call.from_user.id)

        if unsubscribed_channels:
            bot.answer_callback_query(
                call.id,
                "Ты подписался(-ась) не на всех обязательных каналах 💔",
                show_alert=True
            )

            bot.send_message(
                call.message.chat.id,
                text="""<b>Почти готово💘</b>

Я проверила подписку и вижу, что ты подписался(-ась) <b>не на всех обязательных каналах</b>.
Пожалуйста, подпишись на все каналы из списка ниже, а потом нажми кнопку:

<b>✅ Я подписался(-ась), проверить ещё раз</b>""",
                reply_markup=not_subscribed_keyboard(unsubscribed_channels),
                parse_mode="HTML"
            )
            return

        bot.send_message(
            call.message.chat.id,
            text="""<b>Спасибо!💘</b>

Твой запрос <b>принят</b> и поставлен в очередь на обработку.
⏳<u>Примерное время ожидания ответа:</u> <b>до 48 часов 31 минуты</b>.

<i>Я или одна из участниц моей команды обязательно вернёмся к твоему запросу, как только подойдёт твоя очередь.</i>

⚠️<u>Пожалуйста, не отписывайся от спонсоров до получения ответа.</u>

Если подписка будет отменена, бот может <b>не увидеть тебя в очереди</b>, и заявка автоматически потеряет приоритет :(
🔮<i>Энергообмен очень важен</i>, поэтому мы просим лишь <b>подписку на партнёров</b>💕

Если ты <u>не готов(-а) ждать бесплатный ответ</u> или хочешь получить помощь быстрее, ты можешь написать мне лично и заказать ритуал <b>на платной основе</b>.

📩<b>МОИ КОНТАКТЫ:</b> @tarotmarian""",
            parse_mode="HTML"
        )


# =========================
# ОБРАБОТКА СОСТОЯНИЙ АДМИНА
# =========================

@bot.message_handler(
    content_types=["text", "photo", "video", "document", "sticker", "animation", "voice"],
    func=lambda message: message.from_user.id == ADMIN_ID and message.from_user.id in admin_states
)
def handle_admin_state(message):
    state = admin_states.get(message.from_user.id)

    if message.content_type == "text" and message.text == "❌ Отмена":
        del admin_states[message.from_user.id]

        bot.send_message(
            message.chat.id,
            "❌ Действие отменено.",
            reply_markup=admin_keyboard()
        )
        return

    if state == "waiting_broadcast":
        users = get_users()

        success = 0
        failed = 0

        bot.send_message(message.chat.id, "📢 Рассылка началась...")

        for user_id in users:
            try:
                bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
                success += 1
                time.sleep(0.05)
            except Exception:
                failed += 1

        del admin_states[message.from_user.id]

        bot.send_message(
            message.chat.id,
            f"✅ Рассылка завершена.\n\n"
            f"Успешно: {success}\n"
            f"Ошибок: {failed}",
            reply_markup=admin_keyboard()
        )

        return

    if state == "waiting_links_import":
        if message.content_type != "text":
            bot.send_message(
                message.chat.id,
                "❌ Нужно отправить именно текст с кликабельными ссылками.",
                reply_markup=admin_keyboard()
            )
            return

        imported_links = extract_clickable_links_from_message(message)

        if not imported_links:
            bot.send_message(
                message.chat.id,
                "❌ Я не нашла кликабельные ссылки.\n\n"
                "Важно: текст должен быть именно кликабельным.\n"
                "То есть ты нажимаешь на строку — и открывается канал.\n\n"
                "Пример правильного вида:\n"
                "🛍️ Вб дарит бесплатно\n"
                "💅 Трендовый маникюр\n"
                "📳 Рекко",
                reply_markup=admin_keyboard()
            )
            return

        clear_links()

        added = 0

        for item in imported_links:
            add_link(item["title"], item["url"])
            added += 1

        del admin_states[message.from_user.id]

        bot.send_message(
            message.chat.id,
            f"✅ Импорт завершён.\n\n"
            f"Добавлено кликабельных ссылок: {added}",
            reply_markup=admin_keyboard()
        )

        return

    if state == "waiting_sponsor_channels":
        if message.content_type != "text":
            bot.send_message(
                message.chat.id,
                "❌ Нужно отправить текст со списком каналов.",
                reply_markup=admin_keyboard()
            )
            return

        lines = message.text.splitlines()

        added = 0

        for line in lines:
            line = line.strip()

            if not line:
                continue

            parts = [part.strip() for part in line.split("|")]

            channel = None
            link = None
            title = None
            insert_position = None

            if len(parts) == 1:
                channel = parts[0]
                link = f"https://t.me/{channel.replace('@', '')}"
                title = f"🔥 {channel}"

            elif len(parts) == 2:
                channel = parts[0]
                link = parts[1]
                title = f"🔥 {channel}"

            elif len(parts) == 3:
                channel = parts[0]
                link = parts[1]
                title = parts[2]

            elif len(parts) >= 4:
                channel = parts[0]
                link = parts[1]
                title = parts[2]

                try:
                    insert_position = int(parts[3])
                except Exception:
                    insert_position = None

            if (
                isinstance(channel, str)
                and isinstance(link, str)
                and channel.startswith("@")
                and link.startswith("http")
            ):
                add_sponsor_channel(channel, link, title, insert_position)
                added += 1

        del admin_states[message.from_user.id]

        bot.send_message(
            message.chat.id,
            f"✅ Проверочные каналы добавлены.\n\n"
            f"Добавлено: {added}\n\n"
            "Если ты указала позицию, канал вставится внутрь списка ссылок.",
            reply_markup=admin_keyboard()
        )

        return


# =========================
# КНОПКИ АДМИН-ПАНЕЛИ
# =========================

@bot.message_handler(func=lambda message: message.text == "📢 Сделать рассылку")
def start_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return

    admin_states[message.from_user.id] = "waiting_broadcast"

    bot.send_message(
        message.chat.id,
        "📢 Отправь сообщение для рассылки.\n\n"
        "Можно отправить текст, фото, видео, документ, стикер или голосовое.\n\n"
        "Для отмены нажми ❌ Отмена.",
        reply_markup=admin_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "📥 Импорт ссылок")
def import_links_start(message):
    if message.from_user.id != ADMIN_ID:
        return

    admin_states[message.from_user.id] = "waiting_links_import"

    bot.send_message(
        message.chat.id,
        "📥 Отправь список КЛИКАБЕЛЬНЫХ ссылок одним сообщением.\n\n"
        "То есть не так:\n"
        "https://t.me/channel1\n\n"
        "А вот так, чтобы каждая строка уже нажималась:\n\n"
        "🛍️ Вб дарит бесплатно\n"
        "💅 Трендовый маникюр\n"
        "📳 Рекко\n\n"
        "Важно: если строка не кликается у тебя в Telegram, бот тоже не сможет узнать ссылку.\n\n"
        "Для отмены нажми ❌ Отмена.",
        reply_markup=admin_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "⚙️ Каналы с проверкой")
def sponsor_channels_start(message):
    if message.from_user.id != ADMIN_ID:
        return

    admin_states[message.from_user.id] = "waiting_sponsor_channels"

    bot.send_message(
        message.chat.id,
        "⚙️ Отправь проверочные каналы списком.\n\n"
        "Формат простой:\n"
        "@channel1\n\n"
        "Формат со ссылкой:\n"
        "@channel1 | https://t.me/channel1\n\n"
        "Формат с названием:\n"
        "@channel1 | https://t.me/channel1 | 🔥 Твоя проверочная ссылка\n\n"
        "Формат с названием и местом вставки:\n"
        "@channel1 | https://t.me/channel1 | 🔥 Твоя проверочная ссылка | 21\n\n"
        "Где 21 — это место, куда вставить проверочную ссылку внутри общего списка.\n\n"
        "Если проверочных каналов два:\n"
        "@channel1 | https://t.me/channel1 | 🔥 Проверка 1 | 5\n"
        "@channel2 | https://t.me/channel2 | 🔥 Проверка 2 | 20\n\n"
        "Для отмены нажми ❌ Отмена.",
        reply_markup=admin_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "📋 Показать ссылки")
def show_links(message):
    if message.from_user.id != ADMIN_ID:
        return

    final_links = get_final_links_with_sponsors()
    channels = get_sponsor_channels()

    if not final_links:
        links_text = "Список ссылок пуст."
    else:
        links_text = build_clickable_links_text(final_links)

    text = "📋 Итоговый список ссылок:\n\n"
    text += links_text

    text += "\n\n📢 Проверочные каналы:\n\n"

    if not channels:
        text += "Список каналов пуст."
    else:
        for channel_id, channel, link, title, insert_position in channels:
            safe_channel = html.escape(str(channel))
            safe_title = html.escape(str(title))
            safe_link = html.escape(str(link))

            text += f"{channel_id}. {safe_channel}\n"
            text += f"Название: {safe_title}\n"
            text += f"Ссылка: {safe_link}\n"

            if insert_position:
                text += f"Место вставки: {insert_position}\n"
            else:
                text += "Место вставки: в конец списка\n"

            text += "\n"

    send_long_html_message(
        message.chat.id,
        text,
        reply_markup=admin_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    users_count = get_users_count()
    links_count = len(get_links())
    channels_count = len(get_sponsor_channels())

    bot.send_message(
        message.chat.id,
        "📊 Статистика\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"🔗 Ссылок: {links_count}\n"
        f"📢 Проверочных каналов: {channels_count}",
        reply_markup=admin_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "🗑 Очистить список ссылок")
def clear_links_handler(message):
    if message.from_user.id != ADMIN_ID:
        return

    count = len(get_links())

    clear_links()

    bot.send_message(
        message.chat.id,
        f"🗑 Список ссылок очищен.\n\nУдалено ссылок: {count}",
        reply_markup=admin_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "♻️ Сбросить проверочные каналы")
def reset_sponsor_channels_handler(message):
    if message.from_user.id != ADMIN_ID:
        return

    count = len(get_sponsor_channels())

    reset_default_sponsor_channels()

    bot.send_message(
        message.chat.id,
        f"♻️ Проверочные каналы сброшены.\n\n"
        f"Удалено старых каналов: {count}\n"
        f"Добавлено стандартных каналов: {len(DEFAULT_SPONSOR_CHANNELS)}",
        reply_markup=admin_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "❌ Отмена")
def cancel_admin_action(message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]

    bot.send_message(
        message.chat.id,
        "❌ Действие отменено.",
        reply_markup=admin_keyboard()
    )


# =========================
# ОБЫЧНЫЙ ТЕКСТ ОТ ПОЛЬЗОВАТЕЛЯ
# =========================

@bot.message_handler(content_types=["text"])
def handle_user_text(message):
    add_user_to_db(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    if message.from_user.id == ADMIN_ID:
        if message.text and message.text.startswith("/"):
            return

    show_answer_menu = types.InlineKeyboardMarkup(row_width=1)

    show_answer_menu.add(types.InlineKeyboardButton(
        text="ПОКАЗАТЬ ОТВЕТ",
        callback_data="show_answer"
    ))

    send_typing_message(
        message.chat.id,
        text="<b><i>Анализ полученных данных...</i></b>",
        delay=3
    )

    send_typing_message(
        message.chat.id,
        text="<b><i>Еще чуть-чуть...</i></b>",
        delay=3
    )

    send_typing_message(
        message.chat.id,
        text="<b><i>Ответ получен! 🪐</i></b>",
        delay=3,
        reply_markup=show_answer_menu
    )


# =========================
# ЗАПУСК
# =========================

try:
    bot.set_my_commands([
        types.BotCommand("start", "Запустить бота"),
        types.BotCommand("help", "Помощь"),
        types.BotCommand("admin", "Админ-панель")
    ])
except Exception as error:
    print("Не удалось установить команды бота:", error)

init_db()
import_users_from_txt()

print("Астробот запущен")

bot.infinity_polling(skip_pending=True)