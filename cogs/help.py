import discord
from discord.ext import commands

class CustomHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.original_help = bot.help_command
        bot.help_command = None

    def cog_unload(self):
        self.bot.help_command = self.original_help

    @commands.command(name="help", aliases=["h", "cmds"])
    async def custom_help(self, ctx):
        """Displays the Heavenly Court system directory"""
        
        embed = discord.Embed(
            title="✦ Heavenly Court",
            description="Contribution system and utility commands",
            color=0x6B1614
        )

        members_text = (
            "` ,points ` — check your points\n"
            "` ,points @user ` — check someone's points\n"
            "` ,leaderboard ` — top 10 members"
        )
        embed.add_field(name="👤 Members", value=members_text, inline=False)

        staff_text = (
            "` ,points add @user amount ` — give points\n"
            "` ,points remove @user amount ` — remove points\n"
            "` ,points set @user amount ` — set exact points\n"
            "` ,points reset @user ` — wipe to zero\n"
            "` ,clan add @user ` — add to kwork whitelist\n"
            "` ,clan remove @user ` — remove from whitelist\n"
            "` ,clan list ` — view whitelist"
        )
        embed.add_field(name="⚙️ Staff", value=staff_text, inline=False)

        lent_text = (
            "` ,lent ` or ` ,lentlist ` — view your lent cards ledger\n"
            "` ,lent add @user ` — track a card you lent out (run `kci` when prompted)\n"
            "` ,lent remove ` — open a menu to easily remove returned cards"
        )
        embed.add_field(name="📦 Lent Tracker", value=lent_text, inline=False)

        effort_text = (
            "*( Works automatically — no command needed )*\n"
            "Drop a Karuta `kwi` (Worker Details) embed in chat, and Fang Yuan will automatically calculate the exact cosmetics needed to maximize its effort.\n"
            "> 💡 **Tip:** *Run `kci` right before `kwi` for the most accurate Mint projections!*"
        )
        embed.add_field(name="📊 Effort Calculator", value=effort_text, inline=False)

        embed.set_footer(text="Heavenly Court ✦ system directory")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CustomHelp(bot))