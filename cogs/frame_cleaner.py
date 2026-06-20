import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps
import sys
import os
from frame_prices import FRAME_DB

BASE_CARD_PATH = os.path.join("assets", "base_card.jpg")

class FrameRenderEngine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test_clean", description="Execute Dual-Zone Spatial Matrix Extraction")
    async def test_clean(self, interaction: discord.Interaction, frame_name: str):
        match = next((n for n in FRAME_DB if frame_name.lower() in n.lower()), None)
        if not match:
            return await interaction.response.send_message("Frame entity not located in database.", ephemeral=True)

        image_url = FRAME_DB[match].get("image")
        if not image_url:
            return await interaction.response.send_message("Image vector unavailable.", ephemeral=True)

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("HTTP transmission failed.")
                    
                    frame_bytes = await resp.read()
                    
                    with Image.open(BytesIO(frame_bytes)).convert("RGBA") as img:
                        fw, fh = img.size
                        bg_r, bg_g, bg_b = 49, 51, 56
                        
                        LEFT, TOP = 40, 32
                        RIGHT, BOTTOM = fw - 40, fh - 32
                        
                        IN_T_MIN, IN_T_MAX = 10.0, 45.0
                        OUT_T_MIN, OUT_T_MAX = 5.0, 15.0
                        
                        datas = img.getdata()
                        new_data = []
                        
                        for idx, item in enumerate(datas):
                            x = idx % fw
                            y = idx // fw
                            r, g, b, a = item
                            
                            dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2) ** 0.5
                            
                            if LEFT <= x <= RIGHT and TOP <= y <= BOTTOM:
                                if dist <= IN_T_MIN:
                                    new_data.append((0, 0, 0, 0))
                                elif dist >= IN_T_MAX:
                                    new_data.append(item)
                                else:
                                    ratio = (dist - IN_T_MIN) / (IN_T_MAX - IN_T_MIN)
                                    factor = (ratio ** 2) * (3.0 - 2.0 * ratio)
                                    new_data.append((r, g, b, int(a * factor)))
                            else:
                                if dist <= OUT_T_MIN:
                                    new_data.append((0, 0, 0, 0))
                                elif dist >= OUT_T_MAX:
                                    new_data.append(item)
                                else:
                                    ratio = (dist - OUT_T_MIN) / (OUT_T_MAX - OUT_T_MIN)
                                    factor = (ratio ** 2) * (3.0 - 2.0 * ratio)
                                    new_data.append((r, g, b, int(a * factor)))
                                
                        img.putdata(new_data)
                        
                        output_buffer = BytesIO()
                        img.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file_name = f"dual_extract_{match.replace(' ', '_')}.png"
                        file = discord.File(fp=output_buffer, filename=file_name)
                        
                        embed = discord.Embed(
                            title="[ SYSTEM: DUAL-ZONE DOMAIN EXTRACTION ]",
                            color=0x2b2d31
                        )
                        
                        embed.add_field(
                            name="Internal Subspace (Gradient Sweep)", 
                            value=(
                                "$$(x,y) \\in \\Omega_{inner}$$\n"
                                f"$$\\tau_{{min}} = {IN_T_MIN}, \\quad \\tau_{{max}} = {IN_T_MAX}$$"
                            ),
                            inline=False
                        )
                        
                        embed.add_field(
                            name="External Boundary (Strict Cutoff)", 
                            value=(
                                "$$(x,y) \\notin \\Omega_{inner}$$\n"
                                f"$$\\tau_{{min}} = {OUT_T_MIN}, \\quad \\tau_{{max}} = {OUT_T_MAX}$$\n"
                                "Isolates and terminates residual topological artifacts in outer geometries."
                            ),
                            inline=False
                        )
                        
                        embed.set_image(url=f"attachment://{file_name}")
                        await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"Runtime Exception: {e}")
            print(f"Extraction Error: {e}", file=sys.stderr)

    @app_commands.command(name="test_composite", description="Execute Raw Z-Index Overlay")
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
                        bg_r, bg_g, bg_b = 49, 51, 56
                        
                        LEFT, TOP = 40, 32
                        RIGHT, BOTTOM = fw - 40, fh - 32
                        
                        IN_T_MIN, IN_T_MAX = 10.0, 45.0
                        OUT_T_MIN, OUT_T_MAX = 5.0, 15.0
                        
                        datas = frame_img.getdata()
                        new_data = []
                        
                        for idx, item in enumerate(datas):
                            x = idx % fw
                            y = idx // fw
                            r, g, b, a = item
                            
                            dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2) ** 0.5
                            
                            if LEFT <= x <= RIGHT and TOP <= y <= BOTTOM:
                                if dist <= IN_T_MIN:
                                    new_data.append((0, 0, 0, 0))
                                elif dist >= IN_T_MAX:
                                    new_data.append(item)
                                else:
                                    ratio = (dist - IN_T_MIN) / (IN_T_MAX - IN_T_MIN)
                                    factor = (ratio ** 2) * (3.0 - 2.0 * ratio)
                                    new_data.append((r, g, b, int(a * factor)))
                            else:
                                if dist <= OUT_T_MIN:
                                    new_data.append((0, 0, 0, 0))
                                elif dist >= OUT_T_MAX:
                                    new_data.append(item)
                                else:
                                    ratio = (dist - OUT_T_MIN) / (OUT_T_MAX - OUT_T_MIN)
                                    factor = (ratio ** 2) * (3.0 - 2.0 * ratio)
                                    new_data.append((r, g, b, int(a * factor)))
                                
                        frame_img.putdata(new_data)
                        
                        try:
                            resample_method = Image.Resampling.LANCZOS
                        except AttributeError:
                            resample_method = Image.ANTIALIAS
                            
                        card_resized = ImageOps.fit(base_img, (fw, fh), method=resample_method).convert("RGBA")
                        
                        final_composite = Image.alpha_composite(card_resized, frame_img)
                        
                        output_buffer = BytesIO()
                        final_composite.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file_name = f"raw_composite_{match.replace(' ', '_')}.png"
                        file = discord.File(fp=output_buffer, filename=file_name)
                        
                        embed = discord.Embed(
                            title="[ SYSTEM: RAW ORTHOGONAL OVERLAY ]",
                            color=0x2b2d31
                        )
                        
                        embed.add_field(
                            name="Compositing Protocol", 
                            value=(
                                "$$\\mathbf{C}_{final} = \\mathbf{C}_{base} \\oplus_{\\alpha} \\mathbf{C}_{frame}$$\n"
                                "Direct 1:1 scale composite. No clipping domains or bounding masks applied."
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