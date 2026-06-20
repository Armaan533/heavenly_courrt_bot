import discord
from discord import app_commands
from discord.ext import commands
from frame_prices import FRAME_DB

async def frame_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Filters the frame database dynamically as the user types."""
    matches = [frame_name for frame_name in FRAME_DB.keys() if current.lower() in frame_name.lower()]
    
    return [
        app_commands.Choice(name=match.title()[:100], value=match[:100])
        for match in matches[:25]
    ]
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
        
        embed = discord.Embed(
            title=f"<:two_flowers:1516684386546880614> [ {category.upper()} CATALOG ]",
            description=f"Browse our complete collection of **{category}** frames below.",
            color=0x6b1614
        )
        await interaction.response.edit_message(embed=embed, view=view)

class FramePaginationView(discord.ui.View):
    def __init__(self, bot, category, frames):
        super().__init__(timeout=180)
        self.bot = bot
        self.category = category
        self.frames = frames
        self.per_page = 24
        self.current_page = 0
        self.build_pagination()

    def build_pagination(self):
        self.clear_items()
        
        start_idx = self.current_page * self.per_page
        end_idx = start_idx + self.per_page
        current_chunk = self.frames[start_idx:end_idx]
        total_pages = ((len(self.frames) - 1) // self.per_page) + 1
        
        placeholder = f"{self.category} (Page {self.current_page + 1}/{total_pages})"
        self.add_item(FrameItemSelect(self.bot, placeholder, current_chunk, self.category))
        
        if self.current_page > 0:
            self.add_item(FramePageButton(label="◀️ Prev", action="prev"))
            
        self.add_item(BackButton(self.bot, target="categories"))
        
        if end_idx < len(self.frames):
            self.add_item(FramePageButton(label="Next ▶️", action="next"))

class FramePageButton(discord.ui.Button):
    def __init__(self, label, action):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        view: FramePaginationView = self.view
        if self.action == "prev":
            view.current_page -= 1
        elif self.action == "next":
            view.current_page += 1
            
        view.build_pagination()
        
        embed = discord.Embed(
            title=f"<:two_flowers:1516684386546880614> [ {view.category.upper()} CATALOG ]",
            description=f"Browse our complete collection of **{view.category}** frames below.",
            color=0x6b1614
        )
        await interaction.response.edit_message(embed=embed, view=view)

class FrameItemSelect(discord.ui.Select):
    def __init__(self, bot, placeholder, frame_list, category):
        self.bot = bot
        self.category = category
        options = [
            discord.SelectOption(label=name.title()[:100], value=name[:100], emoji="🖼️") 
            for name in frame_list
        ]
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        frame_name = self.values[0]
        data = FRAME_DB[frame_name]
        
        market_price = data.get("market", 0)
        liquid_price = data.get("liquid cost", 0)
        frame_type = data.get("type", "Unknown")
        image_url = data.get("image", None)
        
        embed = discord.Embed(
            title=f"<:two_flowers:1516684386546880614> Preview: {frame_name.title()}",
            color=0x6b1614
        )
        embed.add_field(name="<:book_ig:1516683126066253844> Category", value=f"`{frame_type}`", inline=False)
        
        if market_price == 0 and liquid_price == 0:
            embed.add_field(
                name="💰 Pricing Estimate", 
                value="*⚠️ Pricing fluctuates heavily. Insufficient market data available.*", 
                inline=False
            )
        else:
            embed.add_field(name="<:eight_side_sparkle:1516681364806570105> Market Value", value=f"**{market_price}** 🎟️", inline=True)
            if liquid_price >= 25 and frame_type.lower() != "bits":
                embed.add_field(name="<:for_john:1517226175901208696> Liquid Cost", value=f"**{liquid_price}** 🎟️", inline=True)
                
        embed.set_footer(text="Estimates based on ledger logs. Verify before finalizing trades.")
        
        if image_url:
            embed.set_image(url=image_url)

        view = discord.ui.View(timeout=180)
        view.add_item(BackButton(self.bot, target="category_list", current_category=self.category))
        
        await interaction.response.edit_message(embed=embed, view=view, attachments=[])

class BackButton(discord.ui.Button):
    def __init__(self, bot, target, current_category=None):
        self.bot = bot
        self.target = target
        self.current_category = current_category
        super().__init__(label="Go Back", style=discord.ButtonStyle.danger, emoji="🔙")

    async def callback(self, interaction: discord.Interaction):
        if self.target == "categories":
            view = discord.ui.View(timeout=180)
            view.add_item(FrameCategorySelect(self.bot))
            
            embed = discord.Embed(
                title="<:red_lotus:1516679367743377448> [ HEAVENLY COURT VAULT ]",
                description="Welcome to the Frame Showroom. Select a system index class below to access the database collections.",
                color=0x6b1614
            )
            await interaction.response.edit_message(embed=embed, view=view, attachments=[])
            
        elif self.target == "category_list":
            category = self.current_category
            frames = sorted([name for name, data in FRAME_DB.items() if data.get("type") == category])
            
            view = FramePaginationView(self.bot, category, frames)
            
            embed = discord.Embed(
                title=f"<:two_flowers:1516684386546880614> [ {category.upper()} CATALOG ]",
                description=f"Browse our complete collection of **{category}** frames below.",
                color=0x6b1614
            )
            await interaction.response.edit_message(embed=embed, view=view, attachments=[])

class FramesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    frame_group = app_commands.Group(name="frame", description="Heavenly Court Frame Utilities")

    @frame_group.command(name="menu", description="Open the interactive frame preview vault catalog")
    async def frame_menu(self, interaction: discord.Interaction):
        view = discord.ui.View(timeout=180)
        view.add_item(FrameCategorySelect(self.bot))
        
        embed = discord.Embed(
            title="<:red_lotus:1516679367743377448> [ HEAVENLY COURT VAULT ]",
            description="Welcome to the Frame Showroom. Select a system index class below to access the database collections.",
            color=0x6b1614
        )
        await interaction.response.send_message(embed=embed, view=view)

    @frame_group.command(name="lookup", description="Instantly search for a specific frame by name")
    @app_commands.autocomplete(frame_name=frame_autocomplete)
    async def frame_lookup(self, interaction: discord.Interaction, frame_name: str):
        if frame_name not in FRAME_DB:
            match = next((n for n in FRAME_DB if frame_name.lower() in n.lower()), None)
            if not match:
                return await interaction.response.send_message("❌ Frame not found in the database. Please select an option from the autocomplete list.", ephemeral=True)
            frame_name = match

        data = FRAME_DB[frame_name]
        market_price = data.get("market", 0)
        liquid_price = data.get("liquid cost", 0)
        frame_type = data.get("type", "Unknown")
        image_url = data.get("image", None)
        
        embed = discord.Embed(
            title=f"🔍 Search Result: {frame_name.title()}",
            color=0x6b1614
        )
        embed.add_field(name="<:book_ig:1516683126066253844> Category", value=f"`{frame_type}`", inline=False)
        
        if market_price == 0 and liquid_price == 0:
            embed.add_field(name="💰 Pricing Estimate", value="*⚠️ Pricing fluctuates heavily. Insufficient market data available.*", inline=False)
        else:
            embed.add_field(name="<:eight_side_sparkle:1516681364806570105> Market Value", value=f"**{market_price}** 🎟️", inline=True)
            if liquid_price >= 25 and frame_type.lower() != "bits":
                embed.add_field(name="<:for_john:1517226175901208696> Liquid Cost", value=f"**{liquid_price}** 🎟️", inline=True)
                
        embed.set_footer(text="Estimates based on ledger logs. Verify before finalizing trades.")
        
        if image_url:
            embed.set_image(url=image_url)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(FramesCog(bot))