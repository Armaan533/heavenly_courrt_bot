import discord
from discord import app_commands
from discord.ext import commands
from frame_prices import FRAME_DB

async def frame_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=n.title()[:100], value=n[:100]) for n in FRAME_DB if current.lower() in n.lower()][:25]

class FrameCategorySelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        categories = sorted(list(set(data.get("type", "Unknown") for data in FRAME_DB.values())))
        options = [discord.SelectOption(label=cat, value=cat, emoji="🗂️") for cat in categories]
        super().__init__(placeholder="Select a frame category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        frames = sorted([name for name, data in FRAME_DB.items() if data.get("type") == category])
        view = FramePaginationView(self.bot, category, frames)
        embed = discord.Embed(title=f"📁 [ {category.upper()} CATALOG ]", description=f"Browsing **{category}** frames.", color=0x6b1614)
        await interaction.response.edit_message(embed=embed, view=view)

class FramePaginationView(discord.ui.View):
    def __init__(self, bot, category, frames):
        super().__init__(timeout=180)
        self.bot, self.category, self.frames = bot, category, frames
        self.per_page, self.current_page = 24, 0
        self.build_pagination()

    def build_pagination(self):
        self.clear_items()
        start, end = self.current_page * self.per_page, (self.current_page + 1) * self.per_page
        chunk = self.frames[start:end]
        self.add_item(FrameItemSelect(self.bot, f"{self.category} (Page {self.current_page + 1})", chunk, self.category))
        if self.current_page > 0: self.add_item(FramePageButton("◀️ Prev", "prev"))
        self.add_item(BackButton(self.bot, "categories"))
        if end < len(self.frames): self.add_item(FramePageButton("Next ▶️", "next"))

class FrameItemSelect(discord.ui.Select):
    def __init__(self, bot, placeholder, frame_list, category):
        self.bot, self.category = bot, category
        options = [discord.SelectOption(label=name.title()[:100], value=name[:100], emoji="🖼️") for name in frame_list]
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        frame_name = self.values[0]
        data = FRAME_DB[frame_name]
        embed = discord.Embed(title=f"Preview: {frame_name.title()}", color=0x6b1614)
        embed.add_field(name="Category", value=f"`{data.get('type')}`", inline=False)
        embed.add_field(name="Market Value", value=f"**{data.get('market', 0)}** 🎟️", inline=True)
        embed.add_field(name="Liquid Cost", value=f"**{data.get('liquid cost', 0)}** 🎟️", inline=True)
        if data.get("image"): embed.set_image(url=data["image"])
        await interaction.response.edit_message(embed=embed, view=discord.ui.View().add_item(BackButton(self.bot, "category_list", self.category)))


class FramesCog(commands.Cog):
    def __init__(self, bot): self.bot = bot
    
    frame_group = app_commands.Group(name="frame", description="Frame Utilities")

    @frame_group.command(name="menu")
    async def frame_menu(self, interaction: discord.Interaction):
        view = discord.ui.View().add_item(FrameCategorySelect(self.bot))
        await interaction.response.send_message("Welcome to the Vault.", embed=discord.Embed(title="[ HEAVENLY COURT VAULT ]", color=0x6b1614), view=view)

    @frame_group.command(name="lookup")
    @app_commands.autocomplete(frame_name=frame_autocomplete)
    async def frame_lookup(self, interaction: discord.Interaction, frame_name: str):
        if frame_name not in FRAME_DB: return await interaction.response.send_message("❌ Not found.", ephemeral=True)
        data = FRAME_DB[frame_name]
        embed = discord.Embed(title=f"🔍 {frame_name.title()}", color=0x6b1614)
        embed.add_field(name="Category", value=data.get("type"), inline=False)
        embed.add_field(name="Market Value", value=data.get("market", 0), inline=True)
        embed.add_field(name="Liquid Cost", value=data.get("liquid cost", 0), inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot): await bot.add_cog(FramesCog(bot))