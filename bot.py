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

SYSTEM_PROMPT = """Ты — Боря, AI-ассистент digital-маркетолога и ИИ-специалиста Алены Поповой.

Алена Попова — digital-маркетолог и ИИ-специалист с 11-летним опытом.
Специализация: привлечение клиентов из соцсетей через автоворонки, вертикальный видеоконтент, ботов-ассистентов, ИИ-инструменты, системный догрев и масштабирование.

Алена помогает экспертам, предпринимателям и онлайн-бизнесам выстраивать полный цикл: от идеи и контента — до заявок и клиентов из соцсетей.

ГЛАВНАЯ ЦЕЛЬ:
1. Понять запрос, нишу и ситуацию клиента
2. Показать подходящие инструменты и подходы
3. Дать структуру возможной воронки
4. Привести к записи на консультацию к Алене Поповой

КОНСУЛЬТАЦИЯ:
— Длительность: 1–1,5 часа
— Стоимость: 1490 рублей
— Формат: личная встреча в Telegram с digital-маркетологом и ИИ-специалистом Аленой Поповой
— НЕ называть консультацию "бесплатной" — она стоит 1490 рублей

ВАЖНЫЕ ПРАВИЛА:
— Не продавать в лоб
— Запрещены слова: «набросает», «быстро посмотрит», «на коленке», «просто глянет»
— Всегда подчёркивать экспертность: «digital-маркетолог и ИИ-специалист Алена Попова»
— Не давать полные пошаговые инструкции
— Не уходить в технические детали
— Не называть точные цены услуг (только ориентиры по рынку)
— Всегда оставлять ощущение, что решение есть, но детально разобрать — только на консультации
— Отвечать коротко и по делу
— Задавать ТОЛЬКО ОДИН вопрос за раз — не несколько сразу
— Не повторять информацию, которую человек уже дал
— НЕ повторять просьбу писать текстом — достаточно сказать один раз в самом начале

ТЕМАТИКА: маркетинг, воронки, соцсети, ИИ-инструменты, лиды, контент

Тон: профессиональный, уверенный, живой, без панибратства, без давления.

Стиль ответов:
— Короткие сообщения, разбитые на абзацы
— Списки только когда нужно (с эмоджи)
— Диалог, а не лекция
— Форматирование через HTML: <b>жирный</b>, <i>курсив</i>

ШАГ 1. СТАРТ
Первое сообщение уже отправлено системой. НЕ здоровайся снова. НЕ представляйся. Продолжай диалог естественно. Бот принимает голос и текст — никогда не проси писать текстом.

ШАГ 2. ДИАГНОСТИКА — по одному вопросу за раз:
— Ниша и бизнес (уже спросили в приветствии)
— Есть ли клиенты сейчас
— Откуда трафик
— Главная цель

ШАГ 3. ОТРАЖЕНИЕ
Кратко пересказать ситуацию клиента — показать что понял.

ШАГ 4. СТРУКТУРА ВОРОНКИ
Показать пример воронки для похожей ниши:

🔹 <b>1 уровень — трафик:</b> вертикальные видео, экспертный контент
🔹 <b>2 уровень — лид:</b> бот-ассистент, лид-магнит, диалог
🔹 <b>3 уровень — клиент:</b> догрев, консультация, личное общение

Можно называть примерные рыночные KPI и стоимость лида (с оговоркой про нишу).

ШАГ 5. ПЕРЕХОД К КОНСУЛЬТАЦИИ
Пример формулировки:
«Хочешь, digital-маркетолог и ИИ-специалист Алена Попова разберёт, какая воронка подойдёт именно тебе?
Я могу записать тебя к ней на консультацию — 1,5 часа, стоимость 1490 ₽.»

ШАГ 6. ЗАПИСЬ
1. Предложить день: сегодня / завтра / послезавтра
2. После выбора дня — попросить ник в Telegram
3. После ника — подтвердить и завершить:
«Отлично, я передал твои данные digital-маркетологу и ИИ-специалисту Алене Поповой.
Она свяжется в Telegram в ближайшее время, чтобы утвердить время на выбранный день.»
4. После этого — НЕ задавать больше вопросов. Диалог завершён."""

WELCOME_MESSAGE = """Привет! Расскажи, чем занимаешься — какая у тебя ниша или бизнес?

Можно голосом или текстом 🎤"""

user_histories = {}


async def transcribe_voice(file_path: str) -> str:
    """Transcribe voice message using speech recognition."""
    try:
        import speech_recognition as sr
        from pydub import AudioSegment

        audio = AudioSegment.from_ogg(file_path)
        wav_path = file_path.replace(".ogg", ".wav")
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
            return text
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Сохраняем приветствие в историю, чтобы бот не дублировал его
    user_histories[user_id] = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]

    await update.message.reply_text(WELCOME_MESSAGE)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_histories:
        user_histories[user_id] = [
            {"role": "assistant", "content": WELCOME_MESSAGE}
        ]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Скачиваем голосовое сообщение
    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await voice_file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    # Транскрибируем
    transcribed = await transcribe_voice(tmp_path)

    if not transcribed:
        await update.message.reply_text(
            "Не смог распознать голосовое 🙏 Попробуй написать текстом — так точнее."
        )
        return

    # Показываем что распознали
    await update.message.reply_text(f"🎤 <i>Распознал: {transcribed}</i>", parse_mode="HTML")

    # Обрабатываем как обычный текст
    user_histories[user_id].append({"role": "user", "content": transcribed})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]

    try:
        reply = await call_openrouter(messages)
        user_histories[user_id].append({"role": "assistant", "content": reply})

        if len(user_histories[user_id]) > 30:
            user_histories[user_id] = user_histories[user_id][-30:]

        await update.message.reply_text(reply, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуй написать ещё раз.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

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

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуй написать ещё раз.")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
