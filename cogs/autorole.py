import discord
from discord.ext import commands

class AutoRoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.autorole_id = 1503778569300607097

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        role = member.guild.get_role(self.autorole_id)
        
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                print(f"❌ Missing permissions to give the autorole to {member.display_name}. Check role hierarchy!")
            except Exception as e:
                print(f"❌ Error giving autorole: {e}")

async def setup(bot):
    await bot.add_cog(AutoRoleCog(bot))