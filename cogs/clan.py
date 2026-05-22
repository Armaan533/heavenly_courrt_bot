from discord.ext import commands
import discord

from constants import *
from utils.database import add_to_whitelist, remove_from_whitelist, get_whitelist, set_points



async def setup(bot: commands.Bot):
    await bot.add_cog(Clan(bot))



class Clan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @commands.group(name="clan", invoke_without_command=True)
    async def clan_cmd(self, ctx):
        pass

    @clan_cmd.command(name = "add", help = "Add a member to the clan")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def clan_add(self, ctx: commands.Context, member: discord.Member):
        try:
            await add_to_whitelist(member.id)
            if ctx.guild is None:
                return
            role = ctx.guild.get_role(CLAN_ROLE_ID)
            if role:
                await member.add_roles(role)
            await ctx.send(embed=discord.Embed(
                description=f"✦ {member.mention} added to clan whitelist.",
                color=EMBED_COLOR
            ))
        except ValueError:
            return await ctx.send(embed = discord.Embed(
                description=f"✦ {member.mention} is already whitelisted.",
                color=EMBED_COLOR
            ))
        
    @clan_cmd.command(name = "remove", help = "Remove a member from the clan", aliases=["rm", "kick"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def clan_remove(self, ctx: commands.Context, member: discord.Member):
        try:
            await remove_from_whitelist(member.id)
            if ctx.guild is None:
                return
            role = ctx.guild.get_role(CLAN_ROLE_ID)
            if role:
                await member.remove_roles(role)
            await ctx.send(embed=discord.Embed(
                description=f"✦ {member.mention} removed from clan whitelist.",
                color=EMBED_COLOR
            ))
        except ValueError:
            return await ctx.send(embed = discord.Embed(
                description=f"✦ {member.mention} is not whitelisted.",
                color=EMBED_COLOR
            ))
        
    @clan_cmd.command(name = "list", help = "List all whitelisted clan members")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def clan_list(self, ctx: commands.Context):
        whitelist = await get_whitelist()
        if not whitelist:
            return await ctx.send(embed=discord.Embed(
                description="✦ No members are currently whitelisted.",
                color=EMBED_COLOR
            ))
        
        member_mentions = []
        for user_id in whitelist:
            member = self.bot.get_user(user_id)
            if member:
                member_mentions.append(member.mention)
        
        description = "✦ Whitelisted Clan Members:\n" + "\n".join(member_mentions)
        await ctx.send(embed=discord.Embed(
            description=description,
            color=EMBED_COLOR
        ))
