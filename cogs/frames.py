import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw
import os
from frame_prices import FRAME_DB

BASE_CARD_PATH = os.path.join("assets", "base_card.jpg")

async def generate_composite(frame_name):
    image_url = FRAME_DB[frame_name].get("image")
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            frame_bytes = await resp.read()
    
    with Image.open(BASE_CARD_PATH).convert("RGBA") as base_img, \
         Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:
        
        fw, fh = frame_img.size
        card = ImageOps.fit(base_img, (fw, fh), Image.Resampling.LANCZOS).convert("RGBA")
        final = Image.alpha_composite(card, frame_img)
        
        buf = BytesIO()
        final.save(buf, format="PNG")
        buf.seek(0)
        return buf

class FramesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def frame_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=name.title()[:100], value=name[:100])
            for name in FRAME_DB.keys() 
            if current.lower() in name.lower()
        ][:25]

    @app_commands.command(name="lookup", description="Lookup a frame with live composite render")
    @app_commands.autocomplete(frame_name=frame_autocomplete)
    async def frame_lookup(self, interaction: discord.Interaction, frame_name: str):
        if frame_name not in FRAME_DB:
            return await interaction.response.send_message("❌ Frame not found.", ephemeral=True)
            
        await interaction.response.defer()
        img_buf = await generate_composite(frame_name)
        file = discord.File(img_buf, filename="render.png")
        
        embed = discord.Embed(title=f"Render: {frame_name.title()}", color=0x6b1614)
        embed.set_image(url="attachment://render.png")
        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name="menu", description="Open the frame vault")
    async def frame_menu(self, interaction: discord.Interaction):
        await interaction.response.send_message("Vault opening...", ephemeral=True)

async def setup(bot):
    await bot.add_cog(FramesCog(bot))