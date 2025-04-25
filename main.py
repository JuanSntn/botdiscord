import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp as youtube_dl
import random
import asyncio
import time
from collections import deque
import lyricsgenius 
import re

# Carga variables de entorno
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

GENIUS_TOKEN = os.getenv('GENIUS_TOKEN')
genius = lyricsgenius.Genius(GENIUS_TOKEN)

# Configura el bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Configuración de la actividad del bot
INACTIVITY_TIMEOUT = 20  # 5 minutos en segundos
last_activity = {}


# Configuración de yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'opus',
        'preferredquality': '192',
    }],
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Clase para manejar la cola de reproducción
class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.now_playing = None

    def add(self, track):
        self.queue.append(track)

    def next(self):
        if self.queue:
            self.now_playing = self.queue.popleft()
            return self.now_playing
        return None

    def clear(self):
        self.queue.clear()
        self.now_playing = None

    def get_queue_list(self):
        return list(self.queue)

# Clase para manejar el audio
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.7):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(
            filename,
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            options='-vn'
        ), data=data)

# Diccionario para almacenar colas por servidor
queues = {}

def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = MusicQueue()
    return queues[guild_id]


# Función para verificar inactividad
async def check_inactivity(guild_id, vc, text_channel):
    while True:
        await asyncio.sleep(30)  # Verifica cada 30 segundos
        
        # Verificar condiciones de inactividad
        queue = get_queue(guild_id)
        current_time = time.time()
        
        if (current_time - last_activity.get(guild_id, current_time)) >= INACTIVITY_TIMEOUT:
            if vc.is_connected() and not vc.is_playing() and not queue.queue:
                if len(vc.channel.members) == 1:  # Solo el bot en el canal
                    try:
                        await text_channel.send("🔌 Desconectando por inactividad...")
                        queue.clear()
                        await vc.disconnect()
                        break  # Salir del bucle después de desconectar
                    except Exception as e:
                        print(f"Error al desconectar: {e}")
                        break

# Comando !play
@bot.command(name='play')
async def play(ctx, *, url):
    if not ctx.author.voice:
        return await ctx.send("❌ Debes estar en un canal de voz")

    try:
        # Conectar al canal de voz
        if ctx.voice_client is None:
            vc = await ctx.author.voice.channel.connect()
        else:
            vc = ctx.voice_client
            if vc.channel != ctx.author.voice.channel:
                await vc.move_to(ctx.author.voice.channel)

        queue = get_queue(ctx.guild.id)
        last_activity[ctx.guild.id] = time.time()

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            queue.add(player)
            
            # Si no hay nada reproduciéndose, empieza a reproducir
            if not vc.is_playing():
                await play_next(ctx)

        await ctx.send(f"🎵 Añadido a la cola: **{player.title}**")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

async def play_next(ctx):
    vc = ctx.voice_client
    queue = get_queue(ctx.guild.id)
    
    if not vc or vc.is_playing():
        return

    next_track = queue.next()
    last_activity[ctx.guild.id] = time.time()
    if next_track:
        vc.play(next_track, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f"🎵 Reproduciendo: **{next_track.title}**")
    else:
        await ctx.send("⏹ Cola vacía")
        await asyncio.sleep(240)  # Esperar 4 minutos
        await auto_disconnect(ctx.guild.id)

async def auto_disconnect(guild_id):
    vc = bot.get_guild(guild_id).voice_client
    if not vc:
        return
    
    queue = get_queue(guild_id)
    
    # Verificar condiciones para desconexión
    if not vc.is_playing() and not queue.queue:
        text_channel = vc.guild.system_channel or next((ch for ch in vc.guild.text_channels if ch.permissions_for(vc.guild.me).send_messages), None)
        if text_channel:
            await text_channel.send("🔌 Me desconecto porque no hay nada en la cola")
        await vc.disconnect()
        queue.clear()

