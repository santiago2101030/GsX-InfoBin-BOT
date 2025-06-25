import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from colorama import init, Fore
import pycountry
import re
import ast
import os
import random
from datetime import datetime, timedelta

# Inicializar color en consola
init(autoreset=True)
print(Fore.GREEN + "Team GsX InfoBin On🔥")

# Claves API
BINTABLE_API_KEY = "672f3cd2ab924f41c60244737a9132939017f443"
APILAYER_API_KEY = "HPvKox4edGKSP3W6cLRBB2KVQIpyTAS4"

# Cargar grupos premium desde archivo
def cargar_grupos_premium():
    if not os.path.exists("GruposPremium.txt"):
        return set()
    with open("GruposPremium.txt", "r", encoding="utf-8") as f:
        texto = f.read()
        try:
            grupos = re.findall(r'Premium\s*=\s*(\[.*?\])', texto)
            if grupos:
                return set(ast.literal_eval(grupos[0]))
        except Exception:
            pass
    return set()

GRUPOS_PREMIUM = cargar_grupos_premium()

# Lista dinámica de grupos donde el bot está agregado (IDs de grupo)
GRUPOS_BOT = set()

# Función para guardar grupos nuevos en archivo "GruposReg.txt"
def guardar_grupo_en_archivo(grupo_id: int):
    filename = "GruposReg.txt"
    grupos_guardados = set()
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line_strip = line.strip()
                if line_strip:
                    try:
                        grupos_guardados.add(int(line_strip))
                    except ValueError:
                        continue
    if grupo_id not in grupos_guardados:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(f"{grupo_id}\n")
        print(Fore.GREEN + f"Nuevo grupo registrado en archivo: {grupo_id}")

# Guardar y leer métodos
def guardar_metodo(nombre, bin_):
    with open('Metodos.txt', 'a', encoding='utf-8') as f:
        f.write(f"{nombre} {bin_}\n")

