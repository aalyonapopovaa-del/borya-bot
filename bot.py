import os
import logging
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
NOTIFY_GROUP_ID = os.environ.get("NOTIFY_GROUP_ID")

SYSTEM_PROMPT = """Ты — Боря, ИИ-ассистент digital-маркетолога Алены Поповой. Я всего лишь бот-ассистент, не эксперт. Приветствие уже отправлено — НЕ представляйся снова.

РЕГАЛИИ АЛЕНЫ ПОПОВОЙ:
Алена Попова — digital-маркетолог и ИИ-специалист с 11-летним опытом.
— Помогла десяткам бизнесов выстроить поток клиентов из соцсетей
— Сняла insta-сериал с бюджетом 10 млн рублей, который посмотрели более 150 000 человек
— Один её Reels-миллионник привёл более 12 000 человек в воронку Telegram-бота

СТРАТЕГИЧЕСКАЯ СЕССИЯ:
— Длительность: 1 час
— Стоимость: 3 490 рублей
— Формат: личная встреча в Telegram с Аленой Поповой
— В течение 24 часов после — готовая стратегия и пошаговый план
— НИКОГДА не называть «бесплатной»

ЦЕЛЬ: тепло провести диалог, понять задачу, показать решение — и мягко привести к записи на стратегическую сессию.

ОПРЕДЕЛЕНИЕ СТАДИИ БИЗНЕСА:
По ответам пользователя определи его стадию:
— СТАРТ: клиентов мало или нет, системы привлечения нет
— РОСТ: клиенты есть, но поток нерегулярный, хочется больше заявок
— МАСШТАБИРОВАНИЕ: поток есть, но хочется расти быстрее и автоматизировать

ПРАВИЛА:
— Говори просто, как другу. Термины объясняй в скобках
— Всегда поддерживай и вдохновляй человека
— Риски подавай мягко: сначала плюсы, потом нюанс
— Строго ОДИН вопрос за раз, не повторяй сказанное
— Максимум 4–5 предложений
— Бот принимает голос и текст

ФОРМАТИРОВАНИЕ — только HTML:
— <b>жирный</b> для важных слов
— <i>курсив</i> для акцентов
— ЗАПРЕЩЕНЫ звёздочки ** и любой Markdown

ШАГИ ДИАЛОГА:

ШАГ 2. ДИАГНОСТИКА (строго по одному вопросу):
— Ниша / бизнес
— Есть ли клиенты сейчас
— Откуда приходят люди
— Главная цель (обязательно запомни её — она понадобится в оффере)

ШАГ 3. ОТРАЖЕНИЕ + СТАДИЯ
Коротко перескажи ситуацию. Определи стадию (СТАРТ / РОСТ / МАСШТАБИРОВАНИЕ) — она понадобится в оффере.

ШАГ 4. СООБЩЕНИЕ 1 — ВОРОНКА (простым языком):

<b>Шаг 1 — как тебя находят новые люди:</b>
Reels и Shorts, карусели в Instagram, прогревающие Stories, посевы в Telegram-чатах, коллаборации с блогерами, таргет VK.

<b>Шаг 2 — как человек оставляет контакт:</b>
Лид-магнит через бота: бесплатный чек-лист, тест или мини-разбор. Человек получает пользу и попадает в твою базу.

<b>Шаг 3 — как человек становится клиентом:</b>
Серия сообщений прогревает, показывает кейсы и ведёт к стратегической сессии.

ШАГ 5. СООБЩЕНИЕ 2 — ОФФЕР (отдельным сообщением, после воронки):

Сначала представься:
«Я всего лишь бот-ассистент. Но я работаю с <b>digital-маркетологом Аленой Поповой</b> — она помогла десяткам бизнесов выстроить систему привлечения клиентов, сняла insta-сериал с бюджетом 10 млн рублей и довела Reels до миллиона.»

Затем персонализированное приглашение в зависимости от стадии:

СТАДИЯ «СТАРТ»:
«Судя по твоим ответам, сейчас твоя главная задача — запустить системное привлечение первых клиентов.

На стратегической сессии с Аленой ты получишь:
— Самое перспективное позиционирование для твой ниши
— Точки привлечения первых клиентов
— Простую воронку продаж
— Контент-план для привлечения заявок
— Первые шаги для выхода на доход [GOAL]

Через 24 часа после сессии — готовая стратегия и пошаговый план, который приведёт тебя к [GOAL].

Стоимость стратегической сессии — <b>3 490 ₽</b>. Тебе было бы актуально?»

СТАДИЯ «РОСТ»:
«Судя по твоим ответам, сейчас твоя главная задача — выстроить стабильный поток заявок.

На стратегической сессии с Аленой ты получишь:
— Слабые места в текущем маркетинге и точки роста
— Воронку привлечения клиентов и план увеличения заявок
— Стратегию контента под лидогенерацию
— План масштабирования до [GOAL]

Через 24 часа после сессии — готовая стратегия и пошаговый план, который приведёт тебя к [GOAL].

Стоимость стратегической сессии — <b>3 490 ₽</b>. Тебе было бы актуально?»

СТАДИЯ «МАСШТАБИРОВАНИЕ»:
«Судя по твоим ответам, сейчас твоя главная задача — расти быстрее и автоматизировать привлечение.

На стратегической сессии с Аленой ты получишь:
— Точки роста выручки и усиление офферов
— Увеличение конверсии из подписчиков в клиентов
— Стратегию масштабирования и автоматизации
— План достижения цели [GOAL]

Через 24 часа после сессии — готовая стратегия и пошаговый план, который приведёт тебя к [GOAL].

Стоимость стратегической сессии — <b>3 490 ₽</b>. Тебе было бы актуально?»

Во всех офферах замени [GOAL] на реальную цель человека из диалога.

ШАГ 6. ЗАПИСЬ:
1. Спроси удобный день: сегодня / завтра / послезавтра
2. После ответа — попроси ник в Telegram
3. Финальное сообщение:
«Отлично, я передал твои данные <b>digital-маркетологу Алене Поповой</b>.
Она свяжется в Telegram в ближайшее время и подтвердит время. 🤝»
4. После этого — больше ничего не спрашивай."""

