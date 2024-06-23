import discord
from youtubesearchpython import VideosSearch
import os
import asyncio
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri='http://localhost:3000/'))


    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    queues = {}
    voice_clients = {}
    yt_dl_options = {"format": "bestaudio/best", "noplaylist": True, "lazy_playlist": True}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a "volume=0.25"'
    }
    
    async def search_spotify(query):
        results = sp.search(q="michael jackson", limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            return track['name'], track['external_urls']['spotify']
        else:
            return None

    async def leave_voice_channel(guild_id, message):
        if guild_id in voice_clients:
            if voice_clients[guild_id].is_playing():
                voice_clients[guild_id].stop()
            await message.channel.send(f"**Me he **desconectado** del canal de voz!")
            await voice_clients[guild_id].disconnect()
            del voice_clients[guild_id]

    async def monitor_inactivity(guild_id, message):
        await asyncio.sleep(300)  # 5 minutos
        if guild_id in voice_clients and not voice_clients[guild_id].is_playing():
            await leave_voice_channel(guild_id, message)

    async def play_spotify_song(guild_id, message, track_url, track_name):
        await message.channel.send("Lo siento, aún no aceptamos enlaces de Spotify.")

    @client.event
    async def on_ready():
        print(f'{client.user} está online')

        await client.change_presence(status=discord.Status.idle)
        custom_activity = discord.Activity(type=discord.ActivityType.listening, name="Eso Tilin")
        await client.change_presence(activity=custom_activity)

    @client.event
    async def on_message(message):
        if message.content.startswith('?clear'):
            try:
                amount = int(message.content.split()[1]) + 1
                deleted = await message.channel.purge(limit=amount)
                deleted_count = len(deleted) - 1
                count_message = await message.channel.send(f":white_check_mark: Se borraron {deleted_count} mensajes en total.")

                await asyncio.sleep(5)
                await count_message.delete()
            except Exception as e:
                await message.channel.send("Ocurrió un error al intentar borrar los mensajes.")
                print(e)

        if message.content.startswith("?search"):
            try:
                search_query = " ".join(message.content.split()[1:])
                videos = search_youtube(search_query)

                if videos:
                    for title, link in videos:
                        await message.channel.send(f"**{title}**\n{link}")
                else:
                    await message.channel.send("No se encontraron resultados para la búsqueda.")
            except Exception as e:
                print(e)
                await message.channel.send("Ocurrió un error al buscar la canción.")

        if message.content.startswith("?p"):
            try:
                if message.author.voice:
                    voice_client = await message.author.voice.channel.connect()
                    voice_clients[voice_client.guild.id] = voice_client
                else:
                    await message.channel.send("No estás en un canal de voz.")
                    return
            except Exception as e:
                print(e)

            try:
                query = " ".join(message.content.split()[1:])

                # Verificar si es una URL o una búsqueda
                if "youtube.com" in query or "youtu.be" in query:
                    url = query
                else:
                    # Si no es un enlace de YouTube, verificar si es un enlace de Spotify
                    if "open.spotify.com" in query:
                        track_id = query.split('/')[-1].split('?')[0]
                        track_info = sp.track(track_id)
                        track_name, track_url = await search_spotify(query)

                        await play_spotify_song(message.guild.id, message, track_url, track_name)  # Pasa el mensaje como argumento
                        return
                    else:
                        # Es una búsqueda de YouTube
                        query = query.replace(" ", "+")
                        search_results = search_youtube(query)
                        if search_results:
                            title, url = search_results[0]
                        else:
                            await message.channel.send("No se encontró ningún video en la búsqueda.")
                            return

                if url:
                    if 'list=' in url:
                        loop = asyncio.get_event_loop()
                        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

                        if 'entries' in data:
                            for entry in data['entries']:
                                if entry['url'] in url or entry['id'] in url:
                                    await message.channel.send(f"No puedo reproducir playlists. La canción solicitada es **{entry['title']}**.")
                                    return

                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

                    song = data['url']
                    title = data['title']

                    player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

                    if message.guild.id in queues:
                        if not voice_clients[message.guild.id].is_playing():
                            await play_next_song(message.guild.id, message.channel)
                        else:
                            queues[message.guild.id].append((player, title))
                            await message.channel.send(f"Se agregó **{title}** a la cola de reproducción.")
                    else:
                        queues[message.guild.id] = [(player, title)]
                        if not voice_clients[message.guild.id].is_playing():
                            await play_next_song(message.guild.id, message.channel)
                    
                    asyncio.create_task(monitor_inactivity(message.guild.id, message))

                else:
                    await message.channel.send("No se encontró ningún video en la búsqueda.")
            except Exception as e:
                print(e)

        if message.content.startswith("?pause"):
            try:
                voice_clients[message.guild.id].pause()
            except Exception as e:
                print(e)

        if message.content.startswith("?resume"):
            try:
                voice_clients[message.guild.id].resume()
            except Exception as e:
                print(e)

        if message.content.startswith("?stop"):
            try:
                voice_clients[message.guild.id].stop()
                await leave_voice_channel(message.guild.id)
            except Exception as e:
                print(e)

        if message.content.startswith("?q"):
            try:
                if message.guild.id in queues and queues[message.guild.id]:
                    queue_list = "\n".join([f"{index + 1}. {song[1]}" for index, song in enumerate(queues[message.guild.id])])
                    await message.channel.send(f"**Cola de reproducción:**\n{queue_list}")
                else:
                    await message.channel.send("No hay canciones en la cola.")
            except Exception as e:
                print(e)

        if message.content.startswith("?skip"):
            try:
                if message.guild.id in queues and queues[message.guild.id]:
                    # Detener la canción actual y pasar a la siguiente
                    voice_clients[message.guild.id].stop()
                else:
                    await message.channel.send("No hay canciones en la cola.")
            except Exception as e:
                print(e)

        if message.content.startswith("?remove"):
            try:
                index = int(message.content.split()[1]) - 1
                if message.guild.id in queues and 0 <= index < len(queues[message.guild.id]):
                    removed_song = queues[message.guild.id].pop(index)
                    await message.channel.send(f"Se ha eliminado la canción {removed_song[1]} de la cola.")
                else:
                    await message.channel.send("No existe una canción en esa posición.")
            except Exception as e:
                await message.channel.send("Por favor, proporciona un número válido de canción para eliminar.")

    async def play_next_song(guild_id, channel):
        if queues[guild_id]:
            song_info = queues[guild_id].pop(0)
            player = song_info[0]
            
            if "spotify" in song_info[1]:
                # Si es una canción de Spotify, reproducirla directamente
                await play_spotify_song(guild_id, channel, song_info[1])
            else:
                # Si no, reproducir la canción desde YouTube
                voice_clients[guild_id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(guild_id, channel), client.loop))
                await channel.send(f"Reproduciendo ahora: **{song_info[1]}**")

    def search_youtube(query):
        try:
            # Realizar la búsqueda de videos en YouTube
            videos_search = VideosSearch(query, limit=10)
            # Obtener los resultados de la búsqueda
            results = videos_search.result()
            # Crear una lista de tuplas con el título y el enlace de cada video
            videos = [(video['title'], video['link']) for video in results['result']]

            # Devolver solo el primer resultado si hay al menos uno
            if videos:
                return [(videos[0][0], videos[0][1])]
            else:
                print("No se encontraron resultados para la búsqueda.")
                return None
        except Exception as e:
            print(f'Error al realizar la búsqueda en YouTube: {e}')
            return None

    client.run(TOKEN)

run_bot()
