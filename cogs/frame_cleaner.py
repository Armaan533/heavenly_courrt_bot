import discord
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw, ImageFont
import asyncio
from collections import deque
from frame_prices import FRAME_DB

KARUTA_BOT_ID = 646937666251915264

class FrameTestModal(discord.ui.Modal, title="Frame Rendering Matrix"):
    frame_name = discord.ui.TextInput(
        label="Enter Frame Name", 
        placeholder="e.g. Voidspawn, Interface, Spring..."
    )

    def __init__(self, bot, card_url, char_name, prompt_message):
        super().__init__()
        self.bot = bot
        self.card_url = card_url
        self.char_name = char_name
        self.prompt_message = prompt_message

    async def on_submit(self, interaction: discord.Interaction):
        f_name = self.frame_name.value.strip().lower()
        
        try:
            await self.prompt_message.delete()
        except:
            pass

        
        match = next((n for n in FRAME_DB if f_name in n.lower()), None)
        if not match:
            return await interaction.response.send_message(f"❌ Frame `{f_name}` not found in the database.", ephemeral=True)

        frame_url = FRAME_DB[match].get("image")
        if not frame_url:
            return await interaction.response.send_message(f"❌ No image mapped for {match.title()}.", ephemeral=True)

        await interaction.response.defer(ephemeral=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.card_url) as card_resp, session.get(frame_url) as frame_resp:
                    if card_resp.status != 200 or frame_resp.status != 200:
                        return await interaction.followup.send("❌ Failed to fetch assets from Discord content servers.")
                    
                    card_bytes = await card_resp.read()
                    frame_bytes = await frame_resp.read()

                    output_buffer = await asyncio.to_thread(self.process_frame, card_bytes, frame_bytes)

                    file = discord.File(fp=output_buffer, filename=f"preview_{match.replace(' ', '_')}.png")
                    
                    embed = discord.Embed(
                        title="✦ . FRAME RENDER . ✦",
                        description=f"**Character:** {self.char_name}\n**Frame:** {match.title()}",
                        color=0x2b2d31
                    )
                    embed.set_image(url=f"attachment://{file.filename}")
                    
                    await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"❌ **Render Error:** {e}")

    def process_frame(self, card_bytes, frame_bytes):
        """Executes targeted background area flood fill maps and top-layer text stamping."""
        with Image.open(BytesIO(card_bytes)).convert("RGBA") as card_img, \
             Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:
             
            fw, fh = frame_img.size
            pixels = frame_img.load()
            
            
            bg_mask = Image.new("L", (fw, fh), 0)
            mask_pixels = bg_mask.load()
            bg_r, bg_g, bg_b = 49, 51, 56
            
            def do_flood_fill(start_xy):
                if start_xy[0] < 0 or start_xy[0] >= fw or start_xy[1] < 0 or start_xy[1] >= fh:
                    return
                q = deque([start_xy])
                visited = {start_xy}
                while q:
                    cx, cy = q.popleft()
                    mask_pixels[cx, cy] = 255
                    
                    for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < fw and 0 <= ny < fh:
                            if (nx, ny) not in visited:
                                r, g, b, a = pixels[nx, ny]
                                dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2) ** 0.5
                                
                                if dist <= 50.0:
                                    visited.add((nx, ny))
                                    q.append((nx, ny))
            
            do_flood_fill((0, 0))               
            do_flood_fill((fw // 2, fh // 2))   
            
            
            T_MIN = 3.0   
            T_MAX = 45.0  
            
            for y in range(fh):
                for x in range(fw):
                    if mask_pixels[x, y] == 255:
                        r, g, b, a = pixels[x, y]
                        dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2) ** 0.5
                        
                        if dist <= T_MIN:
                            pixels[x, y] = (0, 0, 0, 0)
                        elif dist >= T_MAX:
                            pass 
                        else:
                            ratio = (dist - T_MIN) / (T_MAX - T_MIN)
                            factor = ratio * ratio * (3.0 - 2.0 * ratio)
                            pixels[x, y] = (r, g, b, int(a * factor))
            
            
            PAD = 14
            inner_w, inner_h = fw - (PAD * 2), fh - (PAD * 2)
            
            try: resample_method = Image.Resampling.LANCZOS
            except AttributeError: resample_method = Image.ANTIALIAS
                
            card_resized = ImageOps.fit(card_img, (inner_w, inner_h), method=resample_method).convert("RGBA")
            
            mask = Image.new("L", (inner_w, inner_h), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.rounded_rectangle((0, 0, inner_w, inner_h), radius=15, fill=255)
            card_resized.putalpha(mask)
            
            canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
            canvas.paste(card_resized, (PAD, PAD), card_resized)
            
            
            final_composite = Image.alpha_composite(canvas, frame_img)
            
            
            draw_text = ImageDraw.Draw(final_composite)
            
            font_paths = ["arialbd.ttf", "Helvetica-Bold.ttf", "Arial Bold.ttf", "arial.ttf"]
            font_top, font_bottom = None, None
            
            for path in font_paths:
                try:
                    font_top = ImageFont.truetype(path, int(fh * 0.048))   
                    font_bottom = ImageFont.truetype(path, int(fh * 0.042))
                    break
                except IOError:
                    continue
            
            if not font_top:
                font_top = ImageFont.load_default()
                font_bottom = ImageFont.load_default()
            
            
            COLOR_TOP = (15, 15, 15, 255)       
            COLOR_BOTTOM = (245, 245, 245, 255) 
            
            
            top_text = self.char_name
            try:
                left, top, right, bottom = draw_text.textbbox((0, 0), top_text, font=font_top)
                tw = right - left
            except AttributeError:
                tw, _ = draw_text.textsize(top_text, font=font_top)
            
            top_x = (fw - tw) // 2
            top_y = int(fh * 0.038) 
            draw_text.text((top_x, top_y), top_text, font=font_top, fill=COLOR_TOP)
            
            
            bottom_text = "Fang Yuan"
            try:
                left, top, right, bottom = draw_text.textbbox((0, 0), bottom_text, font=font_bottom)
                bw = right - left
            except AttributeError:
                bw, _ = draw_text.textsize(bottom_text, font=font_bottom)
                
            bot_x = (fw - bw) // 2
            bot_y = int(fh * 0.915) 
            draw_text.text((bot_x, bot_y), bottom_text, font=font_bottom, fill=COLOR_BOTTOM)
            
            output = BytesIO()
            final_composite.save(output, format="PNG")
            output.seek(0)
            return output


class FrameTestPromptView(discord.ui.View):
    def __init__(self, bot, card_url, char_name):
        super().__init__(timeout=60)
        self.bot = bot
        self.card_url = card_url
        self.char_name = char_name

    @discord.ui.button(label="Test Frame", style=discord.ButtonStyle.danger, emoji="⚙️")
    async def open_test_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Access Denied: Administrator configuration required.", ephemeral=True)
            
        await interaction.response.send_modal(FrameTestModal(self.bot, self.card_url, self.char_name, interaction.message))


class FrameTesterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != KARUTA_BOT_ID or not message.embeds:
            return
        
        embed = message.embeds[0]
        title = str(embed.title) if embed.title else ""
        
        if "Character Lookup" in title:
            try: await message.add_reaction("⚠️")
            except: pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.id != KARUTA_BOT_ID or not after.embeds:
            return
            
        embed = after.embeds[0]
        title = str(embed.title) if embed.title else ""
        
        if "Character Lookup" in title:
            has_reaction = any(str(r.emoji) == "⚠️" and r.me for r in after.reactions)
            if not has_reaction:
                try: await after.add_reaction("⚠️")
                except: pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⚠️" or payload.user_id == self.bot.user.id:
            return
            
        if not payload.member or not payload.member.guild_permissions.administrator:
            return
            
        try:
            channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            if message.author.id != KARUTA_BOT_ID or not message.embeds:
                return
                
            embed = message.embeds[0]
            title = str(embed.title) if embed.title else ""

            if "Character Lookup" not in title:
                return

            card_url = None
            if embed.image and embed.image.url:
                card_url = embed.image.url
            elif embed.thumbnail and embed.thumbnail.url:
                card_url = embed.thumbnail.url

            if not card_url:
                return

            char_name = "Unknown"
            if embed.description:
                for line in embed.description.splitlines():
                    if "Character" in line or "Character ·" in line:
                        char_name = line.split("·")[-1].replace("*", "").strip()
                        break

            user = await self.bot.fetch_user(payload.user_id)
            await channel.send(
                f"🔧 **Session Initialized:** {user.mention}, render a custom workspace for **{char_name}**?",
                view=FrameTestPromptView(self.bot, card_url, char_name),
                delete_after=60
            )

        except Exception as e:
            print(f"Reaction Session Error: {e}")

async def setup(bot):
    await bot.add_cog(FrameTesterCog(bot))