def leer_metodos():
    try:
        with open('Metodos.txt', 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

# Consultar información de BINs en APIs externas
async def obtener_info_bin(bin_code: str):
    apis = [
        {
            "url": f"https://lookup.binlist.net/{bin_code}",
            "headers": {"Accept-Version": "3"},
            "parser": lambda d: {
                "marca": d.get("scheme", "N/A").title(),
                "tipo": d.get("type", "N/A").title(),
                "nivel": d.get("brand", "N/A"),
                "pais": d.get("country", {}).get("name", "N/A"),
                "banco": d.get("bank", {}).get("name", "N/A")
            }
        },
        {
            "url": f"https://api.bintable.com/v1/{bin_code}?api_key={BINTABLE_API_KEY}",
            "headers": {},
            "parser": lambda d: {
                "marca": d.get("scheme", "N/A"),
                "tipo": d.get("type", "N/A"),
                "nivel": d.get("card_level", "N/A"),
                "pais": d.get("country_name", "N/A"),
                "banco": d.get("issuer_name", "N/A")
            }
        },
        {
            "url": f"https://api.apilayer.com/bincheck/{bin_code}",
            "headers": {"apikey": APILAYER_API_KEY},
            "parser": lambda d: {
                "marca": d.get("scheme", "N/A"),
                "tipo": d.get("type", "N/A"),
                "nivel": d.get("brand", "N/A"),
                "pais": d.get("country_name", "N/A"),
                "banco": d.get("bank", {}).get("name", "N/A")
            }
        }
    ]

    async with aiohttp.ClientSession() as session:
        for api in apis:
            try:
                async with session.get(api["url"], headers=api["headers"], timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return api["parser"](data)
            except:
                continue
    return None

# Dibuja la bandera según el país
def emoji_bandera(nombre_pais: str) -> str:
    try:
        country = pycountry.countries.get(name=nombre_pais)
        if not country:
            for c in pycountry.countries:
                if nombre_pais.lower() in c.name.lower():
                    country = c
                    break
        if country:
            code = country.alpha_2.upper()
            return chr(127397 + ord(code[0])) + chr(127397 + ord(code[1]))
    except:
        pass
    return ""

# Formato del mensaje de respuesta del BIN
def formatear_mensaje(data: dict, bin_code: str) -> str:
    bandera = emoji_bandera(data['pais'])
    return (
        f"💳InfoBin: {bin_code}\n\n"
        f"Marca: {data['marca']}\n"
        f"Tipo: {data['tipo']}\n"
        f"Nivel: {data['nivel']}\n"
        f"Pais: {data['pais']} {bandera}\n"
        f"Banco: {data['banco']}\n\n"
        "Team GsX 🇨🇴"
    )

# Función para validar Luhn
def validar_luhn(numero: str) -> bool:
    total = 0
    reverse_digits = numero[::-1]
    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

# Función para generar un número de tarjeta válido completando desde BIN
def generar_numero_completo(bin_code: str) -> str:
    base = bin_code
    while True:
        numeros_random = ''.join(str(random.randint(0,9)) for _ in range(9))
        num15 = base + numeros_random[:-1]
        total = 0
        reverse_digits = num15[::-1]
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 0:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        mod = total % 10
        digito_control = '0' if mod == 0 else str(10 - mod)
        numero_final = num15 + digito_control
        if validar_luhn(numero_final):
            return numero_final

# Handler para .bin y /bin
async def handle_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        if text.lower().startswith(".bin "):
            parts = text.split()
        elif text.lower().startswith("/bin "):
            parts = text.split()
        else:
            return

        if len(parts) != 2:
            await update.message.reply_text("Uso correcto: .bin 457173")
            return

        bin_code = parts[1].strip()[:6]

        if len(bin_code) != 6 or not bin_code.isdigit():
            await update.message.reply_text("Uso correcto: .bin 457173")
            return

        user = update.message.from_user
        user_id = user.id
        username = f"@{user.username}" if user.username else "Sin username"
        nombre = f"{user.first_name or ''} {user.last_name or ''}".strip()

        try:
            with open("UsuariosInfoBin.txt", "a", encoding="utf-8") as file:
                file.write(f"ID: {user_id} | Usuario: {username} | Nombre: {nombre} | BIN: {bin_code}\n")
        except Exception:
            pass

        data = await obtener_info_bin(bin_code)
        if data:
            mensaje = formatear_mensaje(data, bin_code)
            await update.message.reply_text(mensaje)
        else:
            await update.message.reply_text("BIN no encontrado.")
    except Exception as e:
        print(f"Error en handle_bin: {e}")

# Handler para .extra y /extra
async def handle_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return
        chat_id = update.message.chat_id
        if chat_id not in GRUPOS_PREMIUM:
            await update.message.reply_text("🚫Solo Los Grupos Premium Pueden Usar Este Comando🚫")
            return

        text = update.message.text.strip()
        match = re.match(r'^[\./]extra\s+(\d{6})$', text)
        if not match:
            await update.message.reply_text("Uso correcto: .extra 530691")
            return

        bin_code = match.group(1)
        datos_bin = await obtener_info_bin(bin_code)
        banco = datos_bin["banco"] if datos_bin and datos_bin.get("banco") else "N/A"
        pais = datos_bin["pais"] if datos_bin and datos_bin.get("pais") else "N/A"
        resultados = []
        generados = 0
        intentos_maximos = 100
        intentos = 0
        ahora = datetime.now()
        minimo_vigencia = ahora + timedelta(days=30*5)

        while generados < 15 and intentos < intentos_maximos:
            numero = generar_numero_completo(bin_code)
            intentos += 1

            anio = random.randint(ahora.year, ahora.year + 6)
            if anio == ahora.year:
                mes_min = ahora.month + 5
                if mes_min > 12:
                    mes_min -= 12
                    anio += 1
                mes = random.randint(mes_min, 12)
            else:
                mes = random.randint(1, 12)

            fecha_expiracion = datetime(year=anio, month=mes, day=1)
            if fecha_expiracion < minimo_vigencia:
                continue

            numero_mostrar = numero[:12] + "xxxx"
            resultado = f"{numero_mostrar}|{mes:02}|{anio}|xxx"

            if resultado not in resultados:
                resultados.append(resultado)
                generados += 1

        if resultados:
            mensaje_completo = (
                "𝙶𝚜𝚇 𝙴𝚡𝚝𝚛𝚊𝙶𝚎𝚗\n"
                "──────────────\n" +
                "\n".join(resultados) +
                "\n──────────────\n"
                f"𝙱𝙸𝙽 ⥤ {bin_code}\n"
                f"𝙱𝙰𝙽𝙲𝙾 ⥤ {banco}\n"
                f"𝙿𝙰𝙸𝚂 ⥤ {pais}\n"
                f"𝙶𝚎𝚗 𝙱𝚢 ⥤ {('@' + update.message.from_user.username) if update.message.from_user.username else 'Sin username'}"
            )
            await update.message.reply_text(mensaje_completo)
        else:
            await update.message.reply_text("No se pudieron generar combinaciones válidas.")
    except Exception as e:
        print(f"Error en handle_extra: {e}")

# Handler para .comands y /comands
async def handle_comands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
            return
        chat_id = update.message.chat_id
        comandos_texto = (
            "⚡️GsX InfoBin Bot⚡\n"
            "Mis Comandos Son:\n\n"
            ".bin - Consulta información sobre un BIN\n"
        )
        if chat_id in GRUPOS_PREMIUM:
            comandos_texto += (
                ".reg - Registrar un método asociado a un BIN\n"
                ".metodos - Ver métodos registrados \n"
                ".infoGroup - Consulta su licencia\n"
                ".extra - Generar extrapolaciones de tarjeta (BIN)\n"
            )
        else:
            comandos_texto += (
                ".infoGroup - Consulta su licencia\n"
            )
        comandos_texto += (
            "\nGsX Team 🇨🇴\n\n"
            "Owner & Dev: @TYRANTGsX"
        )
        await update.message.reply_text(comandos_texto)
    except Exception as e:
        print(f"Error en handle_comands: {e}")

# Handler para .reg y /reg
async def handle_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return
        chat_id = update.message.chat_id
        if chat_id not in GRUPOS_PREMIUM:
            await update.message.reply_text("🚫Solo Los Grupos Premium Pueden Registrar Métodos🚫")
            return

        text = update.message.text.strip()
        match = re.match(r'^[\./]reg\s+(\w+)\s+(\d{6})\s+(\d+)$', text)
        if not match:
            await update.message.reply_text("Uso correcto: .reg App BIN CVV")
            return

        nombre = match.group(1)
        bin_ = match.group(2)
        codigo = match.group(3)
        guardar_metodo(nombre, f"{bin_} {codigo}")
        await update.message.reply_text(f"Método registrado: {nombre} {bin_} {codigo}")
    except Exception as e:
        print(f"Error en handle_reg: {e}")

# Handler para .metodos y /metodos
async def handle_metodos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
            return
        chat_id = update.message.chat_id
        if chat_id not in GRUPOS_PREMIUM:
            await update.message.reply_text("🚫Solo Los Grupos Premium Pueden Ver Los Métodos🚫")
            return

        metodos = leer_metodos()
        if metodos:
            await update.message.reply_text('\n'.join(metodos))
        else:
            await update.message.reply_text("No hay métodos registrados.")
    except Exception as e:
        print(f"Error en handle_metodos: {e}")

# Handler para .infoGroup y /infoGroup
async def handle_info_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
            return
        chat_id = update.message.chat_id
        if chat_id in GRUPOS_PREMIUM:
            premium_text = (
                "⚡️GsX InfoBin Bot⚡\n"
                "GsX Team 🇨🇴\n"
                "Este Grupo Cuenta Con Licencia Premium\n"
                "Owner & Dev: @TYRANTGsX"
            )
            await update.message.reply_text(premium_text)
        else:
            no_premium_text = (
                "⚡️GsX InfoBin Bot⚡\n"
                "GsX Team 🇨🇴\n"
                "Este Grupo No Cuenta Con Licencia Premium\n"
                "Contacta A Nuestro Owner\n"
                "Owner & Dev: @TYRANTGsX"
            )
            await update.message.reply_text(no_premium_text)
    except Exception as e:
        print(f"Error en handle_info_group: {e}")

# Saludo cuando el bot se agrega al grupo y registro de grupos nuevos
async def saludo_al_agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message and update.message.new_chat_members:
            for new_member in update.message.new_chat_members:
                if new_member.id == context.bot.id:
                    chat_id = update.message.chat_id
                    if chat_id not in GRUPOS_BOT:
                        GRUPOS_BOT.add(chat_id)
                        guardar_grupo_en_archivo(chat_id)
                        print(Fore.GREEN + f"Bot agregado al grupo {chat_id}")
                    await update.message.reply_text("Ya llegué perras🔥")
                    break
    except Exception as e:
        print(f"Error en saludo_al_agregar: {e}")

# Registrar grupo si hay mensajes (para asegurar que el bot conozca los grupos donde está)
async def registrar_grupo_por_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
            return
        chat_id = update.message.chat_id
        if chat_id not in GRUPOS_BOT:
            GRUPOS_BOT.add(chat_id)
            guardar_grupo_en_archivo(chat_id)
            print(Fore.GREEN + f"Detectado grupo nuevo: {chat_id}")
    except Exception as e:
        print(f"Error en registrar_grupo_por_mensaje: {e}")

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "Hola 👺\n\n"
            "Soy ⚡️GsX InfoBin Bot⚡:\n"
            "GsX Team 🇨🇴\n\n"
            "Owner & Dev: @TYRANTGsX\n"
            "Usa '.comands' Para Ver Mis Funciones"
        )
    except Exception as e:
        print(f"Error en start: {e}")

# ID del grupo GsXAdmin y del Owner
ID_GSX_ADMIN = -1002454854564
ID_OWNER = 7646063371

# Handler mejorado para el comando .gsend y /gsend
async def handle_gsend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
            return
            
        if update.message.chat_id != ID_GSX_ADMIN:
            await update.message.reply_text("🚫 Este comando solo se puede usar en el grupo GsXAdmin.")
            return

        if update.message.from_user.id != ID_OWNER:
            await update.message.reply_text("🚫 Solo el Owner puede usar este comando.")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("🚫 Debes responder a un mensaje para usar este comando.")
            return

        replied_msg = update.message.reply_to_message
        
        # Verificar si hay contenido para enviar
        if not (replied_msg.text or replied_msg.photo or replied_msg.video or 
                replied_msg.document or replied_msg.audio or replied_msg.voice or 
                replied_msg.video_note or replied_msg.sticker or replied_msg.animation):
            await update.message.reply_text("🚫 El mensaje debe contener contenido válido.")
            return
        
        # Función para enviar mensaje a un grupo específico
        async def enviar_a_grupo(grupo_id):
            try:
                if replied_msg.text:
                    # Mensaje de texto
                    await context.bot.send_message(chat_id=grupo_id, text=replied_msg.text)
                elif replied_msg.photo:
                    # Imagen
                    photo = replied_msg.photo[-1]  # La imagen de mayor resolución
                    await context.bot.send_photo(
                        chat_id=grupo_id, 
                        photo=photo.file_id, 
                        caption=replied_msg.caption
                    )
                elif replied_msg.video:
                    # Video
                    await context.bot.send_video(
                        chat_id=grupo_id, 
                        video=replied_msg.video.file_id, 
                        caption=replied_msg.caption
                    )
                elif replied_msg.document:
                    # Documento
                    await context.bot.send_document(
                        chat_id=grupo_id, 
                        document=replied_msg.document.file_id, 
                        caption=replied_msg.caption
                    )
                elif replied_msg.audio:
                    # Audio
                    await context.bot.send_audio(
                        chat_id=grupo_id, 
                        audio=replied_msg.audio.file_id, 
                        caption=replied_msg.caption
                    )
                elif replied_msg.voice:
                    # Nota de voz
                    await context.bot.send_voice(
                        chat_id=grupo_id, 
                        voice=replied_msg.voice.file_id, 
                        caption=replied_msg.caption
                    )
                elif replied_msg.video_note:
                    # Video circular
                    await context.bot.send_video_note(
                        chat_id=grupo_id, 
                        video_note=replied_msg.video_note.file_id
                    )
                elif replied_msg.sticker:
                    # Sticker
                    await context.bot.send_sticker(
                        chat_id=grupo_id, 
                        sticker=replied_msg.sticker.file_id
                    )
                elif replied_msg.animation:
                    # GIF
                    await context.bot.send_animation(
                        chat_id=grupo_id, 
                        animation=replied_msg.animation.file_id, 
                        caption=replied_msg.caption
                    )
                return True
            except Exception as e:
                print(f"Error al enviar mensaje al grupo {grupo_id}: {e}")
                return False
        
        # Verificar si se especifica un ID de grupo
        if context.args:
            try:
                grupo_id = int(context.args[0])
                if grupo_id not in GRUPOS_BOT:
                    await update.message.reply_text("🚫 El ID de grupo especificado no es válido.")
                    return
                
                if await enviar_a_grupo(grupo_id):
                    await update.message.reply_text("✅ Mensaje enviado al grupo especificado.")
                else:
                    await update.message.reply_text("❌ Error al enviar el mensaje al grupo especificado.")
            except ValueError:
                await update.message.reply_text("🚫 El ID de grupo debe ser un número válido.")
        else:
            # Enviar a todos los grupos
            enviados = 0
            errores = 0
            
            for grupo_id in GRUPOS_BOT:
                if await enviar_a_grupo(grupo_id):
                    enviados += 1
                else:
                    errores += 1

            mensaje_resultado = f"✅ Mensaje enviado a {enviados} grupos."
            if errores > 0:
                mensaje_resultado += f"\n❌ {errores} grupos con errores."
            
            await update.message.reply_text(mensaje_resultado)
            
    except Exception as e:
        print(f"Error en handle_gsend: {e}")
        await update.message.reply_text("❌ Error interno del bot.")

# Handler para el comando .list y /list
async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.from_user.id != ID_OWNER:
            await update.message.reply_text("🚫 Solo el Owner puede usar este comando.")
            return

        if not GRUPOS_BOT:
            await update.message.reply_text("No hay grupos registrados donde el bot esté presente.")
            return

        grupos_list = "\n".join(str(grupo_id) for grupo_id in GRUPOS_BOT)
        await update.message.reply_text(f"Grupos donde el bot está presente:\n{grupos_list}")
    except Exception as e:
        print(f"Error en handle_list: {e}")

# --- REGISTRO DE HANDLERS ---

if __name__ == "__main__":
    application = ApplicationBuilder().token("7839558236:AAE7P2wBVvbRD2WoNulC6H_P8nGa-ck_wl8").build()

    # Comandos con /
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("comands", handle_comands))
    application.add_handler(CommandHandler("infoGroup", handle_info_group))
    application.add_handler(CommandHandler("reg", handle_reg))
    application.add_handler(CommandHandler("metodos", handle_metodos))
    application.add_handler(CommandHandler("extra", handle_extra))
    application.add_handler(CommandHandler("bin", handle_bin))
    application.add_handler(CommandHandler("gsend", handle_gsend))
    application.add_handler(CommandHandler("list", handle_list))  # AGREGADO

    # Comandos con . (regex) - DEBEN IR ANTES del handler general
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\.bin "), handle_bin))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\.extra "), handle_extra))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\.comands$"), handle_comands))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\.reg "), handle_reg))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\.metodos$"), handle_metodos))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\.infoGroup$"), handle_info_group))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\.gsend"), handle_gsend))  # AGREGADO
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\.list$"), handle_list))  # AGREGADO

    # Handlers especiales
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, saludo_al_agregar))
    
    # IMPORTANTE: Este handler debe ir AL FINAL
    application.add_handler(MessageHandler(filters.ALL, registrar_grupo_por_mensaje))

    application.run_polling()



