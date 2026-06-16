import discord
from discord.ext import commands

class CustomHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.original_help = bot.help_command
        bot.help_command = None

    def cog_unload(self):
        self.bot.help_command = self.original_help

    @commands.command(name="help", aliases=["h", "commands", "cmds"])
    async def custom_help(self, ctx):
        """Displays the Heavenly Court system directory"""
        
        ticks = chr(96) * 3
        
        desc = "⟡ **Accessing Heavenly Court terminal...**\n\n"
        desc += "Below is the directory of all active modules and commands currently loaded into the Fang Yuan node.\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"

        embed = discord.Embed(
            title="[ SYSTEM DIRECTORY & COMMANDS ]",
            description=desc,
            color=0x8b0000
        )

        lent_cmds = (
            "`> ,lent` or `,lentlist`\n"
            "Displays your personal, private ledger of cards you have lent out.\n\n"
            "`> ,lent add @user`\n"
            "Initializes the tracker. The bot will prompt you to run `kci` on the card, automatically extracting the code and saving the data.\n\n"
            "`> ,lent remove`\n"
            "Opens a secure dropdown menu to instantly clear returned cards from your ledger."
        )
        embed.add_field(name="📦 **Lent Ledger Module**", value=lent_cmds, inline=False)

        effort_cmds = (
            "*( Passive Module - No prefix command required )*\n\n"
            "Fang Yuan automatically intercepts any Karuta worker embed (`kwi`) dropped in the chat. It bypasses Karuta's visual data to calculate the exact True Mint Core, precise cosmetic stat deltas, and absolute S-Style scaling caps.\n\n"
            "> 💡 **Pro-Tip:** *Run `kci` right before running `kwi` to force the engine to calculate based on absolute True Mint values!*"
        )
        embed.add_field(name="📊 **Effort Telemetry Engine**", value=effort_cmds, inline=False)


        embed.set_footer(text="Node: Fang Yuan // Heavenly Court ✦")
        
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CustomHelp(bot))