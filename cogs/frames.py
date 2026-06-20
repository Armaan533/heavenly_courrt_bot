import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image
import math
import os

from frame_prices import FRAME_DB

BASE_CARD_PATH = os.path.join("assets", "base_card.jpg")

class FrameCategorySelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        categories = sorted(list(set(data.get("type", "Unknown") for data in FRAME_DB.values())))
        
        options = [
            discord.SelectOption(label=cat, value=cat, emoji="🗂️") 
            for cat in categories
        ]
        
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
                description="This category is quite large! Please select a subset dropdown below to find your frame.",
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
        options = []
        for name in frame_list:
            options.append(discord.SelectOption(label=name.title(), value=name, emoji="🖼️"))
            
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
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
                value="*⚠️ Pricing fluctuates heavily. Insufficient market data available for standard calculation.*", 
                inline=False
            )
        else:
            embed.add_field(name="<:eight_side_sparkle:1516681364806570105> Market Value", value=f"**{market_price}** 🎟️", inline=True)
            
            if liquid_price >= 25 and frame_type.lower() != "bits":
                embed.add_field(name="<:for_john:1517226175901208696> Liquid Cost", value=f"**{liquid_price}** 🎟️", inline=True)
                
        embed.set_footer(text="Estimates based on ledger logs. Verify before finalizing trades.")
        
        file = None
        if image_url and os.path.exists(BASE_CARD_PATH):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            frame_bytes = await resp.read()
                            
                            with Image.open(BASE_CARD_PATH) as base_img, Image.open(BytesIO(frame_bytes)) as frame_img:
                                frame_rgba = frame_img.convert("RGBA")
                                datas = frame_rgba.getdata()
                                
                                target_width, target_height = frame_rgba.size
                                
                                newData = []
                                for idx, item in enumerate(datas):
                                    x = idx % target_width
                                    y = idx // target_width
                                    
                                    if 40 <= item[0] <= 55 and 40 <= item[1] <= 55 and 40 <= item[2] <= 55:
                                        newData.append((0, 0, 0, 0))
                                        
                                    elif (0.10 * target_width <= x <= 0.60 * target_width) and (0.04 * target_height <= y <= 0.13 * target_height) and (item[0] < 25 and item[1] < 25 and item[2] < 25):
                                        newData.append((0, 0, 0, 0))
                                        
                                    elif (0.40 * target_width <= x <= 0.92 * target_width) and (0.87 * target_height <= y <= 0.96 * target_height) and (item[0] < 25 and item[1] < 25 and item[2] < 25):
                                        newData.append((0, 0, 0, 0))
                                        
                                    else:
                                        newData.append(item)
                                        
                                frame_rgba.putdata(newData)
                                
                                base_w, base_h = base_img.size
                                
                                scale = max(target_width / base_w, target_height / base_h)
                                new_w = int(base_w * scale)
                                new_h = int(base_h * scale)
                                
                                try:
                                    resample_filter = Image.Resampling.LANCZOS
                                except AttributeError:
                                    resample_filter = Image.ANTIALIAS
                                    
                                resized_base = base_img.resize((new_w, new_h), resample_filter)
                                
                                left = (new_w - target_width) / 2
                                top = (new_h - target_height) / 2
                                cropped_base = resized_base.crop((left, top, left + target_width, top + target_height))
                                
                                final_composite = Image.new("RGBA", frame_rgba.size)
                                final_composite.paste(cropped_base, (0, 0))
                                final_composite.paste(frame_rgba, (0, 0), frame_rgba)
                                
                                output_buffer = BytesIO()
                                final_composite.convert("RGB").save(output_buffer, format="JPEG", quality=90)
                                output_buffer.seek(0)
                                
                                file = discord.File(fp=output_buffer, filename="preview.jpg")
                                embed.set_image(url="attachment://preview.jpg")
            except Exception:
                pass 

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