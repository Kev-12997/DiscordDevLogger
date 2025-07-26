import discord
from discord.ext import commands

class Events(commands.Cog):
    '''
    Cog containing events to listen too.
    '''
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        '''
        Runs when the bot is initially online. "on_ready" Is a default function 
        name that discord.py recognizes and that it should run when the bot is ready.
        '''
        print(f'{self.bot.user} has connected to Discord!')
        print(f'Bot is in {len(self.bot.guilds)} guilds')
        
    @commands.Cog.listener()
    async def on_command_error(self, context, error):
        '''
        "on_command_error" is a default function that will run if another command caused an error.
        '''
        if isinstance(error, commands.CommandNotFound):
            await context.send("Command not found! Use `!help` to see available commands.")
        else:
            print(f"Error: {error}")
            
async def setup(bot):
    '''
    Adds the Cog from this extension to the bot. 
    '''
    await bot.add_cog(Events(bot))