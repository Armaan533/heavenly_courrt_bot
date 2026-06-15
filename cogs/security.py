import discord
from discord.ext import commands

class SecurityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_guild_id = 1473256666131726417

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if guild.id != self.allowed_guild_id:
            print(f"🚨 Unauthorized join detected: {guild.name} ({guild.id}). Leaving immediately.")
            
            try:
                await guild.leave()
            except Exception as e:
                print(f"❌ Error trying to leave unauthorized guild: {e}")

async def setup(bot):
    await bot.add_cog(SecurityCog(bot))