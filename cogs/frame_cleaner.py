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

    @app_commands.command(name="test_clean", description="Execute Piecewise Spatial Matrix Extraction")
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
                        
                        LEFT, TOP = 42, 36
                        RIGHT, BOTTOM = fw - 42, fh - 36
                        
                        T_MIN = 10.0
                        T_MAX = 45.0
                        T_RANGE = T_MAX - T_MIN
                        
                        datas = img.getdata()
                        new_data = []
                        
                        for idx, item in enumerate(datas):
                            x = idx % fw
                            y = idx // fw
                            r, g, b, a = item
                            
                            # Piecewise Domain Restriction: Only execute extraction inside the inner matrix
                            if LEFT <= x <= RIGHT and TOP <= y <= BOTTOM:
                                dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2) ** 0.5
                                if dist <= T_MIN:
                                    new_data.append((0, 0, 0, 0))
                                elif dist >= T_MAX:
                                    new_data.append(item)
                                else:
                                    ratio = (dist - T_MIN) / T_RANGE
                                    interpolation_factor = (ratio ** 2) * (3.0 - 2.0 * ratio)
                                    new_data.append((r, g, b, int(a * interpolation_factor)))
                            else:
                                # Force absolute boundary opacity
                                new_data.append((r, g, b, 255))
                                
                        img.putdata(new_data)
                        
                        output_buffer = BytesIO()
                        img.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file_name = f"spatial_extract_{match.replace(' ', '_')}.png"
                        file = discord.File(fp=output_buffer, filename=file_name)
                        
                        embed = discord.Embed(
                            title="Piecewise Spatial Domain Extraction",
                            color=0x2b2d31
                        )
                        
                        embed.add_field(
                            name="Orthogonal Boundary Conditions", 
                            value=(
                                "$$\\Omega_{inner} = \\{ (x,y) \\in \\mathbb{R}^2 \\mid X_{min} \\le x \\le X_{max} \\land Y_{min} \\le y \\le Y_{max} \\}$$\n"
                                f"$$X_{{min}} = {LEFT}, X_{{max}} = {RIGHT}$$\n"
                                f"$$Y_{{min}} = {TOP}, Y_{{max}} = {BOTTOM}$$"
                            ),
                            inline=False
                        )
                        
                        embed.add_field(
                            name="Piecewise Alpha Tensor", 
                            value=(
                                "$$ M(x,y) = \\begin{cases} "
                                "1 & \\text{if } (x,y) \\notin \\Omega_{inner} \\\\"
                                "\\mathcal{H}_{smooth}( \\| \\mathbf{C}_{(x,y)} - \\mathbf{C}_{bg} \\|_2 ) & \\text{if } (x,y) \\in \\Omega_{inner} "
                                "\\end{cases} $$"
                            ),
                            inline=False
                        )
                        
                        embed.set_image(url=f"attachment://{file_name}")
                        await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"Runtime Exception: {e}")
            print(f"Extraction Error: {e}", file=sys.stderr)

    @app_commands.command(name="test_composite", description="Execute Piecewise Spatially Bounded Fusion")
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
                        
                        LEFT, TOP = 42, 36
                        RIGHT, BOTTOM = fw - 42, fh - 36
                        inner_w, inner_h = RIGHT - LEFT, BOTTOM - TOP
                        
                        T_MIN = 10.0
                        T_MAX = 45.0
                        T_RANGE = T_MAX - T_MIN
                        
                        datas = frame_img.getdata()
                        new_data = []
                        
                        for idx, item in enumerate(datas):
                            x = idx % fw
                            y = idx // fw
                            r, g, b, a = item
                            
                            if LEFT <= x <= RIGHT and TOP <= y <= BOTTOM:
                                dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2) ** 0.5
                                if dist <= T_MIN:
                                    new_data.append((0, 0, 0, 0))
                                elif dist >= T_MAX:
                                    new_data.append(item)
                                else:
                                    ratio = (dist - T_MIN) / T_RANGE
                                    interpolation_factor = (ratio ** 2) * (3.0 - 2.0 * ratio)
                                    new_data.append((r, g, b, int(a * interpolation_factor)))
                            else:
                                new_data.append((r, g, b, 255))
                                
                        frame_img.putdata(new_data)
                        
                        try:
                            resample_method = Image.Resampling.LANCZOS
                        except AttributeError:
                            resample_method = Image.ANTIALIAS
                            
                        card_resized = ImageOps.fit(base_img, (inner_w, inner_h), method=resample_method)
                        
                        mask = Image.new("L", (inner_w, inner_h), 0)
                        draw = ImageDraw.Draw(mask)
                        draw.rounded_rectangle((0, 0, inner_w, inner_h), radius=20, fill=255)
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
                            title="[ SYSTEM: ORTHOGONAL GEOMETRIC FUSION ]",
                            color=0x2b2d31
                        )
                        
                        embed.add_field(
                            name="Affine Transformation", 
                            value=(
                                "$$f: \\mathbb{R}^2 \\to \\mathbb{R}^2$$\n"
                                f"$$D_{{out}} = [{LEFT}, {RIGHT}] \\times [{TOP}, {BOTTOM}]$$"
                            ),
                            inline=False
                        )
                        
                        embed.add_field(
                            name="Piecewise Subspace Interlock", 
                            value=(
                                "$$\\mathbf{C}_{final} = \\begin{cases} "
                                "\\mathbf{C}_{frame} & \\text{if } (x,y) \\notin \\Omega_{inner} \\\\"
                                "\\mathbf{C}_{frame} \\oplus_{\\alpha} (\\mathbf{C}_{base} \\circ M_{clip}) & \\text{if } (x,y) \\in \\Omega_{inner} "
                                "\\end{cases} $$"
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