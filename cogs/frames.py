import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw
import os
import sys

from frame_prices import FRAME_DB

class FrameCategorySelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        categories = sorted(list(set(data.get("type", "Unknown") for data in FRAME_DB.values())))
        options = [discord.SelectOption(label=cat, value=cat, emoji="🗂️") for cat in categories]
        super().__init__(placeholder="Select a frame category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        category = self.values[0]
        frames = sorted([name for name, data in FRAME_DB.items() if data.get("type") == category])
        
        view = discord.ui.View(timeout=180)
        if len(frames) > 24:
            chunk_size = 24
            chunks = [frames[i:i + chunk_size] for i in range(0, len(frames), chunk_size)]
            for chunk in chunks:
                label = f"{category} ({chunk[0][0].upper()}-{chunk[-1][0].upper()})"
                view.add_item(FrameItemSelect(self.bot, label, chunk, category))
        else:
            view.add_item(FrameItemSelect(self.bot, f"Select a {category} Frame", frames, category))
        
        view.add_item(BackButton(self.bot, target="categories"))
        embed = discord.Embed(title=f"📁 [ {category.upper()} CATALOG ]", color=0x6b1614)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view)

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
        image_url = data.get("image")
        
        embed = discord.Embed(title=f"🖼️ Preview: {frame_name.title()}", color=0x6b1614)
        file = None
        
        if image_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            img = Image.open(BytesIO(await resp.read())).convert("RGBA")
                            data = img.getdata()
                            new_data = [(0,0,0,0) if (i[0]+i[1]+i[2]) < 200 and i[0] < 70 else i for i in data]
                            img.putdata(new_data)
                            
                            buf = BytesIO()
                            img.save(buf, format="PNG")
                            buf.seek(0)
                            file = discord.File(buf, "frame.png")
                            embed.set_image(url="attachment://frame.png")
            except: pass
            
        view = discord.ui.View(timeout=180)
        view.add_item(BackButton(self.bot, target="category_list", current_category=self.category))
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=view, attachments=[file] if file else [])

class BackButton(discord.ui.Button):
    def __init__(self, bot, target, current_category=None):
        super().__init__(label="Go Back", style=discord.ButtonStyle.danger, emoji="🔙")
        self.bot, self.target, self.current_category = bot, target, current_category

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.target == "categories":
            view = discord.ui.View(timeout=180)
            view.add_item(FrameCategorySelect(self.bot))
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=discord.Embed(title="📁 [ VAULT ]", color=0x6b1614), view=view, attachments=[])
        else:

            frames = sorted([n for n, d in FRAME_DB.items() if d.get("type") == self.current_category])
            view = discord.ui.View(timeout=180)
            view.add_item(FrameItemSelect(self.bot, f"Select a {self.current_category} Frame", frames, self.current_category))
            view.add_item(BackButton(self.bot, target="categories"))
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=discord.Embed(title=f"📁 [ {self.current_category.upper()} CATALOG ]", color=0x6b1614), view=view, attachments=[])

class FramesCog(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @app_commands.command(name="frame", description="Open frame vault")
    async def frame_menu(self, interaction: discord.Interaction):
        view = discord.ui.View(timeout=180)
        view.add_item(FrameCategorySelect(self.bot))
        await interaction.response.send_message(embed=discord.Embed(title="📁 [ VAULT ]", color=0x6b1614), view=view)

async def setup(bot): await bot.add_cog(FramesCog(bot))