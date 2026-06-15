import discord
from discord.ext import commands
import re
import traceback

class EffortListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.processed_cache = []

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.process_effort_data(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self.process_effort_data(after)

    async def process_effort_data(self, message: discord.Message):
        if not message.author.bot or "karuta" not in message.author.name.lower():
            return
        if not message.embeds:
            return
        if message.id in self.processed_cache:
            return

        embed = message.embeds[0]
        
        # Safely extract all text
        content_parts = []
        if embed.author and embed.author.name: content_parts.append(embed.author.name)
        if embed.title: content_parts.append(embed.title)
        if embed.description: content_parts.append(embed.description)
        for field in embed.fields:
            content_parts.append(field.name)
            content_parts.append(field.value)
            
        raw_text = " ".join(content_parts)
        
        # Violent text sanitization to completely remove markdown
        clean_text = re.sub(r'[*`~_]', ' ', raw_text)
        clean_text = re.sub(r'[^\x20-\x7E]', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text)

        if "base value" not in clean_text.lower():
            return

        try:
            base_match = re.search(r'(\d+)\s+base\s+value', clean_text, re.IGNORECASE)
            if not base_match:
                return
            base_val = int(base_match.group(1))
            
            self.processed_cache.append(message.id)
            if len(self.processed_cache) > 100:
                self.processed_cache.pop(0)

            def parse_stat(stat_name):
                match = re.search(r'(\d+)\s+\(([SABCDEF])\)\s+' + stat_name, clean_text, re.IGNORECASE)
                if match:
                    return int(match.group(1)), match.group(2).upper()
                return 0, "F"

            style_val, _ = parse_stat("Style")
            tough_val, _ = parse_stat("Toughness")
            vanity_val, _ = parse_stat("Vanity")
            
            effort_match = re.search(r'Effort\s+(\d+)', clean_text, re.IGNORECASE)
            current_effort = int(effort_match.group(1)) if effort_match else base_val
            
            naked_effort = current_effort - style_val

            # The Flawless Karuta Cosmetic Math
            dye_val = base_val
            frame_val = 30
            mystic_dye_val = max(base_val + 10, 30)
            mystic_and_frame = frame_val + mystic_dye_val

            # Determine Applied Style String
            style_str = "None"
            if style_val > 0:
                if style_val == mystic_and_frame: style_str = "Mystic & Frame"
                elif style_val == frame_val: style_str = "Frame"
                elif style_val == dye_val: style_str = "Regular Dye"
                elif style_val == frame_val + dye_val: style_str = "Frame & Dye"
                else: style_str = f"Custom (+{style_val})"

            ticks = chr(96) * 3
            desc = f"🔎 **Identified :**\n"
            desc += f"Base Value · **{base_val}**\n"
            desc += f"Effort · **{current_effort}**\n"
            desc += f"Style Applied · **{style_str}**\n\n"

            # Mirror Keqing: Hide cosmetics if already applied
            if style_val == 0:
                desc += f"🖼️ **Dyes and Frame :**\n"
                desc += f"{ticks}md\n"
                desc += f"Current Core   -> ±{naked_effort}\n"
                desc += f"Dye            -> ±{naked_effort + dye_val} [+ {dye_val}]\n"
                desc += f"Frame          -> ±{naked_effort + frame_val} [+ {frame_val}]\n"
                desc += f"Dye & Frame    -> ±{naked_effort + dye_val + frame_val} [+ {dye_val + frame_val}]\n"
                desc += f"Mystic & Frame -> ±{naked_effort + mystic_and_frame} [+ {mystic_and_frame}]\n"
                desc += f"{ticks}\n"

            desc += f"🔢 **S Style + Vanity and Toughness :**\n"
            desc += f"{ticks}md\n"
            desc += f"[ Current Combat Stats ]\n"
            desc += f"Toughness      :: [+{tough_val}]\n"
            desc += f"Vanity         :: [+{vanity_val}]\n\n"
            desc += f"[ Max Possible Effort ]\n"
            desc += f"With S Style   -> ±{naked_effort + mystic_and_frame + tough_val + vanity_val}\n"
            desc += f"{ticks}\n"
            desc += f"*(Note: Values scale from your current core. True vanity caps vary per global character print.)*"

            embed_response = discord.Embed(
                title="Effort Calculator",
                description=desc,
                color=0x2b2d31 # Invisible Discord Background Color
            )
            embed_response.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

            print(f"[Effort Radar] 📊 Math calculated for Base {base_val}! Sending payload...")
            await message.channel.send(embed=embed_response)

        except Exception as e:
            print("\n================== CRASH REPORT ==================")
            traceback.print_exc()
            print(f"[Effort Radar] ❌ FATAL ERROR: {e}")
            print("==================================================\n")

async def setup(bot):
    await bot.add_cog(EffortListener(bot))