'''



                                                        L.           .          
                              j.                        EW:        ,ft          
   GEEEEEEEEEEEL  f.     ;WE. EW,                    .. E##;       t#E   GEEEEEEEEEEEL
  .,;;;;L#K;;;;.. E#,   i#G   E##j                  ;W, E###t      t#E  .,;;;;L#K;;;;..
        t#E       E#t  f#f    E###D.               j##, E#fE#f     t#E        t#E   
        t#E       E#t G#i     E#jG#W;             G###, E#t D#G    t#E        t#E   
        t#E       E#jEW,      E#t t##f          :E####, E#t  f#E.  t#E        t#E   
        t#E       E##E.       E#t  :K#E:       ;W# G##, E#t   t#K: t#E        t#E   
        t#E       E#G         E#KDDDD###i     j##  W##, E#t    ;#W,t#E        t#E   
        t#E       E#t         E#f,t#Wi,      G##i,,G##, E#t     :K#D#E        t#E   
        t#E       E#t         E#t  ;#W:    :K#K:   L##, E#t      .E##E        t#E   
        fE        EE.         DWi   ,KK:  ;##D.     ##, E#t        G#E         fE   
        :         t           DWi    DWi.             , E#t         fE          :   
                                                                     .

        


                                                                                                                                                                                                                                                    
'''