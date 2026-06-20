import discord
from discord import app_commands
from discord.ext import commands
from frame_prices import FRAME_DB

class FrameView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot
        self.add_item(FrameCategorySelect(bot))

class FrameCategorySelect(discord.ui.Select):
    def __init__(self, bot):
        categories = sorted(list(set(d.get("type", "Misc") for d in FRAME_DB.values())))
        options = [discord.SelectOption(label=c, value=c) for c in categories]
        super().__init__(placeholder="Select a Category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        cat = self.values[0]
        frames = [name for name, d in FRAME_DB.items() if d.get("type") == cat]
        view = discord.ui.View(timeout=180)
        view.add_item(FrameItemSelect(cat, frames))
        view.add_item(BackButton())
        await interaction.followup.edit_message(message_id=interaction.message.id, 
            embed=discord.Embed(title=f"📁 Viewing: {cat}", color=0x6b1614), view=view)

class FrameItemSelect(discord.ui.Select):
    def __init__(self, cat, frames):
        options = [discord.SelectOption(label=f[:25], value=f) for f in frames[:25]]
        super().__init__(placeholder="Choose a Frame...", options=options)
        self.cat = cat
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = FRAME_DB[self.values[0]]
        embed = discord.Embed(title=self.values[0].title(), color=0x6b1614)
        embed.add_field(name="Market Value", value=f"{data.get('market', 0)} 🎟️")
        embed.set_image(url=data.get('image'))
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=FrameView(self.bot))

class BackButton(discord.ui.Button):
    def __init__(self): super().__init__(label="Back", style=discord.ButtonStyle.danger)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.edit_message(message_id=interaction.message.id, 
            embed=discord.Embed(title="📁 Frame Vault", description="Select a category to begin.", color=0x6b1614), view=FrameView(self.bot))

class FramesCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="frame", description="Open the Frame Vault")
    async def frame(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="📁 Frame Vault", description="Select a category to begin.", color=0x6b1614), view=FrameView(self.bot))

    @app_commands.command(name="lookup", description="Search for a specific frame")
    async def lookup(self, interaction: discord.Interaction, name: str):
        match = next((n for n in FRAME_DB if name.lower() in n.lower()), None)
        if not match: return await interaction.response.send_message("Frame not found.", ephemeral=True)
        data = FRAME_DB[match]
        embed = discord.Embed(title=match.title(), color=0x6b1614)
        embed.set_image(url=data.get('image'))
        await interaction.response.send_message(embed=embed)

async def setup(bot): await bot.add_cog(FramesCog(bot))