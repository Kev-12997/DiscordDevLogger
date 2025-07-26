import discord
from discord.ext import commands
import os
import asyncio

TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX')

# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True  # Required for message content access
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

async def load_extensions():
    '''
    Loads all bot extensions from the cogs folder.
    
    The "load_extension" function automatically looks for the "setup" function in each extension.
    An extension is just a python file/module with a set of commands or events for the bot. 
    The classes in theses extensions are called "cogs".
    '''
    try:
        await bot.load_extension('cogs.events')
        await bot.load_extension('cogs.commands')
        print("All extensions loaded successfully!")
    except Exception as error:
        print(f"Failed to load extension: {error}")

async def main():
    '''
    Main function to start the bot
    '''
    if not TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set!")
        return
    
    # Load extensions before starting the bot
    await load_extensions()
    
    # Start the bot
    await bot.start(TOKEN)

if __name__ == "__main__":
    '''
    Creates an async context in main that allows the use of async operations 
    like await (needed to load extensions, for example)
    '''
    asyncio.run(main())