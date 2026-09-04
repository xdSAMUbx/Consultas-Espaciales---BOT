import re, logging, html, time
from telegram import Update
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler, MessageHandler, filters, PicklePersistence

from .sesion import Sesion, Estado
from .config import Config
from ..ia.servicio_consultas import ServicioConsultas
from ..sql.motor_sql import MotorConsultas
from ..ia.cliente_ia import ClienteIA

logger = logging.getLogger(__name__)

class Orquestador:
    TIEMPO_AVISO = 5 * 60
    TIEMPO_CIERRE = 60

    COOLDOWN = 5           # segundos entre consultas del mismo usuario
    LIMITE_DIARIO = 25     # consultas por usuario al día
    LIMITE_GLOBAL = 400    # consultas totales al día, tope de gasto
    MAX_CARACTERES = 300   # largo máximo de una pregunta

    PATRONES_NOMBRE = [
    r"me llamo\s+(.+)",
    r"mi nombre es\s+(.+)",
    r"soy\s+(.+)",
    ]
    FRASE_SALIDA = "No quiero continuar con la conversación"
    FRASE_OLVIDO = "Olvídame"

    def __init__(self, textos: Config, servicio: ServicioConsultas):
        self.textos = textos
        self.servicio = servicio

    def _extraer_nombre(self, texto:str) -> str:
        texto_limpio = texto.strip()
        for patron in self.PATRONES_NOMBRE:
            match = re.search(patron, texto_limpio, re.IGNORECASE)
            if match:
                return match.group(1).strip(" .,!¡").title()
        return texto_limpio.title()

    # timers
    def _cancelar_temporizadores(self, context, chat_id):
        for nombre_job in (f"aviso_{chat_id}", f"cierre_{chat_id}"):
            for job in context.job_queue.get_jobs_by_name(nombre_job):
                job.schedule_removal()

    async def _cerrar_por_inactividad(self, context):
        chat_id = context.job.chat_id
        if context.user_data is not None:
            context.user_data.pop("estado", None)
        await context.bot.send_message(chat_id, self.textos.get("inactividad.cierre"))

    async def _avisar_inactividad(self, context):
        chat_id = context.job.chat_id
        try:
            await context.bot.send_message(chat_id, self.textos.get("inactividad.aviso"))
        except Exception:
            logger.warning("No se pudo avisar inactividad a %s", chat_id)
            return
        context.job_queue.run_once(
            self._cerrar_por_inactividad, self.TIEMPO_CIERRE,
            chat_id = chat_id, user_id = chat_id, name = f"cierre_{chat_id}"
        )
        
    def _programar_aviso(self, context, chat_id):
        self._cancelar_temporizadores(context, chat_id)
        context.job_queue.run_once(
            self._avisar_inactividad, self.TIEMPO_AVISO,
            chat_id = chat_id, user_id = chat_id, name = f"aviso_{chat_id}"
        )    

    # Handlers
    async def cancelar(self, update:Update, context:ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        self._cancelar_temporizadores(context, chat_id)
        sesion = Sesion(context)
        sesion.cerrar_sesion()
        if update.message:
            await update.message.reply_text(self.textos.get("comandos.cancelado"))

    async def _cerrar_por_comando(self, update, context, sesion: Sesion):
        chat_id = update.effective_chat.id
        self._cancelar_temporizadores(context, chat_id)
        sesion.cerrar_sesion()
        await update.message.reply_text(self.textos.get("comandos.cancelado"))

    async def manejar_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error("Excepción no manejada: %s", context.error, exc_info=context.error)
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(self.textos.get("errores.generico"))
            except Exception:
                pass

    async def manejar_mensaje(self, update:Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
        
        chat_id = update.effective_chat.id
        texto = update.message.text
        sesion = Sesion(context)

        if texto.strip().lower() == self.FRASE_OLVIDO.lower():
            self._cancelar_temporizadores(context, chat_id)
            sesion.olvidar()
            await update.message.reply_text(self.textos.get("comandos.olvidado"))
            return

        if texto.strip().lower() == self.FRASE_SALIDA.lower():
            await self._cerrar_por_comando(update, context, sesion)
            return

        self._programar_aviso(context, chat_id)

        if sesion.estado is None:
            if sesion.nombre:
                sesion.estado = Estado.EN_MENU
                await update.message.reply_text(
                    self.textos.get("bienvenida_regreso", nombre=sesion.nombre)
                )
            else:
                sesion.estado = Estado.ESPERANDO_NOMBRE
                await update.message.reply_text(self.textos.get("saludo"))
            return

        if sesion.estado == Estado.ESPERANDO_NOMBRE:
            nombre = self._extraer_nombre(texto)
            sesion.nombre = nombre
            sesion.estado = Estado.EN_MENU
            await update.message.reply_text(self.textos.get("bienvenida", nombre=nombre))
            return

        if sesion.estado == Estado.EN_MENU:
            if len(texto) > self.MAX_CARACTERES:
                await update.message.reply_text(
                    f"Tu pregunta es muy larga (máximo {self.MAX_CARACTERES} caracteres)."
                )
                return

            ahora = time.time()
            hoy = time.strftime("%Y-%m-%d")

            # cooldown
            ultima = context.user_data.get("ultima_consulta", 0)
            if ahora - ultima < self.COOLDOWN:
                restante = int(self.COOLDOWN - (ahora - ultima)) + 1
                await update.message.reply_text(f"Espera {restante} segundos antes de la siguiente consulta.")
                return

            # límite por usuario
            if context.user_data.get("dia") != hoy:
                context.user_data["dia"] = hoy
                context.user_data["consultas_hoy"] = 0

            if context.user_data["consultas_hoy"] >= self.LIMITE_DIARIO:
                await update.message.reply_text(
                    f"Llegaste al límite de {self.LIMITE_DIARIO} consultas por hoy. Vuelve mañana."
                )
                return

            # límite global (protege el saldo)
            bot_data = context.application.bot_data
            if bot_data.get("dia_global") != hoy:
                bot_data["dia_global"] = hoy
                bot_data["consultas_global"] = 0

            if bot_data["consultas_global"] >= self.LIMITE_GLOBAL:
                await update.message.reply_text(
                    "El bot alcanzó su límite de consultas del día. Intenta mañana."
                )
                return

            context.user_data["ultima_consulta"] = ahora
            context.user_data["consultas_hoy"] += 1
            bot_data["consultas_global"] += 1

            await update.message.chat.send_action("typing")
            try:
                resultado = await self.servicio.responder(texto)
            except Exception:
                logger.exception("Error procesando consulta")
                await update.message.reply_text(self.textos.get("errores.consulta"))
                return
            if resultado.sql:
                sesion.ultimo_sql = resultado.sql
            await update.message.reply_text(resultado.texto, parse_mode="HTML")
            return

    async def mostrar_sql(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        sesion = Sesion(context)
        if not sesion.ultimo_sql:
            await update.message.reply_text("Todavía no has hecho ninguna consulta.")
            return
        await update.message.reply_text(
            f"<pre>{html.escape(sesion.ultimo_sql)}</pre>", parse_mode="HTML"
        )

    async def uso(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        hoy_usuario = context.user_data.get("consultas_hoy", 0)
        global_hoy = context.application.bot_data.get("consultas_global", 0)
        await update.message.reply_text(
            f"Tus consultas hoy: {hoy_usuario}/{self.LIMITE_DIARIO}\n"
            f"Consultas del bot hoy: {global_hoy}/{self.LIMITE_GLOBAL}"
        )

    @classmethod
    def main(cls):
        config = Config()

        cliente_ia = ClienteIA(
            api_key=config.env("LLM_API_KEY"),
            modelo=config.env("LLM_MODEL"),
            base_url=config.env("LLM_BASE_URL"),
        )
        motor_sql = MotorConsultas(dsn=config.env("DATABASE_URL"))
        servicio = ServicioConsultas(cliente_ia, motor_sql)
        orquestador = cls(textos=config, servicio=servicio)

        async def post_init(app):
            await motor_sql.conectar()
            print("Pool de Postgres listo.")

        async def post_shutdown(app):
            await motor_sql.cerrar()

        persistencia = PicklePersistence(filepath="datos_bot.pickle")

        app = (
            ApplicationBuilder()
            .token(config.env("TELEGRAM_TOKEN"))
            .persistence(persistencia)
            .concurrent_updates(20)
            .post_init(post_init)
            .post_shutdown(post_shutdown)
            .build()
        )

        app.add_handler(CommandHandler("cancel", orquestador.cancelar))
        app.add_handler(CommandHandler("sql", orquestador.mostrar_sql))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, orquestador.manejar_mensaje))
        app.add_handler(CommandHandler("uso", orquestador.uso))

        print("Bot corriendo... CTRL+C para detener.")
        app.run_polling(drop_pending_updates=True)
