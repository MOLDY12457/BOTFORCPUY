import discord
from discord.ext import commands
import json
import os
import asyncio
import random
import yt_dlp
from dotenv import load_dotenv
from keep_alive import keep_alive
import logging

# Configurer les logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    logger.error("DISCORD_TOKEN non trouvé dans les variables d'environnement")
    exit(1)

# Intents ultra-minimaux pour réduire la charge
intents = discord.Intents.default()
intents.message_content = True
intents.members = False  # Désactiver si non nécessaire
intents.voice_states = True
intents.presences = False
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Supprime la commande help par défaut
bot.remove_command('help')

# Fichiers de stockage
DATA_FILE = 'data.json'

# Charger données avec gestion d'erreur
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        logger.info("Nouveau fichier data.json créé")
        return {'xp': {}, 'levels': {}, 'custom_cmds': {}, 'banned_words': [], 'url': 'https://example.com'}
    except Exception as e:
        logger.error(f"Erreur lors du chargement de {DATA_FILE}: {e}")
        return {'xp': {}, 'levels': {}, 'custom_cmds': {}, 'banned_words': [], 'url': 'https://example.com'}

data = load_data()

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        logger.info("Données enregistrées dans data.json")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de {DATA_FILE}: {e}")

# Event: Bot ready
@bot.event
async def on_ready():
    logger.info(f'{bot.user} est connecté !')
    await bot.change_presence(activity=discord.Game(name="!help pour les commandes"))
    logger.info(f"Commandes enregistrées : {[cmd.name for cmd in bot.commands]}")
    logger.info(f"Commandes personnalisées chargées : {list(data['custom_cmds'].keys())}")

# !help custom
@bot.command(name='help')
async def help_cmd(ctx):
    logger.info("Commande !help exécutée")
    embed = discord.Embed(title="Commandes du Bot", color=0x00ff00)
    embed.add_field(name="Générales", value="!url\n!help", inline=False)
    embed.add_field(name="Modération (Mods seulement)", value="!kick @user [raison]\n!ban @user [raison]\n!mute @user\n!unmute @user\n!clear <nombre>\n!addbanned <mot>", inline=False)
    embed.add_field(name="Custom", value="!addcmd <nom> <réponse>\n!<nom> (exécute la custom)", inline=False)
    embed.add_field(name="Musique", value="!play <URL YouTube>\n!pause\n!stop\n!skip", inline=False)
    embed.add_field(name="Admin Modo", value="!changeurl <nouvelle URL>", inline=False)
    await ctx.send(embed=embed)

# !url
@bot.command(name='url')
async def show_url(ctx):
    logger.info("Commande !url exécutée")
    await ctx.send(f"L'URL actuelle : {data['url']}")

# !changeurl (mods seulement, ajoute https:// si nécessaire)
@bot.command(name='changeurl')
@commands.has_permissions(manage_messages=True)
async def change_url(ctx, *, new_url):
    logger.info("Commande !changeurl exécutée")
    if not new_url.startswith(('http://', 'https://')):
        new_url = 'https://' + new_url
    data['url'] = new_url
    save_data()
    await ctx.send(f"URL changée en : {new_url}")

# Modération
@bot.command(name='kick')
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    logger.info("Commande !kick exécutée")
    try:
        await member.kick(reason=reason)
        await ctx.send(f"{member} kické pour : {reason or 'Aucune raison'}")
    except Exception as e:
        await ctx.send(f"Erreur lors du kick : {str(e)}")

@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    logger.info("Commande !ban exécutée")
    try:
        await member.ban(reason=reason)
        await ctx.send(f"{member} banni pour : {reason or 'Aucune raison'}")
    except Exception as e:
        await ctx.send(f"Erreur lors du ban : {str(e)}")

@bot.command(name='mute')
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):
    logger.info("Commande !mute exécutée")
    try:
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False)
        await member.add_roles(mute_role)
        await ctx.send(f"{member} muté.")
    except Exception as e:
        await ctx.send(f"Erreur lors du mute : {str(e)}")

@bot.command(name='unmute')
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    logger.info("Commande !unmute exécutée")
    try:
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if mute_role:
            await member.remove_roles(mute_role)
            await ctx.send(f"{member} démuté.")
        else:
            await ctx.send("Rôle Muted non trouvé.")
    except Exception as e:
        await ctx.send(f"Erreur lors du unmute : {str(e)}")

@bot.command(name='clear')
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    logger.info("Commande !clear exécutée")
    try:
        if amount > 100:
            await ctx.send("Maximum 100 messages à la fois.")
            return
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"{amount} messages supprimés.", delete_after=5)
    except Exception as e:
        await ctx.send(f"Erreur lors du clear : {str(e)}")

@bot.command(name='addbanned')
@commands.has_permissions(manage_messages=True)
async def add_banned(ctx, *, word):
    logger.info("Commande !addbanned exécutée")
    try:
        if word not in data['banned_words']:
            data['banned_words'].append(word.lower())
            save_data()
            await ctx.send(f"Mot '{word}' ajouté à la liste interdite.")
    except Exception as e:
        await ctx.send(f"Erreur lors de l'ajout du mot : {str(e)}")

