import discord
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw
import asyncio
import numpy as np
from collections import deque
from frame_prices import FRAME_DB

KARUTA_BOT_ID = 646937666251915264

class FrameTestModal(discord.ui.Modal, title="Frame Rendering Matrix"):
    frame_name = discord.ui.TextInput(
        label="Enter Frame Name", 
        placeholder="e.g. Voidspawn, Hacker, Spring..."
    )

    def __init__(self, bot, card_url, char_name, prompt_message):
        super().__init__()
        self.bot = bot
        self.card_url = card_url
        self.char_name = char_name
        self.prompt_message = prompt_message

    async def on_submit(self, interaction: discord.Interaction):
        f_name = self.frame_name.value.strip().lower()
        
        try: await self.prompt_message.delete()
        except: pass

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
                        return await interaction.followup.send("❌ Failed to fetch assets from Discord servers.")
                    
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
        def _smoothstep(edge0, edge1, value):
            t = np.clip((value - edge0) / (edge1 - edge0 + 1e-6), 0.0, 1.0)
            return t * t * (3.0 - 2.0 * t)

        with Image.open(BytesIO(card_bytes)).convert("RGBA") as card_img, \
             Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:
             
            fw, fh = frame_img.size
            frame_arr = np.array(frame_img, dtype=np.float32)
            
            r = frame_arr[:, :, 0]
            g = frame_arr[:, :, 1]
            b = frame_arr[:, :, 2]
            orig_a = frame_arr[:, :, 3] / 255.0
            
            
            BG_RGB = np.array([49.0, 51.0, 56.0], dtype=np.float32)
            BG_LUM = 51.8
            PAD_X, PAD_Y = 25, 38
            FADE = 20.0
            T_LOW_EDGE, T_HIGH_EDGE = 2.0, 18.0
            DARK_BORDER_SLACK = 8.0
            DARK_BORDER_RANGE = 40.0
            UNMAT_MIN_ALPHA = 0.12

            rgb = np.stack([r, g, b], axis=-1)
            bg = BG_RGB[np.newaxis, np.newaxis, :]

            
            delta = rgb - bg
            above_bg = np.maximum(delta / (255.0 - bg + 1e-6), 0.0)
            below_bg = np.maximum(-delta / (bg + 1e-6), 0.0)
            physical_alpha = np.max(np.maximum(above_bg, below_bg), axis=-1)

            dist = np.sqrt(np.sum(delta * delta, axis=-1))

            
            y_idx, x_idx = np.ogrid[:fh, :fw]
            edge_x = np.clip(np.minimum(x_idx - PAD_X, (fw - PAD_X) - x_idx) / FADE, 0.0, 1.0)
            edge_y = np.clip(np.minimum(y_idx - PAD_Y, (fh - PAD_Y) - y_idx) / FADE, 0.0, 1.0)
            centre = np.minimum(edge_x, edge_y)
            edge_keep = np.power(1.0 - centre, 0.65)

            t_low = T_LOW_EDGE + (18.0 - T_LOW_EDGE) * centre
            t_high = T_HIGH_EDGE + (88.0 - T_HIGH_EDGE) * centre

            lum = r * 0.299 + g * 0.587 + b * 0.114
            c_max = np.maximum(np.maximum(r, g), b)
            c_min = np.minimum(np.minimum(r, g), b)
            sat = np.where(c_max > 1e-5, (c_max - c_min) / c_max, 0.0)

            sat_conf = _smoothstep(0.10, 0.55, sat)
            bright_conf = _smoothstep(BG_LUM + 16.0, BG_LUM + 110.0, lum)

            noise_floor = 0.012 + (0.060 - 0.012) * centre
            phys_gate = _smoothstep(noise_floor, noise_floor + 0.075, physical_alpha)

            interior_detail = np.maximum(sat_conf, bright_conf * 0.60)
            art_gate = np.maximum(edge_keep, interior_detail)

            color_alpha = _smoothstep(t_low, t_high, dist) * art_gate
            sat_alpha = np.clip(
                physical_alpha * phys_gate * art_gate * (0.75 + sat_conf * 1.45),
                0.0,
                1.0
            )

            
            dark_excess = BG_LUM - DARK_BORDER_SLACK - lum
            dark_signal = _smoothstep(0.0, DARK_BORDER_RANGE, dark_excess)
            dark_alpha = dark_signal * edge_keep

            raw_alpha = np.maximum.reduce([color_alpha, sat_alpha, dark_alpha])

            
            near_bg = (
                (dist < 34.0) &
                (sat < 0.18) &
                (physical_alpha < 0.26)
            )

            hole = np.zeros((fh, fw), dtype=bool)
            q = deque()

            seed_x0, seed_x1 = fw // 2 - 28, fw // 2 + 28
            seed_y0, seed_y1 = fh // 2 - 40, fh // 2 + 40

            ys, xs = np.where(near_bg[seed_y0:seed_y1, seed_x0:seed_x1])
            for sy, sx in zip(ys + seed_y0, xs + seed_x0):
                hole[sy, sx] = True
                q.append((sy, sx))

            while q:
                y, x = q.popleft()
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < fh and 0 <= nx < fw and near_bg[ny, nx] and not hole[ny, nx]:
                        hole[ny, nx] = True
                        q.append((ny, nx))

            hole_strength = hole.astype(np.float32) * (1.0 - np.maximum(sat_conf, bright_conf))
            raw_alpha *= (1.0 - hole_strength * 0.96)

            raw_alpha = np.clip(raw_alpha * orig_a, 0.0, 1.0)
            final_alpha = np.power(raw_alpha, 1.08)

            
            unmatte_a = np.clip(raw_alpha + 0.06, 0.18, 1.0)[:, :, np.newaxis]

            unmatted = (rgb - bg * (1.0 - unmatte_a)) / unmatte_a
            unmatted = np.clip(unmatted, 0.0, 255.0)

            unmat_strength = np.maximum(sat_conf, bright_conf)
            unmat_strength *= _smoothstep(0.10, 0.50, raw_alpha)
            unmat_strength = unmat_strength[:, :, np.newaxis]

            rgb_out = rgb * (1.0 - unmat_strength) + unmatted * unmat_strength

            
            frame_arr[:, :, 0] = rgb_out[:, :, 0]
            frame_arr[:, :, 1] = rgb_out[:, :, 1]
            frame_arr[:, :, 2] = rgb_out[:, :, 2]
            frame_arr[:, :, 3] = np.clip(final_alpha * 255.0, 0.0, 255.0)

            clean_frame = Image.fromarray(frame_arr.astype(np.uint8), "RGBA")

            
            inner_w = fw - (PAD_X * 2)
            inner_h = fh - (PAD_Y * 2)
            
            try: resample_method = Image.Resampling.LANCZOS
            except AttributeError: resample_method = Image.ANTIALIAS
            
            card_resized = ImageOps.fit(card_img, (inner_w, inner_h), method=resample_method).convert("RGBA")
            
            art_mask = Image.new("L", (inner_w, inner_h), 0)
            draw_art = ImageDraw.Draw(art_mask)
            draw_art.rounded_rectangle((0, 0, inner_w, inner_h), radius=15, fill=255)
            card_resized.putalpha(art_mask)
            
            canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
            canvas.paste(card_resized, (PAD_X, PAD_Y), card_resized)
            
            final_composite = Image.alpha_composite(canvas, clean_frame)
            
            
            final_mask = Image.new("L", (fw, fh), 0)
            draw_final = ImageDraw.Draw(final_mask)
            draw_final.rounded_rectangle((0, 0, fw, fh), radius=20, fill=255)
            
            final_arr = np.array(final_composite)
            mask_arr = np.array(final_mask)
            final_arr[:,:,3] = np.minimum(final_arr[:,:,3], mask_arr)
            final_composite = Image.fromarray(final_arr, 'RGBA')
            
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
            return await interaction.response.send_message("❌ Access Denied. Administrator clearance required.", ephemeral=True)
            
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
            
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        
        member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
        if not member or not member.guild_permissions.administrator:
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

            if "?" in card_url:
                card_url = card_url.split("?")[0]

            char_name = "Unknown"
            if embed.description:
                for line in embed.description.splitlines():
                    if "Character" in line or "Character ·" in line:
                        char_name = line.split("·")[-1].replace("*", "").strip()
                        break

            await channel.send(
                f"🔧 **Session Initialized:** {member.mention}, render a custom workspace for **{char_name}**?",
                view=FrameTestPromptView(self.bot, card_url, char_name),
                delete_after=60
            )

        except Exception as e:
            print(f"Reaction Session Error: {e}")

async def setup(bot):
    await bot.add_cog(FrameTesterCog(bot))