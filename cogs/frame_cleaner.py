import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw
import sys
import os
from frame_prices import FRAME_DB

BASE_CARD_PATH = os.path.join("assets", "base_card.jpg")

class FrameRenderEngine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test_composite", description="Execute Pure Topological Overlay (Zero Chroma-Key)")
    async def test_composite(self, interaction: discord.Interaction, frame_name: str):
        match = next((n for n in FRAME_DB if frame_name.lower() in n.lower()), None)
        if not match:
            return await interaction.response.send_message("Target entity not located in index.", ephemeral=True)

        image_url = FRAME_DB[match].get("image")
        if not image_url:
            return await interaction.response.send_message("Vector topology unavailable.", ephemeral=True)

        if not os.path.exists(BASE_CARD_PATH):
            return await interaction.response.send_message("Base matrix `assets/base_card.jpg` missing.", ephemeral=True)

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("HTTP transmission failed.")
                    
                    frame_bytes = await resp.read()
                    
                    with Image.open(BASE_CARD_PATH).convert("RGBA") as base_img, \
                         Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:
                         
                        fw, fh = frame_img.size
                        
                        LEFT, TOP = 40, 32
                        RIGHT, BOTTOM = fw - 40, fh - 32
                        inner_w, inner_h = RIGHT - LEFT, BOTTOM - TOP
                        
                        try:
                            resample_method = Image.Resampling.LANCZOS
                        except AttributeError:
                            resample_method = Image.ANTIALIAS
                            
                        card_resized = ImageOps.fit(base_img, (inner_w, inner_h), method=resample_method)
                        
                        mask = Image.new("L", (inner_w, inner_h), 0)
                        draw = ImageDraw.Draw(mask)
                        draw.rounded_rectangle((0, 0, inner_w, inner_h), radius=22, fill=255)
                        card_resized.putalpha(mask)
                        
                        canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
                        canvas.paste(card_resized, (LEFT, TOP), card_resized)
                        
                        final_composite = Image.alpha_composite(canvas, frame_img)
                        
                        output_buffer = BytesIO()
                        final_composite.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file_name = f"composite_{match.replace(' ', '_')}.png"
                        file = discord.File(fp=output_buffer, filename=file_name)
                        
                        embed = discord.Embed(
                            title="[ SYSTEM: PURE TOPOLOGICAL OVERLAY ]",
                            description="Chroma-key matrix bypassed. Utilizing native asset alpha channels.",
                            color=0x2b2d31
                        )
                        
                        embed.add_field(
                            name="Diagnostic Revelation", 
                            value=(
                                "The 'gray background' was a phantom visual artifact caused by the Discord client's "
                                "native `#313338` background rendering beneath the pre-existing transparent alpha layer."
                            ),
                            inline=False
                        )

                        embed.add_field(
                            name="Geometric Subspace Interlock", 
                            value=(
                                f"$$D_{{out}} = [{LEFT}, {RIGHT}] \\times [{TOP}, {BOTTOM}]$$\n"
                                "$$\\partial \\Omega = \\rho_{22} \\quad (C^1 \\text{ boundary curvature})$$"
                            ),
                            inline=False
                        )
                        
                        embed.set_image(url=f"attachment://{file_name}")
                        await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"Runtime Exception: {e}")
            print(f"Composite Error: {e}", file=sys.stderr)

async def setup(bot):
    await bot.add_cog(FrameRenderEngine(bot))