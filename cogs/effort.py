import discord
from discord.ext import commands
import re

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
        
        # Safely extract all text from the embed
        content_parts = []
        if embed.author and embed.author.name: content_parts.append(embed.author.name)
        if embed.title: content_parts.append(embed.title)
        if embed.description: content_parts.append(embed.description)
        for field in embed.fields:
            content_parts.append(field.name)
            content_parts.append(field.value)
            
        raw_text = " ".join(content_parts)
        
        # Strip markdown and invisible characters to make parsing bulletproof
        clean_text = re.sub(r'[*`~_]', ' ', raw_text)
        clean_text = re.sub(r'[^\x20-\x7E]', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text)

        if "base value" not in clean_text.lower():
            return

        try:
            # Isolate the Base Value
            base_match = re.search(r'(\d+)\s+base\s+value', clean_text, re.IGNORECASE)
            if not base_match:
                return
            base_val = int(base_match.group(1))
            
            self.processed_cache.append(message.id)
            if len(self.processed_cache) > 100:
                self.processed_cache.pop(0)

            # Bulletproof stat parser
            def parse_stat(stat_name):
                match = re.search(r'(\d+)\s+\(([SABCDEF])\)\s+' + stat_name, clean_text, re.IGNORECASE)
                return (int(match.group(1)), match.group(2).upper()) if match else (0, "F")

            style_val, style_grade = parse_stat("Style")
            tough_val, _ = parse_stat("Toughness")
            
            # Isolate Current Effort
            effort_match = re.search(r'Effort[^\d]+(\d+)', clean_text, re.IGNORECASE)
            current_effort = int(effort_match.group(1)) if effort_match else base_val

            # THE MASTER FORMULAS (0.9375 = 15/16)
            target_dye = max(1, round(base_val * 0.25))
            target_frame = round(base_val * 0.9375)
            target_mystic = round(base_val * 0.9375)
            
            target_dye_frame = target_dye + target_frame
            target_mystic_frame = target_frame + target_mystic
            
            target_tough = round(base_val * 0.25)
            target_vanity = base_val // 2

            # Calculate exact missing deltas
            dye_delta = max(0, target_dye - style_val)
            frame_delta = max(0, target_frame - style_val)
            dye_frame_delta = max(0, target_dye_frame - style_val)
            mystic_frame_delta = max(0, target_mystic_frame - style_val)

            ticks = chr(96) * 3
            
            # Construct the Heavenly Court UI
            desc = f"⟡ **Identified Baseline:** `{base_val} ✧`\n"
            desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            
            if style_grade == 'S':
                desc += f"[ Max Cosmetics Already Applied ]\n"
            else:
                if style_grade in ['F', 'C', 'A', 'D']:
                    desc += f"[ Dye ]          -> {current_effort + dye_delta} [+ {dye_delta}]\n"
                    desc += f"[ Frame ]        -> {current_effort + frame_delta} [+ {frame_delta}]\n"
                elif style_grade == 'B':
                    if dye_frame_delta > 5:
                        desc += f"; Card currently has Frame OR Mystic Dye applied\n"
                    else:
                        desc += f"; Card currently has Frame AND Regular Dye applied\n"
                
                # Hide Dye & Frame if it's already maxed out
                if dye_frame_delta > 5:
                    desc += f"[ Dye & Frame ]  -> {current_effort + dye_frame_delta} [+ {dye_frame_delta}]\n"
                    
                desc += f"[ Mystic Frame ] -> {current_effort + mystic_frame_delta} [+ {mystic_frame_delta}]\n"
                
            desc += f"{ticks}\n"
            
            # S-Style + Vanity & Toughness Section
            cosmetic_base = (current_effort - style_val) + target_mystic_frame
            d_tough_val = max(1, round(base_val * 0.05)) if base_val >= 20 else 0
            d_vanity_val = max(1, round(base_val * 0.12)) if base_val >= 20 else 0

            desc += "⚙️ **S-Style + Vanity & Toughness:**\n"
            desc += f"{ticks}ini\n"
            desc += f"[ Toughness ]\n"
            desc += f"D Toughness  :: [{d_tough_val}]   -> {cosmetic_base + d_tough_val}\n"
            desc += f"S Toughness  :: [{target_tough}]  -> {cosmetic_base + target_tough}\n\n"
            
            desc += f"[ Vanity ]\n"
            desc += f"D Vanity     :: [0-{d_vanity_val}] -> {cosmetic_base} - {cosmetic_base + d_vanity_val}\n"
            desc += f"Max A Vanity :: [{target_vanity}]  -> {cosmetic_base + target_vanity}\n\n"
            
            desc += f"[ Max Theoretical ]\n"
            desc += f"Max A Vanity + S Tough -> {cosmetic_base + target_tough + target_vanity}\n"
            desc += f"{ticks}\n"
            
            desc += "*( 💡 Pro Tip: Run `k!ci` before running `kwi` to see true Mint projections! )*"

            embed_response = discord.Embed(
                title="[ EFFORT TELEMETRY LOG ]",
                description=desc,
                color=0x8b0000
            )
            embed_response.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

            await message.reply(embed=embed_response, mention_author=False)

        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(EffortListener(bot))