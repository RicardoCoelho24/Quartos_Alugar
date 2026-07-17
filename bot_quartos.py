import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import scraper_olx
from keep_alive import manter_vivo

# Carrega as variáveis do ficheiro .env para uso local
load_dotenv()

# Adicionámos o estado GENERO à conversa
CIDADE, PRECO, GENERO = range(3)

async def iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia a conversa e mostra os botões de TODAS as regiões oficiais do OLX."""
    keyboard = [
        [InlineKeyboardButton("Aveiro", callback_data='aveiro'), InlineKeyboardButton("Beja", callback_data='beja')],
        [InlineKeyboardButton("Braga", callback_data='braga'), InlineKeyboardButton("Bragança", callback_data='braganca')],
        [InlineKeyboardButton("Castelo Branco", callback_data='castelobranco'), InlineKeyboardButton("Coimbra", callback_data='coimbra')],
        [InlineKeyboardButton("Évora", callback_data='evora'), InlineKeyboardButton("Faro", callback_data='faro')],
        [InlineKeyboardButton("Guarda", callback_data='guarda'), InlineKeyboardButton("Ilha da Graciosa", callback_data='graciosa')],
        [InlineKeyboardButton("Ilha da Madeira", callback_data='madeira'), InlineKeyboardButton("Ilha das Flores", callback_data='flores')],
        [InlineKeyboardButton("Ilha de Porto Santo", callback_data='portosanto'), InlineKeyboardButton("Ilha de Santa Maria", callback_data='santamaria')],
        [InlineKeyboardButton("Ilha de São Jorge", callback_data='saojorge'), InlineKeyboardButton("Ilha de São Miguel", callback_data='saomiguel')],
        [InlineKeyboardButton("Ilha do Corvo", callback_data='corvo'), InlineKeyboardButton("Ilha do Faial", callback_data='faial')],
        [InlineKeyboardButton("Ilha do Pico", callback_data='pico'), InlineKeyboardButton("Ilha Terceira", callback_data='terceira')],
        [InlineKeyboardButton("Leiria", callback_data='leiria'), InlineKeyboardButton("Lisboa", callback_data='lisboa')],
        [InlineKeyboardButton("Portalegre", callback_data='portalegre'), InlineKeyboardButton("Porto", callback_data='porto')],
        [InlineKeyboardButton("Santarém", callback_data='santarem'), InlineKeyboardButton("Setúbal", callback_data='setubal')],
        [InlineKeyboardButton("Viana do Castelo", callback_data='vianadocastelo'), InlineKeyboardButton("Vila Real", callback_data='vilareal')],
        [InlineKeyboardButton("Viseu", callback_data='viseu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Bem-vindo ao Alerta de Quartos! 🎓\n"
        "Vou monitorizar os anúncios por ti e enviar-te as novidades mais recentes.\n\n"
        "Selecione a região pretendida clicando num dos botões abaixo:",
        reply_markup=reply_markup
    )
    return CIDADE

async def receber_cidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    context.user_data['cidade'] = query.data 
    
    await query.edit_message_text("Qual é o **preço máximo** que queres pagar? (Insere apenas o número, ex: 250)")
    return PRECO

async def receber_preco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preco_escolhido = update.message.text.strip()
    
    if not preco_escolhido.isdigit():
        await update.message.reply_text("Por favor, insere apenas números inteiros (ex: 250).")
        return PRECO
    
    # Guarda o preço e passa para a pergunta do género
    context.user_data['preco'] = preco_escolhido
    
    keyboard = [
        [InlineKeyboardButton("👦 Apenas Rapazes", callback_data='rapaz')],
        [InlineKeyboardButton("👧 Apenas Raparigas", callback_data='rapariga')],
        [InlineKeyboardButton("👫 Misto / Qualquer", callback_data='qualquer')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Perfeito! E o quarto destina-se a quem?",
        reply_markup=reply_markup
    )
    return GENERO

async def receber_genero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    genero_escolhido = query.data
    
    cidade = context.user_data['cidade']
    preco_escolhido = context.user_data['preco']
    chat_id = update.effective_chat.id
    
    # Prepara o nome de exibição bonito para a mensagem final
    nomes_genero = {'rapaz': '👦 Rapaz', 'rapariga': '👧 Rapariga', 'qualquer': '👫 Misto / Qualquer'}
    nome_display = nomes_genero[genero_escolhido]
    
    await query.edit_message_text(
        f"Tudo configurado! ✅\n\n"
        f"📍 **Região:** {cidade.capitalize()}\n"
        f"💰 **Preço Máx:** {preco_escolhido}€\n"
        f"👤 **Filtro:** {nome_display}\n\n"
        f"A partir de agora, vou vigiar a zona selecionada a cada 5 minutos e envio-te uma mensagem assim que sair um quarto compatível."
    )
    
    trabalhos_antigos = context.job_queue.get_jobs_by_name(str(chat_id))
    for trabalho in trabalhos_antigos:
        trabalho.schedule_removal()
        
    # Agora passamos os 3 parâmetros para o job (cidade, preco, genero)
    context.job_queue.run_repeating(
        procurar_automaticamente, 
        interval=300, 
        first=1, 
        chat_id=chat_id,
        name=str(chat_id), 
        data={'cidade': cidade, 'preco': preco_escolhido, 'genero': genero_escolhido} 
    )
    
    return ConversationHandler.END

async def procurar_automaticamente(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    cidade = job.data['cidade']
    preco = job.data['preco']
    genero = job.data['genero']
    
    # Enviamos a nova variável de género para o motor de busca do OLX
    resultados = scraper_olx.procurar_quartos_olx(cidade, preco, genero)
    
    if resultados:
        for quarto_mensagem in resultados:
            await context.bot.send_message(chat_id=job.chat_id, text=quarto_mensagem, parse_mode='Markdown')

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pesquisa automática cancelada. Usa /start para recomeçar.")
    
    chat_id = update.effective_chat.id
    trabalhos_antigos = context.job_queue.get_jobs_by_name(str(chat_id))
    for trabalho in trabalhos_antigos:
        trabalho.schedule_removal()
        
    return ConversationHandler.END

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        print("🚨 ERRO CRÍTICO: Não encontraste o Token do Telegram!")
        print("Garante que o ficheiro .env existe e contém TELEGRAM_TOKEN=o_teu_token")
        return
    
    manter_vivo()
    
    application = Application.builder().token(TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', iniciar)],
        states={
            CIDADE: [CallbackQueryHandler(receber_cidade)],
            PRECO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_preco)],
            # Novo estado mapeado aqui
            GENERO: [CallbackQueryHandler(receber_genero)],
        },
        fallbacks=[CommandHandler('cancel', cancelar)],
    )

    application.add_handler(conv_handler)
    print("🤖 Bot Ativo e seguro! Pressiona Ctrl+C para parar.")
    application.run_polling()

if __name__ == '__main__':
    main()