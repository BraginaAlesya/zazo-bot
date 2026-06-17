"""
3а3о · Бот для выдачи билетов
Данные хранятся в /data/tickets.json (Railway Volume)
Команды: /билет  /список  /отмена
"""

import os
import json
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from ticket_gen import generate_ticket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN   = os.environ.get("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_СЮДА")

# Путь к файлу билетов:
# - на Railway Volume → /data/tickets.json (не удаляется никогда)
# - локально → tickets.json рядом с ботом
DATA_DIR     = os.environ.get("DATA_DIR", ".")
TICKETS_FILE = os.path.join(DATA_DIR, "tickets.json")

# Создаём папку если не существует
os.makedirs(DATA_DIR, exist_ok=True)

# Шаги диалога
ФИО, МЕСТА, СУММА, КОНТАКТ = range(4)

# Telegram username → имя на билете
REGISTRARS = {
    "alesyabragina": "Алеся",
    "raventa007": "Женя",
}
DEFAULT_REGISTRAR = "Команда 3а3о"


def load_tickets():
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_tickets(tickets):
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)


def next_ticket_number():
    tickets = load_tickets()
    if not tickets:
        return 1
    return max(t["number"] for t in tickets) + 1


def get_registrar_name(user) -> str:
    username = (user.username or "").lower()
    return REGISTRARS.get(username, user.first_name or DEFAULT_REGISTRAR)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎟 *Бот выдачи билетов 3а3о*\n\n"
        "Команды:\n"
        "• /билет — выдать новый билет\n"
        "• /список — все выданные билеты\n"
        "• /отмена — отменить текущий диалог",
        parse_mode="Markdown"
    )


async def cmd_билет(update: Update, context: ContextTypes.DEFAULT_TYPE):
    registrar = get_registrar_name(update.effective_user)
    context.user_data["registrar"] = registrar
    context.user_data["ticket_number"] = next_ticket_number()

    await update.message.reply_text(
        f"🎟 Билет №{context.user_data['ticket_number']:03d}\n"
        f"Регистратор: *{registrar}*\n\n"
        "Шаг 1/4 — Введи *ФИО* гостя:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ФИО


async def get_фио(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["фио"] = update.message.text.strip()
    await update.message.reply_text("Шаг 2/4 — Сколько *мест* (человек)?",
                                    parse_mode="Markdown")
    return МЕСТА


async def get_места(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await update.message.reply_text("⚠️ Введи число, например: 2")
        return МЕСТА
    context.user_data["места"] = int(text)
    await update.message.reply_text("Шаг 3/4 — Какая *сумма оплачена* (₽)?",
                                    parse_mode="Markdown")
    return СУММА


async def get_сумма(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(" ", "").replace("₽", "")
    if not text.isdigit():
        await update.message.reply_text("⚠️ Введи сумму цифрами, например: 1600")
        return СУММА
    context.user_data["сумма"] = int(text)
    await update.message.reply_text("Шаг 4/4 — *Контакт* гостя (Telegram, ВКонтакте или телефон):",
                                    parse_mode="Markdown")
    return КОНТАКТ


async def get_контакт(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["контакт"] = update.message.text.strip()

    data = context.user_data
    now  = datetime.now()

    ticket_data = {
        "number":    data["ticket_number"],
        "фио":       data["фио"],
        "места":     data["места"],
        "сумма":     data["сумма"],
        "контакт":   data["контакт"],
        "registrar": data["registrar"],
        "timestamp": now.strftime("%d.%m.%Y %H:%M"),
    }

    # Сохраняем в постоянное хранилище
    tickets = load_tickets()
    tickets.append(ticket_data)
    save_tickets(tickets)

    await update.message.reply_text("⏳ Генерирую билет...")
    img_path = generate_ticket(ticket_data)

    with open(img_path, "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=(
                f"✅ *Билет №{ticket_data['number']:03d} выдан*\n"
                f"Гость: {ticket_data['фио']}\n"
                f"Мест: {ticket_data['места']} · "
                f"Оплачено: {ticket_data['сумма']:,} ₽\n"
                f"Контакт: {ticket_data['контакт']}"
            ).replace(",", " "),
            parse_mode="Markdown"
        )

    os.remove(img_path)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def cmd_список(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickets = load_tickets()
    if not tickets:
        await update.message.reply_text("📋 Билеты ещё не выдавались.")
        return

    lines = [f"📋 *Выдано билетов: {len(tickets)}*\n"]
    total_seats, total_sum = 0, 0

    for t in tickets:
        lines.append(
            f"№{t['number']:03d} · {t['фио']} · "
            f"{t['места']} мест · {t['сумма']:,} ₽\n"
            f"     📞 {t['контакт']} · {t['timestamp']}"
        )
        total_seats += t["места"]
        total_sum   += t["сумма"]

    lines.append(f"\n💰 Итого: {total_seats} мест · {total_sum:,} ₽")
    text = "\n".join(lines).replace(",", " ")

    if len(text) > 4000:
        for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("билет", cmd_билет)],
        states={
            ФИО:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_фио)],
            МЕСТА:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_места)],
            СУММА:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_сумма)],
            КОНТАКТ: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_контакт)],
        },
        fallbacks=[CommandHandler("отмена", cancel)],
    )

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("список", cmd_список))
    app.add_handler(conv)

    logger.info("Бот 3а3о запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
