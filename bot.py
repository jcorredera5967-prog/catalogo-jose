import os, time, asyncio, logging, threading, csv, io, urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, InlineQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "")
URL_CSV = "https://jcorredera5967-prog.github.io/catalogo-jose/datos.csv"
URL_WEB = "https://jcorredera5967-prog.github.io/catalogo-jose/"

logging.basicConfig(level=logging.INFO)
cache_filas = []
ultima_carga = 0

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Catalogo activo")

def iniciar_puerto_web():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), PingHandler).serve_forever()

def obtener_catalogo():
    global cache_filas, ultima_carga
    if not cache_filas or (time.time() - ultima_carga > 300):
        try:
            req = urllib.request.urlopen(URL_CSV + "?v=" + str(int(time.time())), timeout=15)
            texto = req.read().decode("utf-8-sig")
            cache_filas = list(csv.DictReader(io.StringIO(texto)))[::-1]
            ultima_carga = time.time()
        except Exception as e:
            logging.error("Error cargando CSV: %s", e)
    return cache_filas

async def buscar_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip().lower()
    if len(query) < 2:
        return
    filas = obtener_catalogo()
    resultados = []
    for idx, row in enumerate(filas):
        titulo = row.get("Título", "")
        director = row.get("Director", "")
        reparto = row.get("Reparto", "")
        if query in titulo.lower() or query in director.lower() or query in reparto.lower():
            cat = row.get("Categoría", "")
            carpeta = row.get("Carpeta", "")
            sinopsis = row.get("Sinopsis", "")
            if len(sinopsis) > 220:
                sinopsis = sinopsis[:220] + "..."
            enlace = row.get("Enlace", "")
            foto = row.get("Imagen", "")
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
            if len(resultados) >= 15:
                break
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
    threading.Thread(target=iniciar_puerto_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(InlineQueryHandler(buscar_inline))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bienvenida))
    app.run_polling()

if __name__ == "__main__":
    main()
