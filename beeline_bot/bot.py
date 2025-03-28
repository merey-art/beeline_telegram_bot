from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from service import authenticate_manual, get_all_devices, get_device_messages, create_excel_report
import pandas as pd

BOT_TOKEN = "7335573625:AAGC1E3VT5MCn5OrbSDP9AP2dQGSpyfsVMA"

EMAIL, PASSWORD, START_DATE, STOP_DATE = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Введите ваш email:")
    return EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text
    await update.message.reply_text("Теперь введите пароль:")
    return PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["password"] = update.message.text
    await update.message.reply_text("Введите начальную дату (дд-мм-гггг):")
    return START_DATE


async def get_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["start_date"] = update.message.text
    await update.message.reply_text("Введите конечную дату (дд-мм-гггг):")
    return STOP_DATE


async def get_stop_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["stop_date"] = update.message.text
    await update.message.reply_text("Генерирую отчет, подождите...")

    email = context.user_data["email"]
    password = context.user_data["password"]
    start_date = context.user_data["start_date"]
    stop_date = context.user_data["stop_date"]

    token = authenticate_manual(email, password)
    if not token:
        await update.message.reply_text("❌ Ошибка авторизации.")
        return ConversationHandler.END

    device_ids = get_all_devices(token)
    all_messages = []

    for device_id in device_ids:
        messages = get_device_messages(token, device_id, start_date, stop_date)
        if messages:
            df = pd.DataFrame(messages)
            df["device_id"] = device_id
            if "datetime_at_hour" not in df.columns:
                df["datetime_at_hour"] = "-"
            df["consumption"] = df.sort_values(by=["device_id", "datetime_at_hour"]).groupby("device_id")["in1"].diff().fillna("-")
            all_messages.append(df)

    report_file = create_excel_report(all_messages)
    if report_file:
        with open(report_file, "rb") as f:
            await update.message.reply_document(document=InputFile(f, filename=report_file))
    else:
        await update.message.reply_text("❌ Не удалось создать отчет.")

    return ConversationHandler.END


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_start_date)],
            STOP_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_stop_date)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()