# Comando !letra
@bot.command(name='letra')
async def lyrics(ctx):
    vc = ctx.voice_client
    if not vc or not vc.is_playing():
        return await ctx.send("❌ No hay música reproduciéndose actualmente")
    
    queue = get_queue(ctx.guild.id)
    if not queue.now_playing:
        return await ctx.send("❌ No hay información de la canción actual")
    
    try:
        await ctx.send(f"🔍 Buscando letra de: **{queue.now_playing.title}**...")
        
        # Limpieza mejorada del título
        clean_title = re.sub(r'\(.*?\)|\[.*?\]|Video Oficial|\|', '', queue.now_playing.title).strip()
        
        # Búsqueda con manejo de errores
        song = genius.search_song(clean_title, get_full_info=False)
        
        if song:
            # Formateo de la letra
            lyrics_text = song.lyrics.replace('Embed', '').strip()
            if len(lyrics_text) > 1500:
                lyrics_text = lyrics_text[:1500] + "...\n[Letra completa en Genius](" + song.url + ")"
            
            # Envío en embed
            embed = discord.Embed(
                title=f"🎤 {song.title}",
                description=lyrics_text,
                color=0x00ff00,
                url=song.url
            )
            await ctx.send(embed=embed)
        else:
            search_url = f"https://genius.com/search?q={clean_title.replace(' ', '%20')}"
            await ctx.send(f"❌ No encontré la letra. [Buscar manualmente]({search_url})")
            
    except Exception as e:
        print(f"Error al buscar letra: {e}")
        await ctx.send("⚠️ Error al conectar con Genius. Intenta más tarde.")


# Buscar letra !buscarletra
@bot.command(name='buscarletra')
async def search_lyrics(ctx, *, query):
    song = genius.search_song(query)
    if song:
        await ctx.send(f"🎤 {song.title}\n\n{song.lyrics[:2000]}...")
    else:
        await ctx.send(f"No encontré resultados. Prueba en: https://genius.com/search?q={query.replace(' ', '%20')}")

# Comando !skip
@bot.command(name='skip')
async def skip(ctx):
    vc = ctx.voice_client
    if not vc or not vc.is_playing():
        return await ctx.send("❌ No hay música reproduciéndose")
    
    last_activity[ctx.guild.id] = time.time()
    vc.stop()
    await ctx.send("⏭ Canción saltada")
    
    queue = get_queue(ctx.guild.id)
    if not queue.queue:  # Si no hay más canciones en la cola
        await ctx.send("⏹ No hay más canciones en la cola. Me desconectaré en 4 minutos si no se añade nada.")
        await asyncio.sleep(240)  # Esperar 4 minutos
        await auto_disconnect(ctx.guild.id)

# Comando !queue
@bot.command(name='cola')
async def show_queue(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue.queue and not queue.now_playing:
        return await ctx.send("❌ La cola está vacía")
    
    message = []
    if queue.now_playing:
        message.append(f"🔊 **Reproduciendo ahora:** {queue.now_playing.title}")
    
    if queue.queue:
        message.append("\n📜 **Cola de reproducción:**")
        for i, track in enumerate(queue.queue, 1):
            message.append(f"{i}. {track.title}")
    
    await ctx.send("\n".join(message))


# Comando !stop
@bot.command(name='stop')
async def stop(ctx):
    vc = ctx.voice_client
    if not vc:
        return await ctx.send("❌ No estoy conectado en un canal de voz")
    
    queue = get_queue(ctx.guild.id)
    queue.clear()
    vc.stop()
    await vc.disconnect()
    await ctx.send("⏹ Música detenida y cola limpiada")

# Comando !votar
@bot.command(name='votar')
async def votar(ctx):
    opciones = ['lol', 'overcooked']
    eleccion = random.choice(opciones)
    await ctx.send(f"🎲 La elección es: **{eleccion}**")


# Verificar inactividad al iniciar el bot
@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user:
        return
        
    guild_id = before.channel.guild.id if before.channel else after.channel.guild.id
    vc = bot.get_guild(guild_id).voice_client
    
    if vc and vc.channel:
        # Actualizar actividad siempre que haya cambios en el canal de voz
        last_activity[guild_id] = time.time()
        
        # Si el bot está solo, iniciar verificación de inactividad
        if len(vc.channel.members) == 1:
            text_channel = vc.guild.system_channel or next((ch for ch in vc.guild.text_channels if ch.permissions_for(vc.guild.me).send_messages), None)
            if text_channel:
                asyncio.create_task(check_inactivity(guild_id, vc, text_channel))


# Evento cuando el bot está listo
@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user.name}')

# Inicia el bot
bot.run(TOKEN)