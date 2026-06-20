import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw
import os
import sys

from frame_prices import FRAME_DB

BASE_CARD_PATH = os.path.join("assets", "base_card.jpg")

class FrameCategorySelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        categories = sorted(list(set(data.get("type", "Unknown") for data in FRAME_DB.values())))
        options = [discord.SelectOption(label=cat, value=cat, emoji="🗂️") for cat in categories]
        super().__init__(placeholder="Select a frame category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        frames = sorted([name for name, data in FRAME_DB.items() if data.get("type") == category])
        
        if len(frames) > 24:
            view = discord.ui.View(timeout=180)
            chunk_size = 24
            chunks = [frames[i:i + chunk_size] for i in range(0, len(frames), chunk_size)]
            for idx, chunk in enumerate(chunks):
                start_letter = chunk[0][0].upper()
                end_letter = chunk[-1][0].upper()
                label = f"{category} ({start_letter}-{end_letter})"
                view.add_item(FrameItemSelect(self.bot, label, chunk, category))
            view.add_item(BackButton(self.bot, target="categories"))
            
            embed = discord.Embed(
                title=f"<:two_flowers:1516684386546880614> [ {category.upper()} SUB-PANEL ]",
                description="This category is quite large! Please select a subset dropdown below.",
                color=0x6b1614
            )
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            view = discord.ui.View(timeout=180)
            view.add_item(FrameItemSelect(self.bot, f"Select a {category} Frame", frames, category))
            view.add_item(BackButton(self.bot, target="categories"))
            
            embed = discord.Embed(
                title=f"<:two_flowers:1516684386546880614> [ {category.upper()} CATALOG ]",
                description=f"Browse our complete collection of **{category}** frames below.",
                color=0x6b1614
            )
            await interaction.response.edit_message(embed=embed, view=view)

class FrameItemSelect(discord.ui.Select):
    def __init__(self, bot, placeholder, frame_list, category):
        self.bot = bot
        self.category = category
        options = [discord.SelectOption(label=n.title(), value=n, emoji="🖼️") for n in frame_list]
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        frame_name = self.values[0]
        data = FRAME_DB[frame_name]
        
        market_price = data.get("market", 0)
        liquid_price = data.get("liquid cost", 0)
        frame_type = data.get("type", "Unknown")
        image_url = data.get("image", None)
        
        embed = discord.Embed(color=0x6b1614)
        embed.set_author(name=f"Preview: {frame_name.title()}", icon_url="https://cdn.discordapp.com/emojis/1516684386546880614.png")
        
        desc = f"**<:book_ig:1516683126066253844> Category:** `{frame_type}`\n"
        if market_price == 0 and liquid_price == 0:
            desc += "**💰 Pricing Estimate:** *⚠️ Insufficient market data available.*\n"
        else:
            desc += f"**<:eight_side_sparkle:1516681364806570105> Market Value:** **{market_price}** 🎟️\n"
            if liquid_price >= 25 and frame_type.lower() != "bits":
                desc += f"**<:for_john:1517226175901208696> Liquid Cost:** **{liquid_price}** 🎟️\n"
        
        embed.description = desc
        embed.set_footer(text="Estimates based on ledger logs. Verify before finalizing trades.")
        
        file = None
        if image_url and os.path.exists(BASE_CARD_PATH):
            try:
                urls_to_try = [
                    image_url.replace(".jpg", ".png").replace(".webp", ".png"),
                    image_url
                ]
                
                frame_bytes = None
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
                
                async with aiohttp.ClientSession(headers=headers) as session:
                    for url in urls_to_try:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                frame_bytes = await resp.read()
                                break
                                
                if frame_bytes:
                    with Image.open(BASE_CARD_PATH).convert("RGBA") as base_img, Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:
                        fw, fh = frame_img.size
                        
                        try:
                            resample_filter = Image.Resampling.LANCZOS
                        except AttributeError:
                            resample_filter = Image.ANTIALIAS
                            
                        base_cropped = ImageOps.fit(base_img, (fw, fh), method=resample_filter)
                        
                        mask = Image.new("L", (fw, fh), 0)
                        draw_mask = ImageDraw.Draw(mask)
                        draw_mask.rounded_rectangle((0, 0, fw, fh), radius=22, fill=255)
                        base_cropped.putalpha(mask)
                        
                        plate_overlay = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
                        draw_plates = ImageDraw.Draw(plate_overlay)
                        draw_plates.rectangle((0, 0, fw, int(fh * 0.13)), fill=(0, 0, 0, 160))
                        draw_plates.rectangle((0, int(fh * 0.88), fw, fh), fill=(0, 0, 0, 160))
                        
                        base_composite = Image.alpha_composite(base_cropped, plate_overlay)
                        final_composite = Image.alpha_composite(base_composite, frame_img)
                        
                        output_buffer = BytesIO()
                        final_composite.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file = discord.File(fp=output_buffer, filename="preview.png")
                        embed.set_image(url="attachment://preview.png")
            except Exception as e:
                print(f"Frame Processing Error: {e}", file=sys.stderr)

        view = discord.ui.View(timeout=180)
        view.add_item(BackButton(self.bot, target="category_list", current_category=self.category))
        
        if file:
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view, attachments=[file])
        else:
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view, attachments=[])

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
            view = discord.ui.View(timeout=180)
            
            if len(frames) > 24:
                chunk_size = 24
                chunks = [frames[i:i + chunk_size] for i in range(0, len(frames), chunk_size)]
                for idx, chunk in enumerate(chunks):
                    start_letter = chunk[0][0].upper()
                    end_letter = chunk[-1][0].upper()
                    label = f"{category} ({start_letter}-{end_letter})"
                    view.add_item(FrameItemSelect(self.bot, label, chunk, category))
            else:
                view.add_item(FrameItemSelect(self.bot, f"Select a {category} Frame", frames, category))
                
            view.add_item(BackButton(self.bot, target="categories"))
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

    @frame_group.command(name="menu", description="Open the luxurious, interactive frame preview vault catalog")
    async def frame_menu(self, interaction: discord.Interaction):
        view = discord.ui.View(timeout=180)
        view.add_item(FrameCategorySelect(self.bot))
        embed = discord.Embed(
            title="<:red_lotus:1516679367743377448> [ HEAVENLY COURT VAULT ]",
            description="Welcome to the Frame Showroom. Select a system index class below to access the database collections.",
            color=0x6b1614
        )
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(FramesCog(bot))