import os
import discord
import asyncio
import urllib.request
import json
import youtube_dl
import aiohttp

from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KEY = os.getenv('KEY')

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='+', intents=intents)

@bot.command(name='suma')
async def sumar(ctx, num1, num2):
    response = int(num1) + int(num2)
    await ctx.send(response)

@bot.event
async def on_ready():
    print(f'{bot.user} se conectó a Discord')

@bot.command(name='borrar')
async def borrar_mensajes(ctx, cantidad: int):
    if cantidad <= 0:
        await ctx.send("Por favor, especifica un número válido de mensajes para borrar.")
        return
    
    await ctx.channel.purge(limit=cantidad + 1)
    mensaje_confirmacion = await ctx.send(f'Se han borrado {cantidad} mensajes.')
    
    await asyncio.sleep(5)
    await mensaje_confirmacion.delete()

@bot.command(name='subs')
async def subscriptores(ctx, username):
    try:
        data = urllib.request.urlopen("https://www.googleapis.com/youtube/v3/channels?part=statistics&forUsername=" + username + "&key=" + KEY).read()
        subs = json.loads(data)["items"][0]["statistics"]["subscriberCount"]
        response = username + " tiene " + "{:,d}".format(int(subs)) + " suscriptores!"
        await ctx.send(response)
    except Exception as e:
        await ctx.send(f"No se encontró el canal '{username}'.")
        print(e)

@bot.command(name='search')
async def buscar_cancion(ctx, *, nombre_cancion):
    try:
        # Realizar la búsqueda de la canción en YouTube
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=" + urllib.parse.quote(nombre_cancion) + "&key=" + KEY
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        
        results = data.get("items", [])
        
        if results:
            # Obtener el primer resultado de la búsqueda
            primer_resultado = results[0]
            video_id = primer_resultado["id"]["videoId"]
            titulo = primer_resultado["snippet"]["title"]
            
            # Enviar el enlace del video al canal de Discord
            await ctx.send(f"**{titulo}**\nhttps://www.youtube.com/watch?v={video_id}")
        else:
            await ctx.send("No se encontraron resultados para la canción.")
    except Exception as e:
        print(e)
        await ctx.send("Ocurrió un error al buscar la canción.")
        
@bot.command(name='leave')
async def detener(ctx):
    try:
        # Verificar si el bot está en un canal de voz en el servidor
        if ctx.voice_client is not None:
            # Detener la reproducción y salir del canal de voz
            await ctx.voice_client.disconnect()
            await ctx.send("Saliendo del canal de voz.")
        else:
            await ctx.send("No estoy un canal de voz.")
    except Exception as e:
        await ctx.send(f'Error inesperado: {e}')

@bot.command(name='p')
async def reproducir(ctx, *, query):
    try:
        # Verificar si el bot ya está en un canal de voz en el servidor
        if ctx.voice_client is not None:
            # Si ya está en un canal de voz, salir antes de unirse a otro
            await ctx.voice_client.disconnect()

        # Unirse al canal de voz del autor del mensaje
        # voice_channel = ctx.author.voice.channel
        # voice_client = await voice_channel.connect()

        # Construir la URL de la API de YouTube para obtener información del video
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=" + urllib.parse.quote(query) + "&key=" + KEY
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()

        if 'items' in data and data['items']:
            video_info = data['items'][0]['snippet']
            title = video_info['title']
            video_id = data['items'][0]['id']['videoId']
            audio_url = f"https://www.youtube.com/watch?v={video_id}"

            await ctx.send(f"**{title}**\n{audio_url}")

            # Reproducir el audio en el canal de voz
            voice_channel = ctx.author.voice.channel
            voice_client = await voice_channel.connect()
            voice_client.play(discord.FFmpegPCMAudio(audio_url))
        else:
            await ctx.send("No se encontró información para el video especificado.")
    except Exception as e:
        await ctx.send(f'Error al reproducir el video: {e}')
        
@bot.command(name='shutdown', hidden=True)
@commands.is_owner()  # Asegura que solo el propietario del bot pueda usar este comando
async def shutdown(ctx):
    await ctx.send("Apagando el bot...")
    await bot.close()

bot.run(TOKEN)