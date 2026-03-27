import discord
from discord.ext import commands
from discord import app_commands
import os

# ─── CONFIGURACIÓN ───────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN")

CANAL_CREAR_FICHA     = 1486894283343794227   # #crear-ficha
CANAL_FICHAS_PUBLICAS = 1486894336330170568   # #fichas-jugadores
CATEGORIA_PRIVADA     = 1392580433602023560   # categoría fichajes privados
# ─────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ══════════════════════════════════════════════════════════════
#  MODAL — Formulario de ficha
# ══════════════════════════════════════════════════════════════
class FichaModal(discord.ui.Modal, title="🏀 Ficha de Jugador"):
    nombre = discord.ui.TextInput(
        label="👤 Nombre o Gamertag",
        placeholder="Ej: KingJames23",
        max_length=50,
        required=True,
    )
    posicion = discord.ui.TextInput(
        label="📍 Posición",
        placeholder="Base / Escolta / Alero / Ala-Pívot / Pívot",
        max_length=30,
        required=True,
    )
    stats = discord.ui.TextInput(
        label="📊 Stats por partido",
        placeholder="PPG: 20 · RPG: 8 · APG: 5 · SPG: 2 · BPG: 1",
        style=discord.TextStyle.short,
        required=True,
    )
    equipos = discord.ui.TextInput(
        label="🏆 Equipos anteriores",
        placeholder="¿Dónde has jugado antes?",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=200,
    )
    frase = discord.ui.TextInput(
        label="💬 Tu frase de cancha",
        placeholder="La frase que te define",
        max_length=100,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        canal_publico = interaction.guild.get_channel(CANAL_FICHAS_PUBLICAS)
        if canal_publico is None:
            await interaction.response.send_message(
                "❌ No encontré el canal de fichas. Avisa a un admin.", ephemeral=True
            )
            return

        # Embed de la ficha
        embed = discord.Embed(
            title=f"🏀 Ficha de Jugador — {self.nombre.value}",
            color=0xF97316,
        )
        embed.add_field(name="👤 Jugador",            value=interaction.user.mention, inline=True)
        embed.add_field(name="📍 Posición",           value=self.posicion.value,      inline=True)
        embed.add_field(name="📊 Stats por partido",  value=self.stats.value,         inline=False)
        embed.add_field(
            name="🏆 Equipos anteriores",
            value=self.equipos.value if self.equipos.value else "—",
            inline=False,
        )
        embed.add_field(
            name="💬 Frase de cancha",
            value=f'*"{self.frase.value}"*' if self.frase.value else "—",
            inline=False,
        )
        embed.set_footer(text="Solo los que se presentan, juegan. 🏀")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # Botón para contactar al jugador
        view = ContactarView(jugador=interaction.user)
        msg = await canal_publico.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"✅ ¡Tu ficha fue publicada en {canal_publico.mention}!", ephemeral=True
        )


# ══════════════════════════════════════════════════════════════
#  BOTÓN — Contactar jugador (abre canal privado)
# ══════════════════════════════════════════════════════════════
class ContactarView(discord.ui.View):
    def __init__(self, jugador: discord.Member):
        super().__init__(timeout=None)
        self.jugador = jugador

    @discord.ui.button(label="📩 Contactar jugador", style=discord.ButtonStyle.blurple)
    async def contactar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild    = interaction.guild
        categoria = guild.get_channel(CATEGORIA_PRIVADA)

        if categoria is None:
            await interaction.response.send_message(
                "❌ No encontré la categoría privada. Avisa a un admin.", ephemeral=True
            )
            return

        # Permisos: solo el DT que hace clic + el jugador
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user:   discord.PermissionOverwrite(view_channel=True, send_messages=True),
            self.jugador:       discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        canal_privado = await guild.create_text_channel(
            name=f"fichaje-{self.jugador.display_name}",
            category=categoria,
            overwrites=overwrites,
        )

        await canal_privado.send(
            f"👋 {interaction.user.mention} quiere hablar contigo, {self.jugador.mention}!\n\n"
            f"🏀 Este es tu canal privado de fichaje. ¡Buena suerte!"
        )

        await interaction.response.send_message(
            f"✅ Canal privado creado: {canal_privado.mention}", ephemeral=True
        )


# ══════════════════════════════════════════════════════════════
#  BOTÓN — Crear ficha (abre el modal)
# ══════════════════════════════════════════════════════════════
class CrearFichaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🏀 Crear mi ficha",
        style=discord.ButtonStyle.green,
        custom_id="crear_ficha_btn",
    )
    async def crear_ficha(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FichaModal())


# ══════════════════════════════════════════════════════════════
#  EVENTO — Bot listo
# ══════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    # Registra la view persistente para que sobreviva reinicios
    bot.add_view(CrearFichaView())
    await tree.sync()
    print(f"✅ Bot conectado como {bot.user}")

    # Envía el mensaje con el botón al canal #crear-ficha si no existe ya
    canal = bot.get_channel(CANAL_CREAR_FICHA)
    if canal:
        # Revisa si ya hay un mensaje del bot
        async for msg in canal.history(limit=10):
            if msg.author == bot.user:
                return  # Ya existe, no lo duplica

        embed = discord.Embed(
            title="🏀 ¡Crea tu ficha de jugador!",
            description=(
                "¿Listo para que todos sepan tu nivel? 👀\n\n"
                "Haz clic en el botón y completa tu carta.\n"
                "Se publicará en el canal de fichajes para que los DT puedan verte."
            ),
            color=0xF97316,
        )
        embed.set_footer(text="Solo los que se presentan, juegan. 🏀")
        await canal.send(embed=embed, view=CrearFichaView())


bot.run(TOKEN)
