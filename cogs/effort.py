import discord
from discord.ext import commands
import re
import traceback

class EffortView(discord.ui.View):
    def __init__(self, base_val, current_effort, naked_effort, pure_core, style_val, style_grade, style_str, tough_val, vanity_val, dye_val, frame_val, dye_frame_val, mystic_frame_val):
        super().__init__(timeout=300)
        self.base_val = base_val
        self.current_effort = current_effort
        self.naked_effort = naked_effort
        self.pure_core = pure_core
        self.style_val = style_val
        self.style_grade = style_grade
        self.style_str = style_str
        self.tough_val = tough_val
        self.vanity_val = vanity_val
        self.dye_val = dye_val
        self.frame_val = frame_val
        self.dye_frame_val = dye_frame_val
        self.mystic_frame_val = mystic_frame_val

    @discord.ui.button(label="Advanced Diagnostics", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticks = chr(96) * 3
        
        desc = f"**⟡ Identified Baseline:** `{self.base_val} ✧`\n"
        desc += f"**⟡ Current Total Effort:** `{self.current_effort} ✧`\n"
        if self.style_val > 0:
            desc += f"**⟡ Style Applied:** `{self.style_str}`\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"

        if self.style_grade == 'S':
            desc += "**🎨 Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            desc += f"[ Max Cosmetics Already Applied ]\n"
            desc += f"{ticks}\n"
        else:
            desc += "**🎨 Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            if self.style_grade in ['F', 'C', 'A']:
                desc += f"[ Dye ]          -> {self.naked_effort + self.dye_val} [{(self.naked_effort + self.dye_val) - self.current_effort:+d}]\n"
                desc += f"[ Frame ]        -> {self.naked_effort + self.frame_val} [{(self.naked_effort + self.frame_val) - self.current_effort:+d}]\n"
            
            desc += f"[ Dye & Frame ]  -> {self.naked_effort + self.dye_frame_val} [{(self.naked_effort + self.dye_frame_val) - self.current_effort:+d}]\n"
            desc += f"[ Mystic Frame ] -> {self.naked_effort + self.mystic_frame_val} [{(self.naked_effort + self.mystic_frame_val) - self.current_effort:+d}]\n"
            desc += f"{ticks}\n"

        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += "**⚙️ S-Style + Vanity & Toughness:**\n"
        desc += f"{ticks}ini\n"
        desc += f"[ Toughness ]\n"
        desc += f"Current Toughness :: [+{self.tough_val}]\n"
        desc += f"S-Tier Toughness  :: [+{self.base_val}]\n\n"
        
        max_vanity = self.base_val * 2
        desc += f"[ Vanity ]\n"
        desc += f"Current Vanity    :: [+{self.vanity_val}]\n"
        desc += f"Max A-Tier Vanity :: [+{max_vanity}]\n\n"
        
        max_optimized = self.pure_core + self.mystic_frame_val + self.base_val + max_vanity
        desc += f"[ Maximum Theoretical ]\n"
        desc += f"Max Vanity + S Toughness -> {max_optimized}\n"
        desc += f"{ticks}\n"
        desc += "*(Note: If your card is High-Printed, ignore the Max A Vanity projection.)*\n"
        
        embed = interaction.message.embeds[0]
        embed.description = desc
        
        button.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

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
        
        content_parts = []
        if embed.author and embed.author.name: content_parts.append(embed.author.name)
        if embed.title: content_parts.append(embed.title)
        if embed.description: content_parts.append(embed.description)
        for field in embed.fields:
            content_parts.append(field.name)
            content_parts.append(field.value)
            
        raw_text = " ".join(content_parts)
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

            style_val, style_grade = parse_stat("Style")
            tough_val, tough_grade = parse_stat("Toughness")
            vanity_val, vanity_grade = parse_stat("Vanity")
            
            effort_match = re.search(r'Effort\s+(\d+)', clean_text, re.IGNORECASE)
            current_effort = int(effort_match.group(1)) if effort_match else base_val
            
            naked_effort = current_effort - style_val
            pure_core = naked_effort - tough_val - vanity_val

            style_str = "None"
            if style_grade == 'D': style_str = "Regular Dye Only"
            elif style_grade == 'B': style_str = "Frame OR Mystic Dye"
            elif style_grade == 'S': style_str = "Mystic & Frame (Maxed)"
            elif style_grade in ['F', 'C', 'A']: style_str = "None"
            else: style_str = f"Custom (Grade {style_grade})"

            dye_val = base_val
            frame_val = 30
            mystic_frame_val = max(base_val + 10, 30) + 30
            dye_frame_val = dye_val + frame_val

            ticks = chr(96) * 3
            desc = f"**⟡ Identified Baseline:** `{base_val} ✧`\n"
            desc += f"**⟡ Current Total Effort:** `{current_effort} ✧`\n"
            if style_val > 0:
                desc += f"**⟡ Style Applied:** `{style_str}`\n"
            desc += "━━━━━━━━━━━━━━━━━━━━━━\n"

            if style_grade == 'S':
                desc += "**🎨 Cosmetics Optimization:**\n"
                desc += f"{ticks}ini\n"
                desc += f"[ Max Cosmetics Already Applied ]\n"
                desc += f"{ticks}\n"
            else:
                desc += "**🎨 Cosmetics Optimization:**\n"
                desc += f"{ticks}ini\n"
                if style_grade in ['F', 'C', 'A']:
                    desc += f"[ Dye ]          -> {naked_effort + dye_val} [{(naked_effort + dye_val) - current_effort:+d}]\n"
                    desc += f"[ Frame ]        -> {naked_effort + frame_val} [{(naked_effort + frame_val) - current_effort:+d}]\n"
                
                desc += f"[ Dye & Frame ]  -> {naked_effort + dye_frame_val} [{(naked_effort + dye_frame_val) - current_effort:+d}]\n"
                desc += f"[ Mystic Frame ] -> {naked_effort + mystic_frame_val} [{(naked_effort + mystic_frame_val) - current_effort:+d}]\n"
                desc += f"{ticks}\n"

            desc += "*( ⚠️ Effort telemetry is currently in testing. Please report any math inconsistencies! )*"

            embed_response = discord.Embed(
                title="[ EFFORT TELEMETRY LOG ]",
                description=desc,
                color=0x8b0000
            )
            embed_response.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

            view = EffortView(base_val, current_effort, naked_effort, pure_core, style_val, style_grade, style_str, tough_val, vanity_val, dye_val, frame_val, dye_frame_val, mystic_frame_val)
            
            print(f"[Effort Radar] 📊 Heavenly Court UI Generated for Base {base_val}. Sending silently...")
            await message.channel.send(embed=embed_response, view=view)

        except Exception as e:
            print("\n================== CRASH REPORT ==================")
            traceback.print_exc()
            print(f"[Effort Radar] ❌ FATAL ERROR: {e}")
            print("==================================================\n")

async def setup(bot):
    await bot.add_cog(EffortListener(bot))