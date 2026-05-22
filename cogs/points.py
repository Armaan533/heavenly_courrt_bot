from discord.ext import commands
import discord
from main import log

from constants import *
from utils.database import add_points, get_points, remove_points, set_points, get_leaderboard


async def setup(bot: commands.Bot):
    await bot.add_cog(Points(bot))

class Points(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="points", invoke_without_command=True)
    @commands.guild_only()
    async def points_cmd(self, ctx: commands.Context, member: discord.Member | None = None):
        target = member or ctx.author
        pts = await get_points(target.id)
        embed = discord.Embed(title="✦ Contribution Points", color=EMBED_COLOR)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name=target.display_name, value=f"**{pts}** points")
        await ctx.send(embed=embed)

    @points_cmd.command(name="reset", help="Reset a member's points to 0")
    @commands.has_permissions(administrator=True)
    async def points_reset(self, ctx: commands.Context, member: discord.Member):
        await set_points(member.id, 0)
        await ctx.send(embed=discord.Embed(
            description=f"✦ Reset {member.mention}'s points to 0.",
            color=EMBED_COLOR
        ))


    @points_cmd.command(name="set", help="Set a member's points to a specific value")
    @commands.has_permissions(administrator=True)
    async def points_set(self, ctx: commands.Context, member: discord.Member, points: int):
        await set_points(member.id, points)
        await ctx.send(embed=discord.Embed(
            description=f"✦ Set {member.mention}'s points to {points}.",
            color=EMBED_COLOR
        ))
        

    @points_cmd.command(name="add", help="Add a specific number of points to a member")
    @commands.has_permissions(administrator=True)
    async def points_add(self, ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        await add_points(member.id, amount)
        total = await get_points(member.id)
        await ctx.send(embed=discord.Embed(
            description=f"✦ Gave **{amount}** points to {member.mention}. Total: **{total}**",
            color=EMBED_COLOR
        ))
        await log(ctx.guild, f"➕ `+{amount}` → {member} | by {ctx.author} | total: {total}")


    @points_cmd.command(name="remove", help="Remove a specific number of points from a member", aliases=["rm"])
    @commands.has_permissions(administrator=True)
    async def points_remove(self, ctx: commands.Context, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        try:
            new_total = await remove_points(member.id, amount)
            await ctx.send(embed=discord.Embed(
                description=f"✦ Removed **{amount}** points from {member.mention}. Total: **{new_total}**",
                color=EMBED_COLOR
            ))
            await log(ctx.guild, f"➖ `-{amount}` → {member} | by {ctx.author} | total: {new_total}")
        except ValueError:
            return await ctx.send("Member does not have enough points.")


    @commands.command(name="leaderboard", help="Show the top 10 members with the most points", aliases=["lb", "top"])
    @commands.guild_only()
    async def leaderboard_cmd(self, ctx: commands.Context):
        rows = await get_leaderboard(10)
        embed = discord.Embed(title="✦ Contribution Leaderboard", color=EMBED_COLOR)
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        if not rows:
            embed.description = "No points recorded yet."
        else:
            lines = []
            for i, (user_id, points) in enumerate(rows):
                try:
                    user = await self.bot.fetch_user(user_id)
                    name = user.display_name
                except Exception:
                    name = f"Unknown ({user_id})"
                prefix = medals.get(i, f"**{i+1}.**")
                lines.append(f"{prefix} {name} — **{points}** pts")
            embed.description = "\n".join(lines)
        await ctx.send(embed=embed)