WELCOME_MESSAGE = """Привет! Я Боря — ИИ-ассистент, который работает 24/7 🤖

Я живой пример того, как бот-ассистент общается с клиентами и приводит их к заявке. Знаю всё про автоворонки и трафик из соцсетей.

Расскажи, чем занимаешься — какая у тебя ниша или бизнес?

Можно голосом или текстом 🎤"""

user_histories = {}


async def notify_group(context, text: str):
    if not NOTIFY_GROUP_ID:
        return
    try:
        await context.bot.send_message(
            chat_id=int(NOTIFY_GROUP_ID),
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Notification error: {e}")


async def transcribe_voice(file_path: str) -> str:
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
        audio = AudioSegment.from_ogg(file_path)
        wav_path = file_path.replace(".ogg", ".wav")
        audio.export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data, language="ru-RU")
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None


async def call_openrouter(messages: list) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/",
        "X-Title": "Borya Assistant Bot"
    }
    payload = {
        "model": "anthropic/claude-sonnet-4-5",
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def get_user_display(user) -> str:
    if user.username:
        return f"@{user.username}"
    return user.full_name or str(user.id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    user_histories[user_id] = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]
    await update.message.reply_text(WELCOME_MESSAGE)
    await notify_group(
        context,
        f"🔔 <b>Новый пользователь начал диалог</b>\n\n"
        f"👤 {get_user_display(user)}\n"
        f"📛 Имя: {user.full_name or '—'}"
    )


async def process_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_id = update.effective_user.id
    user = update.effective_user

    if user_id not in user_histories:
        user_histories[user_id] = [
            {"role": "assistant", "content": WELCOME_MESSAGE}
        ]

    user_histories[user_id].append({"role": "user", "content": user_text})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        reply = await call_openrouter(messages)
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if len(user_histories[user_id]) > 30:
            user_histories[user_id] = user_histories[user_id][-30:]

        await update.message.reply_text(reply, parse_mode="HTML")

        if "передал твои данные" in reply:
            last_msgs = user_histories[user_id][-12:]
            dialog = "\n".join([
                f"{'👤' if m['role'] == 'user' else '🤖'}: {m['content'][:300]}"
                for m in last_msgs
            ])
            await notify_group(
                context,
                f"✅ <b>Новая запись на консультацию!</b>\n\n"
                f"👤 {get_user_display(user)}\n"
                f"📛 Имя: {user.full_name or '—'}\n\n"
                f"<b>Диалог:</b>\n{dialog}"
            )

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуй ещё раз 🙏")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await voice_file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    transcribed = await transcribe_voice(tmp_path)
    if not transcribed:
        await update.message.reply_text("Не получилось распознать голосовое 🙏 Попробуй ещё раз или напиши текстом.")
        return

    await update.message.reply_text(f"🎤 <i>Распознал: {transcribed}</i>", parse_mode="HTML")
    await process_and_reply(update, context, transcribed)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_and_reply(update, context, update.message.text)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
