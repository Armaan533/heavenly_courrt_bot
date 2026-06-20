import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw
import os
from frame_prices import FRAME_DB

BASE_CARD_PATH = os.path.join("assets", "base_card.jpg")

async def get_frame_render(frame_name):
    """The extraction and compositing engine as per research specs."""
    image_url = FRAME_DB[frame_name].get("image")
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            frame_bytes = await resp.read()
    
    with Image.open(BASE_CARD_PATH).convert("RGBA") as base_img, \
         Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:
        fw, fh = frame_img.size
        PAD = 14 
        inner_w, inner_h = fw - (PAD*2), fh - (PAD*2)
        
        card = ImageOps.fit(base_img, (inner_w, inner_h), Image.Resampling.LANCZOS).convert("RGBA")
        
        mask = Image.new("L", (inner_w, inner_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, inner_w, inner_h), radius=20, fill=255)
        card.putalpha(mask)
        
        canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        canvas.paste(card, (PAD, PAD), card)
        final = Image.alpha_composite(canvas, frame_img)
        
        buf = BytesIO()
        final.save(buf, format="PNG")
        buf.seek(0)
        return buf

class FramesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="lookup", description="Lookup a frame with live composite render")
    @app_commands.autocomplete(frame_name=lambda inter, cur: [app_commands.Choice(name=n, value=n) for n in FRAME_DB if cur.lower() in n.lower()][:25])
    async def frame_lookup(self, interaction: discord.Interaction, frame_name: str):
        if frame_name not in FRAME_DB:
            return await interaction.response.send_message("❌ Frame not found.", ephemeral=True)
            
        await interaction.response.defer()
        # Generate the high-quality composite [cite: 38, 46]
        img_buf = await get_frame_render(frame_name)
        file = discord.File(img_buf, filename="render.png")
        
        embed = discord.Embed(title=f"Render: {frame_name.title()}", color=0x6b1614)
        embed.set_image(url="attachment://render.png")
        await interaction.followup.send(embed=embed, file=file)

async def setup(bot):
    await bot.add_cog(FramesCog(bot))