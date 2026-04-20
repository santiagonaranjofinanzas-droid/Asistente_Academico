import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime
import uuid

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: Supabase credentials not found.")
    supabase: Client = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🤖 *Asistente Académico - Modo Captura Rápida*\n\n"
        "Hola. Envíame cualquier mensaje y lo convertiré automáticamente en una tarea pendiente en tu Dashboard.\n"
        "Ejemplo: *Hacer ensayo de liderazgo para el viernes*"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store incoming messages as tasks in Supabase."""
    text = update.message.text
    chat_id = update.effective_chat.id

    if not supabase:
        await update.message.reply_text("⚠️ Error: Base de datos no configurada.")
        return

    # Create task object
    # Defaulting to 1 week from now if no specific date logic is applied
    default_due_date = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()
    
    task_data = {
        "id_moodle": f"msg_{uuid.uuid4().hex[:8]}", # Unique ID for manual tasks
        "titulo": text[:50] + ("..." if len(text) > 50 else ""),
        "materia": "General",
        "descripcion": text,
        "estado": "por_empezar",
        "archivada": False,
        "fecha_entrega": default_due_date
    }
    
    try:
        supabase.table("tareas").insert(task_data).execute()
        await update.message.reply_text("✅ Tarea capturada y añadida a tu Dashboard.")
    except Exception as e:
        print(f"Error inserting task: {e}")
        await update.message.reply_text("❌ Hubo un error al guardar la tarea.")

def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    print("Iniciando Bot de Telegram para Captura Rápida...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
