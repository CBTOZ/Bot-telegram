import json
import os
import random
import re
from typing import Dict, Any, List, Set, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# 🔐 COLOQUE SEU TOKEN AQUI
TOKEN = "8681590933:AAE9nFaZBfMuOjsSZ9M3diiIfmPb2pFgjEA"

# 🔐 SENHA DO BOT
BOT_PASSWORD = "kx"

DATA_FILE = "data.json"

# Cada destino: {"name": str, "chat_id": int, "thread_id": Optional[int]}
DESTINOS: List[Dict[str, Any]] = []
AUTHORIZED_USERS: Set[int] = set()


# =============== SALVAR / CARREGAR ===============

def load_data():
    global DESTINOS, AUTHORIZED_USERS

    if not os.path.exists(DATA_FILE):
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        DESTINOS = data.get("destinos", [])
        AUTHORIZED_USERS = set(data.get("authorized_users", []))
    except Exception as e:
        print("Erro ao carregar data.json:", e)


def save_data():
    data = {
        "destinos": DESTINOS,
        "authorized_users": list(AUTHORIZED_USERS),
    }
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Erro ao salvar data.json:", e)


# =============== TEXTO DO ANÚNCIO ===============

def gerar_texto(preco: Optional[str], link: str) -> str:
    """Gera um texto de divulgação automático."""
    if preco:
        preco_txt = f"por {preco}"
    else:
        preco_txt = "com preço especial"

    modelos = [
        (
            "🔥 IRON DROP 👑\n\n"
            "💥 PROMO BUGADA!\n\n"
            f"💸 {preco_txt}\n\n"
            "⚡ Corre antes que acabe!\n"
            f"🔗 {link}"
        ),
        (
            "🚀 OFERTA RELÂMPAGO IRON DROP!\n\n"
            f"💸 {preco_txt}\n\n"
            "Quem chegar primeiro leva, depois some do mapa 😈\n"
            f"👉 {link}"
        ),
        (
            "🔥 ACHADO DA SEMANA IRON DROP!\n\n"
            f"💸 {preco_txt}\n\n"
            "Pra quem gosta de pagar pouco e andar no drip 😉\n"
            f"🔗 {link}"
        ),
    ]

    return random.choice(modelos)


def _get_nomes_topicos() -> List[str]:
    return sorted({d.get("name") for d in DESTINOS if d.get("name")})


async def _enviar_para_destinos(
    context: ContextTypes.DEFAULT_TYPE,
    destinos: List[Dict[str, Any]],
    texto: str,
) -> int:
    enviados = 0
    for d in destinos:
        chat_id = d.get("chat_id")
        thread_id = d.get("thread_id")
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=texto,
                message_thread_id=thread_id,
            )
            enviados += 1
        except Exception as e:
            print(f"Erro ao enviar para {chat_id} (topic {thread_id}):", e)
    return enviados