# Commandes custom
@bot.command(name='addcmd')
@commands.has_permissions(manage_messages=True)
async def add_custom(ctx, name: str, *, response):
    logger.info(f"Commande !addcmd exécutée pour ajouter '!{name}' avec réponse : {response}")
    try:
        if name.lower() in [cmd.name for cmd in bot.commands]:
            await ctx.send(f"Erreur : Une commande nommée '!{name}' existe déjà.")
            return
        data['custom_cmds'][name.lower()] = response
        save_data()
        await ctx.send(f"Commande !{name} ajoutée.")
        logger.info(f"Commandes personnalisées après ajout : {list(data['custom_cmds'].keys())}")
    except Exception as e:
        await ctx.send(f"Erreur lors de l'ajout de la commande : {str(e)}")

# Gestion des erreurs et commandes personnalisées
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        cmd_name = ctx.invoked_with.lower()
        logger.info(f"Commande non trouvée : {cmd_name}, vérification des commandes personnalisées...")
        if cmd_name in data['custom_cmds']:
            logger.info(f"Commande personnalisée trouvée : {cmd_name}")
            await ctx.send(data['custom_cmds'][cmd_name])
        else:
            await ctx.send(f"Commande '{cmd_name}' non trouvée. Tapez !help pour la liste des commandes.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("Vous n'avez pas les permissions pour cette commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Argument manquant. Vérifiez !help.")
    else:
        await ctx.send(f"Erreur inattendue : {str(error)}")
        logger.error(f"Erreur inattendue dans on_command_error : {str(error)}")

# Musique avec gestion robuste des erreurs
@bot.command(name='play')
async def play(ctx, url: str):
    logger.info(f"Commande !play exécutée avec URL : {url}")
    if not ctx.author.voice:
        await ctx.send("Rejoins un salon vocal d'abord !")
        return

    channel = ctx.author.voice.channel
    permissions = channel.permissions_for(ctx.guild.me)
    if not permissions.connect or not permissions.speak:
        await ctx.send("Je n'ai pas les permissions pour rejoindre ou parler dans ce salon vocal.")
        return

    if ctx.guild.voice_client:
        logger.info("Déconnexion du salon vocal existant")
        await ctx.guild.voice_client.disconnect(force=True)

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            logger.info(f"Tentative de connexion vocale {attempt + 1}/{max_attempts}")
            voice_client = await channel.connect(timeout=20.0, reconnect=True)
            break
        except (asyncio.TimeoutError, Exception) as e:
            logger.error(f"Erreur de connexion vocale (tentative {attempt + 1}): {str(e)}")
            if attempt == max_attempts - 1:
                await ctx.send(f"Échec de la connexion au salon vocal après {max_attempts} tentatives : {str(e)}")
                return
            await asyncio.sleep(3)  # Délai plus long entre tentatives

    # Options yt-dlp avec fallback et timeout
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'socket_timeout': 10,
        'ignoreerrors': True,
        'retry_max': 3,
        'sleep_interval': 5,
        'max_sleep_interval': 10,
    }

    try:
        logger.info("Extraction de l'URL YouTube...")
        async with asyncio.timeout(30):  # Timeout de 30s pour l'extraction
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    await ctx.send("Échec de l'extraction de la vidéo. Essayez une autre URL.")
                    await voice_client.disconnect()
                    return
                if 'entries' in info:
                    info = info['entries'][0]
                audio_url = info.get('url')
                title = info.get('title', 'Inconnu')
                await ctx.send(f"Lecture en cours : **{title}**")
                ffmpeg_path = "ffmpeg"  # Render a FFmpeg dans /usr/bin
                source = discord.FFmpegPCMAudio(
                    audio_url,
                    executable=ffmpeg_path,
                    options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
                )
                voice_client.play(source)
    except asyncio.TimeoutError:
        logger.error("Timeout lors de l'extraction YouTube")
        await ctx.send("Délai d'extraction dépassé. Essayez une autre URL ou réessayez plus tard.")
        await voice_client.disconnect()
        return
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction ou lecture YouTube : {str(e)}")
        await ctx.send(f"Erreur lors de la lecture de la vidéo : {str(e)}")
        await voice_client.disconnect()
        return

    while voice_client.is_playing():
        await asyncio.sleep(1)
    logger.info("Lecture terminée, déconnexion du salon vocal")
    await voice_client.disconnect()

@bot.command(name='pause')
async def pause(ctx):
    logger.info("Commande !pause exécutée")
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.pause()
        await ctx.send("Musique en pause.")
    else:
        await ctx.send("Aucune musique en cours.")

@bot.command(name='stop')
async def stop(ctx):
    logger.info("Commande !stop exécutée")
    if ctx.guild.voice_client:
        ctx.guild.voice_client.stop()
        await ctx.guild.voice_client.disconnect(force=True)
        await ctx.send("Musique arrêtée et déconnexion.")
    else:
        await ctx.send("Pas connecté à un salon vocal.")

@bot.command(name='skip')
async def skip(ctx):
    logger.info("Commande !skip exécutée")
    if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.stop()
        await ctx.send("Musique passée.")
    else:
        await ctx.send("Aucune musique à passer.")

# Lancer le keep-alive pour 24/7
keep_alive()

# Lance le bot
bot.run(TOKEN)
