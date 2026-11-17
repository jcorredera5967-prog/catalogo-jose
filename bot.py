import os, time, asyncio, logging
import pandas as pd
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, InlineQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "")
URL_CSV = "https://jcorredera5967-prog.github.io/catalogo-jose/datos.csv"
URL_WEB = "https://jcorredera5967-prog.github.io/catalogo-jose/"

logging.basicConfig(level=logging.INFO)
cache_df = None
ultima_carga = 0

def obtener_catalogo():
    global cache_df, ultima_carga
    if cache_df is None or (time.time() - ultima_carga > 300):
        try:
            cache_df = pd.read_csv(URL_CSV + "?v=" + str(int(time.time())), encoding="utf-8-sig").fillna("")
            ultima_carga = time.time()
        except Exception as e:
            logging.error("Error cargando CSV: %s", e)
    return cache_df

async def buscar_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip().lower()
    if len(query) < 2:
        return
    df = obtener_catalogo()
    if df is None:
        return
    mask = (
        df["Título"].str.lower().str.contains(query, regex=False) |
        df["Director"].str.lower().str.contains(query, regex=False) |
        df["Reparto"].str.lower().str.contains(query, regex=False)
    )
    coincidencias = df[mask].iloc[::-1].head(15)
    resultados = []
    for idx, row in coincidencias.iterrows():
        titulo = str(row["Título"])
        cat = str(row["Categoría"])
        carpeta = str(row["Carpeta"])
        sinopsis = str(row["Sinopsis"])[:220] + "..." if len(str(row["Sinopsis"])) > 220 else str(row["Sinopsis"])
        enlace = str(row["Enlace"])
        foto = str(row["Imagen"])
        texto_msg = f"🎬 <b>{titulo}</b>\n📁 {cat} · {carpeta}\n\n{sinopsis}"
        botones = []
        if enlace.startswith("tg:") or enlace.startswith("http"):
            botones.append([InlineKeyboardButton("▶ Ver en Telegram", url=enlace)])
        botones.append([InlineKeyboardButton("🌐 Abrir Catálogo Completo", url=URL_WEB)])
        resultados.append(
            InlineQueryResultArticle(
                id=str(idx),
                title=titulo,
                description=f"{cat} | {carpeta}",
                thumbnail_url=foto if foto.startswith("http") else None,
                input_message_content=InputTextMessageContent(texto_msg, parse_mode="HTML"),
                reply_markup=InlineKeyboardMarkup(botones)
            )
        )
    await update.inline_query.answer(resultados, cache_time=60)

async def bienvenida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for miembro in update.message.new_chat_members:
        if miembro.is_bot:
            continue
        nombre = miembro.first_name
        texto = (
            f"👋 ¡Bienvenido/a, <b>{nombre}</b>!\n\n"
            "🎬 Aquí tienes acceso directo a todo nuestro catálogo de películas y series.\n"
            "💡 <i>Truco: Escribe @CatalogoJoseM2026_bot seguido de un título en el chat para buscar al instante.</i>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎬 Abrir Catálogo Web", url=URL_WEB)]])
        msg = await update.message.reply_text(texto, parse_mode="HTML", reply_markup=kb)
        await asyncio.sleep(120)
        try:
            await msg.delete()
        except Exception:
            pass

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(InlineQueryHandler(buscar_inline))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bienvenida))
    app.run_polling()

if __name__ == "__main__":
    main()
