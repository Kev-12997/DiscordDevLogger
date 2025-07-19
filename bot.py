import discord
from discord.ext import commands
import os
import asyncio

# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True  # Required for message content access
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

@bot.event
async def on_message(message):
    # Don't respond to ourselves
    if message.author == bot.user:
        return
    
    # Process commands
    await bot.process_commands(message)

@bot.command(name='hello')
async def hello(ctx):
    """Say hello to the bot"""
    await ctx.send(f'Hello {ctx.author.mention}!')

@bot.command(name='ping')
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f'Pong! Latency: {latency}ms')

@bot.command(name='info')
async def info(ctx):
    """Get bot information"""
    embed = discord.Embed(
        title="Bot Information",
        description="A simple Discord bot running in Docker",
        color=0x00ff00
    )
    embed.add_field(name="Guilds", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found! Use `!help` to see available commands.")
    else:
        print(f"Error: {error}")

# Get token from environment variable
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("Error: DISCORD_TOKEN environment variable not set!")
    exit(1)

if __name__ == "__main__":
    bot.run(TOKEN)