from concurrent.futures import process
import discord 
from discord.ext import commands
import yt_dlp
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot_token = os.environ.get("DISCORD_BOT_TOKEN")

bot = commands.Bot(command_prefix='!', intents=intents)

FFMPEG_OPTIONS = {
  'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
  'options': '-vn'
}

YDL_OPTIONS = {
  'format': 'bestaudio/best',
  'noplaylist': 'True',
  'cookiefile': 'cookies.txt'
}

guild_queues = {}

class Song:
  def __init__(self, url, title, stream_url):
    self.url = url
    self.title = title
    self.stream_url = stream_url

async def play_next(ctx, guild_id):
  queue = guild_queues.get(guild_id)
  if queue and len(queue) > 0:
    next_song = queue.pop(0)
    voice_client = ctx.guild.voice_client
    source = await discord.FFmpegOpusAudio.from_probe(next_song.stream_url, **FFMPEG_OPTIONS)

    def after_playing(err):
      if err:
        print(f'Error playing song: {err}')
      fut = asyncio.run_coroutine_threadsafe(play_next(ctx, guild_id), bot.loop)
      try:
        fut.result()
      except Exception as e:
        print(f'Error in after_playing: {e}')

    voice_client.play(source, after=after_playing)
    await ctx.send(f'Now playing: {next_song.title}')

  else:
    await ctx.send('Queue is empty.')
    await ctx.voice_client.disconnect()

@bot.event
async def on_ready():
  print(f'Logged in as {bot.user}')

@bot.command()
async def join(ctx):
  if ctx.author.voice:
    channel = ctx.author.voice.channel
    await channel.connect()
    await ctx.send(f'Joined {channel}')
  else:
    await ctx.send('You are not connected to a voice channel.')

@bot.command()
async def play(ctx, url):
  if not ctx.voice_client:
      await ctx.invoke(bot.get_command("join"))

  with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
      info = ydl.extract_info(url, download=False)
      stream_url = info['url']
      title = info['title']

  song = Song(url, title, stream_url)

  guild_id = ctx.guild.id
  if guild_id not in guild_queues:
      guild_queues[guild_id] = []

  queue = guild_queues[guild_id]

  if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
      queue.insert(0, song)
      await play_next(ctx, guild_id)
  else:
      queue.append(song)
      await ctx.send(f"Queued: {title}")

@bot.command()
async def skip(ctx):
  if ctx.voice_client and ctx.voice_client.is_playing():
      ctx.voice_client.stop()
      await ctx.send("Skipped the current song.")
  else:
      await ctx.send("No song is currently playing.")

@bot.command()
async def pause(ctx):
  if ctx.voice_client and ctx.voice_client.is_playing():
      ctx.voice_client.pause()
      await ctx.send("Paused the song.")
  else:
      await ctx.send("No song is currently playing.")

@bot.command()
async def resume(ctx):
  if ctx.voice_client and ctx.voice_client.is_paused():
      ctx.voice_client.resume()
      await ctx.send("Resumed the song.")
  else:
      await ctx.send("No song is paused.")

@bot.command()
async def queue(ctx):
  guild_id = ctx.guild.id
  queue = guild_queues.get(guild_id, [])
  if queue:
      message = "**Current Queue:**\n" + "\n".join(f"{idx + 1}. {song.title}" for idx, song in enumerate(queue))
      await ctx.send(message)
  else:
      await ctx.send("The queue is empty.")

@bot.command()
async def leave(ctx):
  if ctx.voice_client:
      guild_queues[ctx.guild.id] = []
      await ctx.voice_client.disconnect()
      await ctx.send("Disconnected from voice channel.")
  else:
      await ctx.send("I'm not in a voice channel.")

bot.run(str(bot_token))