async def _gerar_previa_e_botoes(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    link: str,
    preco: Optional[str],
) -> None:
    if not DESTINOS:
        await update.message.reply_text(
            "❌ Nenhum tópico cadastrado ainda.\n"
            "Use /addtopic dentro dos tópicos desejados."
        )
        return

    await update.message.reply_text("⏳ Gerando PRÉVIA do anúncio...")

    texto = gerar_texto(preco, link)

    # Guardar no user_data (por usuário)
    context.user_data["pending_post"] = {
        "link": link,
        "preco": preco,
        "texto": texto,
    }

    nomes_topicos = _get_nomes_topicos()
    keyboard: List[List[InlineKeyboardButton]] = []

    for nome in nomes_topicos:
        keyboard.append([
            InlineKeyboardButton(
                f"🎯 Enviar em {nome}", callback_data=f"send_one:{nome}"
            )
        ])

    keyboard.append([InlineKeyboardButton("📤 Enviar em TODOS", callback_data="send_all")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_post")])

    await update.message.reply_text(
        "📝 *Prévia do anúncio:*\n\n"
        f"{texto}\n\n"
        "Agora escolha onde enviar:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =============== /start + BOTÕES ===============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔐 Login", callback_data="menu_login")],
        [InlineKeyboardButton("📌 Registrar Tópico", callback_data="menu_addtopic")],
        [InlineKeyboardButton("📋 Ver Tópicos", callback_data="menu_listtopics")],
        [InlineKeyboardButton("📤 Criar Post", callback_data="menu_post")],
        [InlineKeyboardButton("🗑 Gerenciar Tópicos", callback_data="menu_manage")],
    ]
    await update.message.reply_text(
        "👑 *BOT DE DIVULGAÇÃO IRON DROP*\n\n"
        "Escolha uma opção abaixo:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ===== MENU PRINCIPAL =====
    if data == "menu_login":
        await query.edit_message_text(
            "🔐 *Login*\n\n"
            "Envie no privado do bot:\n\n"
            "`/login SUA_SENHA`",
            parse_mode="Markdown",
        )
        return

    if data == "menu_addtopic":
        await query.edit_message_text(
            "📌 *Registrar Tópico*\n\n"
            "Dentro do *tópico* desejado (Shopee, Shein, etc), envie:\n\n"
            "`/addtopic NOME`\n\n"
            "Exemplos:\n`/addtopic shopee`\n`/addtopic shein`",
            parse_mode="Markdown",
        )
        return

    if data == "menu_listtopics":
        await query.edit_message_text(
            "📋 *Ver tópicos cadastrados*\n\n"
            "Envie:\n`/listtopics`",
            parse_mode="Markdown",
        )
        return

    if data == "menu_post":
        await query.edit_message_text(
            "📤 *Criar Post com PRÉVIA*\n\n"
            "Você pode:\n"
            "• Usar `/post LINK PRECO`\n"
            "• Ou só colar o LINK (se já tiver feito login)\n\n"
            "Exemplo:\n`/post https://s.shopee.com/xxxx 49,90`",
            parse_mode="Markdown",
        )
        return

    if data == "menu_manage":
        await query.edit_message_text(
            "🗑 *Gerenciar tópicos*\n\n"
            "• `/deltopic NOME` → remove tópicos com esse nome\n"
            "  Ex: `/deltopic shopee`\n\n"
            "• `/cleartopics` → apaga TODOS os tópicos cadastrados (cuidado)",
            parse_mode="Markdown",
        )
        return

    # ===== BOTÕES DE ENVIO (DEPOIS DA PRÉVIA) =====
    user_data = context.user_data
    pending = user_data.get("pending_post")

    if not pending and (data.startswith("send_one:") or data in ("send_all", "cancel_post")):
        await query.edit_message_text(
            "❌ Não existe post pendente.\n"
            "Use /post LINK PRECO ou cole um link para gerar nova prévia."
        )
        return

    if data == "cancel_post":
        user_data["pending_post"] = None
        await query.edit_message_text("❌ Envio cancelado. Nada foi enviado.")
        return

    if data == "send_all":
        texto = pending["texto"]
        enviados = await _enviar_para_destinos(context, DESTINOS, texto)
        user_data["pending_post"] = None
        await query.edit_message_text(
            f"✅ Anúncio enviado em {enviados} destino(s) (todos os tópicos cadastrados)."
        )
        return

    if data.startswith("send_one:"):
        nome = data.split(":", 1)[1]
        destinos = [d for d in DESTINOS if d.get("name") == nome]
        if not destinos:
            await query.edit_message_text(
                f"❌ Nenhum tópico cadastrado com o nome '{nome}'.\n"
                "Use /listtopics pra ver os nomes disponíveis."
            )
            return

        texto = pending["texto"]
        enviados = await _enviar_para_destinos(context, destinos, texto)
        user_data["pending_post"] = None
        await query.edit_message_text(
            f"✅ Anúncio enviado em {enviados} destino(s) com nome '{nome}'."
        )
        return


# =============== LOGIN ===============

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use:\n/login SENHA")
        return

    senha = context.args[0].strip()
    if senha == BOT_PASSWORD:
        AUTHORIZED_USERS.add(update.effective_user.id)
        save_data()
        await update.message.reply_text("✅ Login feito com sucesso! Pode usar /post ou só colar link.")
    else:
        await update.message.reply_text("❌ Senha incorreta.")


# =============== TÓPICOS ===============

async def addtopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use:\n/addtopic NOME")
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ Use /addtopic dentro de um grupo (de preferência com tópicos).")
        return

    nome = context.args[0].strip().lower()
    chat_id = chat.id
    thread_id = update.message.message_thread_id  # tópico específico ou None

    dest = {"name": nome, "chat_id": chat_id, "thread_id": thread_id}
    if dest not in DESTINOS:
        DESTINOS.append(dest)
        save_data()
        await update.message.reply_text(f"✅ Tópico '{nome}' registrado pra divulgação!")
    else:
        await update.message.reply_text("✅ Esse tópico já está registrado.")


async def listtopics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not DESTINOS:
        await update.message.reply_text("Nenhum tópico cadastrado.")
        return

    texto = "📋 Tópicos cadastrados:\n\n"
    for d in DESTINOS:
        texto += f"• {d.get('name')}\n"

    await update.message.reply_text(texto)


async def deltopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DESTINOS

    if not context.args:
        await update.message.reply_text("Use:\n/deltopic NOME")
        return

    nome = context.args[0].strip().lower()
    antes = len(DESTINOS)
    DESTINOS = [d for d in DESTINOS if d.get("name") != nome]
    removidos = antes - len(DESTINOS)
    save_data()

    if removidos > 0:
        await update.message.reply_text(f"🗑 Removido(s) {removidos} destino(s) com nome '{nome}'.")
    else:
        await update.message.reply_text(f"❌ Nenhum tópico com nome '{nome}' encontrado.")


async def cleartopics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DESTINOS

    if not DESTINOS:
        await update.message.reply_text("Não há tópicos pra apagar.")
        return

    qtd = len(DESTINOS)
    DESTINOS = []
    save_data()
    await update.message.reply_text(f"⚠️ Todos os {qtd} tópicos foram apagados.")


# =============== POST / AUTO-LINK ===============

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Você precisa fazer /login antes.")
        return

    if not context.args:
        await update.message.reply_text("Use:\n/post LINK PRECO\nEx:\n/post https://s.shopee.com/xxx 49,90")
        return

    link = context.args[0].strip()
    preco: Optional[str] = None

    if len(context.args) > 1:
        preco_txt = context.args[1].strip()
        if not preco_txt.lower().startswith("r$"):
            preco_txt = "R$ " + preco_txt
        preco = preco_txt

    await _gerar_previa_e_botoes(update, context, link, preco)


async def auto_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quando o usuário só cola um link (sem /post)."""
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_USERS:
        return

    if not update.message or not update.message.text:
        return

    texto = update.message.text.strip()
    match = re.search(r"https?://\S+", texto)
    if not match:
        return

    link = match.group(0)

    # tentar achar preço no texto, tipo 49,90
    preco_match = re.search(r"\d+[,\.]\d{2}", texto)
    preco: Optional[str] = None
    if preco_match:
        valor = preco_match.group(0).replace(",", ".")
        # transformar em R$ xx,xx
        preco = "R$ " + valor.replace(".", ",")

    await _gerar_previa_e_botoes(update, context, link, preco)


# =============== MAIN ===============

def main():
    load_data()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("addtopic", addtopic))
    app.add_handler(CommandHandler("listtopics", listtopics))
    app.add_handler(CommandHandler("deltopic", deltopic))
    app.add_handler(CommandHandler("cleartopics", cleartopics))
    app.add_handler(CommandHandler("post", post))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_link_handler))

    print("IRON DROP bot rodando (versão simples, sem scraping)...")
    app.run_polling()


if __name__ == "__main__":
    main()