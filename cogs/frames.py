import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw
import os

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
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            frame_bytes = await resp.read()
                            
                            with Image.open(BASE_CARD_PATH).convert("RGBA") as base_img, Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:
                                fw, fh = frame_img.size
                                
                                # 1. SOFT CHROMA KEY: Perfectly removes gray and blends anti-aliased edges
                                datas = frame_img.getdata()
                                newData = []
                                for idx, item in enumerate(datas):
                                    x = idx % fw
                                    y = idx // fw
                                    r, g, b, a = item
                                    
                                    # Target the solid black nameplate areas and wipe them entirely
                                    is_top_plate = (0.08 <= x / fw <= 0.48) and (0.015 <= y / fh <= 0.075)
                                    is_bottom_plate = (0.55 <= x / fw <= 0.95) and (0.91 <= y / fh <= 0.985)
                                    
                                    if (is_top_plate or is_bottom_plate) and (r < 35 and g < 35 and b < 35):
                                        newData.append((0, 0, 0, 0))
                                        continue
                                        
                                    # Mathematical distance to Discord's gray color variants
                                    dr, dg, db = abs(r - 49), abs(g - 51), abs(b - 56)
                                    dr2, dg2, db2 = abs(r - 47), abs(g - 49), abs(b - 54)
                                    dist = min(max(dr, dg, db), max(dr2, dg2, db2))
                                    
                                    if dist <= 6:
                                        newData.append((0, 0, 0, 0)) # Pure background
                                    elif dist <= 24:
                                        # Smooth 18-step transparency transition for edge blending
                                        alpha = int(((dist - 6) / 18) * 255)
                                        newData.append((r, g, b, min(a, alpha)))
                                    else:
                                        newData.append(item)
                                        
                                frame_img.putdata(newData)
                                
                                # 2. PREPARE BASE CARD: Squeeze slightly so corners don't bleed outside frame
                                try:
                                    resample_filter = Image.Resampling.LANCZOS
                                except AttributeError:
                                    resample_filter = Image.ANTIALIAS
                                    
                                inset_x = int(fw * 0.04) # Squeeze inward 4% on left/right
                                inset_y = int(fh * 0.01) # Squeeze inward 1% on top/bottom
                                inner_w = fw - (2 * inset_x)
                                inner_h = fh - (2 * inset_y)
                                
                                base_resized = ImageOps.fit(base_img, (inner_w, inner_h), method=resample_filter)
                                
                                mask = Image.new("L", (inner_w, inner_h), 0)
                                draw_mask = ImageDraw.Draw(mask)
                                draw_mask.rounded_rectangle((0, 0, inner_w, inner_h), radius=28, fill=255)
                                base_resized.putalpha(mask)
                                
                                # 3. COMPOSITE
                                base_canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
                                base_canvas.paste(base_resized, (inset_x, inset_y), base_resized)
                                
                                final_composite = Image.alpha_composite(base_canvas, frame_img)
                                
                                output_buffer = BytesIO()
                                final_composite.save(output_buffer, format="PNG")
                                output_buffer.seek(0)
                                
                                file = discord.File(fp=output_buffer, filename="preview.png")
                                embed.set_image(url="attachment://preview.png")
            except Exception as e:
                print(f"Frame Processing Error: {e}")

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