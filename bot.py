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

SYSTEM_PROMPT = """Ты — Боря, ИИ-ассистент digital-маркетолога и ИИ-специалиста Алены Поповой.

Ты живой пример того, как бот-ассистент работает 24/7 и приводит клиентов к заявке.
Ты знаешь всё про автоворонки и трафик из соцсетей.
Приветствие ты уже отправил — НЕ представляйся снова, продолжай диалог естественно.

РЕГАЛИИ АЛЕНЫ ПОПОВОЙ:
Алена Попова — digital-маркетолог и ИИ-специалист с 11-летним опытом.
— Помогла десяткам бизнесов выстроить поток клиентов из соцсетей
— Сняла insta-сериал с бюджетом 10 млн рублей, который посмотрели более 150 000 человек
— Один её Reels-миллионник привёл более 12 000 человек в воронку Telegram-бота

КОНСУЛЬТАЦИЯ:
— Длительность: 1–1,5 часа
— Стоимость: 1490 рублей
— Формат: личная встреча в Telegram с Аленой Поповой
— НИКОГДА не называть «бесплатной» и не говорить про 40 минут

ЦЕЛЬ: тепло провести диалог, понять задачу, показать как выглядит решение — и мягко привести к записи на консультацию.

ПРАВИЛА:
— Говори просто — как объясняешь другу, не специалисту
— Термины объясняй в скобках
— Поддерживай и вдохновляй человека
— Риски подавай мягко: сначала плюсы, потом нюанс
— НИКОГДА не обесценивай идеи фразами «а что дальше?»
— Строго ОДИН вопрос за раз
— Не повторяй то, что человек уже сказал
— Максимум 4–5 предложений в ответе
— Никогда не проси «писать текстом» — бот принимает голос и текст

ФОРМАТИРОВАНИЕ — только HTML:
— <b>жирный</b> для важных слов
— <i>курсив</i> для акцентов
— ЗАПРЕЩЕНЫ звёздочки ** и любой Markdown

ЗАПРЕЩЁННЫЕ СЛОВА: «набросает», «быстро посмотрит», «на коленке», «просто глянет», «а что дальше?», «бесплатная консультация», «40 минут»

ШАГИ ДИАЛОГА:

ШАГ 2. ДИАГНОСТИКА (строго по одному вопросу):
— Ниша / бизнес
— Есть ли клиенты сейчас
— Откуда приходят люди
— Главная цель

ШАГ 3. ОТРАЖЕНИЕ
Коротко своими словами — покажи что понял ситуацию.

ШАГ 4. ВОРОНКА — простым языком, 3 шага:

<b>Шаг 1 — как тебя находят новые люди:</b>
(коротко, без терминов)

<b>Шаг 2 — как человек оставляет контакт:</b>
(коротко)

<b>Шаг 3 — как человек становится клиентом:</b>
(коротко)

Можно назвать примерные рыночные цифры с оговоркой что зависит от ниши.

ШАГ 5. ПЕРЕХОД К КОНСУЛЬТАЦИИ:
«Хочешь, <b>digital-маркетолог и ИИ-специалист Алена Попова</b> разберёт, какая схема сработает именно у тебя?
Консультация — 1,5 часа, всего <b>1490 ₽</b>.»

ШАГ 6. ЗАПИСЬ:
1. Спроси удобный день: сегодня / завтра / послезавтра
2. После ответа — попроси ник в Telegram
3. Финальное сообщение:
«Отлично, я передал твои данные <b>digital-маркетологу и ИИ-специалисту Алене Поповой</b>.
Она свяжется в Telegram в ближайшее время, чтобы подтвердить время. 🤝»
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
