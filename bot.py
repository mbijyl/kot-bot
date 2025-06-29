from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
from database import init_db, save_review, get_reviews
import hashlib
import asyncio
import nest_asyncio

# === НАСТРОЙКИ ===
DISHES = [
    "шакшука", "сырники", "карбонара", "крылышки", "английский завтрак", "овсяная каша",
    "бутерброды с красной рыбой", "блинчики", "оладьи", "вареное яйцо (пашот)",
    "вареное яйцо (всмятку)", "вареное яйцо (вкрутую)", "горячие бутерброды", "айс-латте",
    "курица в сливочно-сырном соусе", "курица в терияки соусе", "свиные ребрышки в кисло-сладком соусе",
    "свинина в барбекю соусе", "котлеты (куриные)", "котлеты (говяжьи)", "котлеты рубленые куриные с сыром",
    "куриные сердечки", "карри", "хинкал", "гуляш", "паста с креветками", "куриные голени", "окунь",
    "свинина по-китайски", "курица по-китайски", "стейк", "бургеры", "соларусят", "оливье", "крабовый салат",
    "окрошка", "лапша", "солянка", "том-ям", "щи с квашеной капустой", "эчпочмаки", "чебуреки", "пицца",
    "пирожки", "коктейль", "другое"
]
ROLES = ["Котенок-клиент", "Котенок-поваренок"]

# === СОСТОЯНИЯ ===
SELECT_ROLE, SELECT_DISH, SELECT_SCORE, GET_FEEDBACK = range(4)

# === Генератор клавиатуры блюд ===
def get_dishes_keyboard(context):
    keyboard = []
    context.user_data["dish_map"] = {}
    for d in DISHES:
        short = hashlib.md5(d.encode()).hexdigest()[:10]
        context.user_data["dish_map"][short] = d
        keyboard.append([InlineKeyboardButton(d, callback_data=f"dish:{short}")])
    return InlineKeyboardMarkup(keyboard)

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(role, callback_data=f"role:{role}")] for role in ROLES]
    await update.message.reply_text("Кто ты?", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_ROLE

# === Роль выбрана ===
async def role_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role = query.data.split(":", 1)[1]
    context.user_data["role"] = role
    await query.edit_message_text("выбери котячье блюдо:", reply_markup=get_dishes_keyboard(context))
    return SELECT_DISH

# === Блюдо выбрано ===
async def dish_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    short = query.data.split(":", 1)[1]
    dish = context.user_data.get("dish_map", {}).get(short)

    if not dish:
        await query.edit_message_text("ошибка: блюдо не найдено.")
        return ConversationHandler.END

    context.user_data["dish"] = dish

    if context.user_data["role"] == "Котенок-клиент":
        keyboard = [[InlineKeyboardButton(str(i), callback_data=f"score:{i}")] for i in range(1, 11)]
        await query.edit_message_text("оцени котячье блюдо:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_SCORE
    else:
        reviews = await get_reviews(dish)
        if not reviews:
            text = f"Нет отзывов по '{dish}'"
        else:
            text = f"Отзывы по '{dish}':\n\n"
            for score, comment in reviews:
                text += f"⭐ {score}/10 — {comment}\n\n"
        await query.edit_message_text(text[:4096])
        await query.message.reply_text("выбери следующее котячье блюдо:", reply_markup=get_dishes_keyboard(context))
        return SELECT_DISH

# === Оценка выбрана ===
async def score_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    score = int(query.data.split(":", 1)[1])
    context.user_data["score"] = score
    await query.edit_message_text("напиши текстовый отзыв!! котенок-поваренок прочтет и учтет его:")
    return GET_FEEDBACK

# === Отзыв получен ===
async def feedback_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dish = context.user_data["dish"]
    score = context.user_data["score"]
    text = update.message.text
    await save_review(dish, score, text)
    await update.message.reply_text("спасибо за твой котячий отзыв!✨")
    await update.message.reply_text("выбери следующее котячье блюдо:", reply_markup=get_dishes_keyboard(context))
    return SELECT_DISH

# === Главная функция ===
async def main():
    await init_db()
    app = ApplicationBuilder().token("7756995593:AAFgw0HL_gR52VZSN0HWWIQ6xesiOMvR2fo").build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_ROLE: [CallbackQueryHandler(role_selected, pattern=r"^role:")],
            SELECT_DISH: [CallbackQueryHandler(dish_selected, pattern=r"^dish:")],
            SELECT_SCORE: [CallbackQueryHandler(score_selected, pattern=r"^score:")],
            GET_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_received)],
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    print("бот запущен")
    await app.run_polling()

# === Запуск ===
if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
