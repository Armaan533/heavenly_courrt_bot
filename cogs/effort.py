import discord
from discord.ext import commands
import re
import traceback

class EffortView(discord.ui.View):
    def __init__(self, naked_effort, dye, frame, mystic, base_val):
        super().__init__(timeout=300)
        self.naked_effort = naked_effort
        self.dye = dye
        self.frame = frame
        self.mystic = mystic
        self.base_val = base_val

    @discord.ui.button(label="Advanced Diagnostics", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticks = chr(96) * 3
        adv_desc = f"**⟡ Identified Baseline:** `{self.base_val} ✧`\n"
        adv_desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        adv_desc += "**🎨 Cosmetics Optimization:**\n"
        adv_desc += f"{ticks}ini\n"
        adv_desc += f"[ Dye ]          -> {self.naked_effort + self.dye} [+ {self.dye}]\n"
        adv_desc += f"[ Frame ]        -> {self.naked_effort + self.frame} [+ {self.frame}]\n"
        adv_desc += f"[ Dye & Frame ]  -> {self.naked_effort + self.dye + self.frame} [+ {self.dye + self.frame}]\n"
        adv_desc += f"[ Mystic Frame ] -> {self.naked_effort + self.mystic} [+ {self.mystic}]\n"
        adv_desc += f"{ticks}\n"
        adv_desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        adv_desc += "**⚙️ S-Style + Vanity & Toughness:**\n"
        adv_desc += f"{ticks}ini\n"
        adv_desc += f"[ Toughness ]\n"
        adv_desc += f"D Toughness  :: [+0]\n"
        adv_desc += f"S Toughness  :: [+{self.base_val}]\n\n"
        
        max_vanity = self.base_val * 2
        adv_desc += f"[ Vanity ]\n"
        adv_desc += f"D Vanity     :: [+0]\n"
        adv_desc += f"Max A Vanity :: [+{max_vanity}]\n\n"
        
        max_optimized = self.naked_effort + self.mystic + self.base_val + max_vanity
        adv_desc += f"[ Maximum Theoretical ]\n"
        adv_desc += f"Max Vanity + S Toughness -> {max_optimized}\n"
        adv_desc += f"{ticks}"
        
        embed = interaction.message.embeds[0]
        embed.description = adv_desc
        
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
        
        # Pull all text directly from embed fields safely
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

            # Check if the card already has cosmetics applied to prevent double stacking math
            style_val, _ = parse_stat("Style")
            
            effort_match = re.search(r'Effort\s+(\d+)', clean_text, re.IGNORECASE)
            current_effort = int(effort_match.group(1)) if effort_match else base_val
            
            # The "Naked" effort strips out current cosmetics so projections are mathematically accurate
            naked_effort = current_effort - style_val

            # Standard Community Cosmetic Deltas
            dye_mod = base_val
            frame_mod = 30 
            mystic_mod = base_val + 40 # Standard S Style scaling

            ticks = chr(96) * 3
            desc = f"**⟡ Identified Baseline:** `{base_val} ✧`\n"
            desc += f"**⟡ Current Total Effort:** `{current_effort} ✧`\n"
            
            if style_val > 0:
                desc += f"*(Note: Card has active cosmetics. Projections below use naked effort of {naked_effort} ✧)*\n"
                
            desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
            desc += "**🎨 Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            desc += f"[ Dye ]          -> {naked_effort + dye_mod} [+ {dye_mod}]\n"
            desc += f"[ Frame ]        -> {naked_effort + frame_mod} [+ {frame_mod}]\n"
            desc += f"[ Dye & Frame ]  -> {naked_effort + dye_mod + frame_mod} [+ {dye_mod + frame_mod}]\n"
            desc += f"[ Mystic Frame ] -> {naked_effort + mystic_mod} [+ {mystic_mod}]\n"
            desc += f"{ticks}"

            embed_response = discord.Embed(
                title="[ EFFORT TELEMETRY LOG ]",
                description=desc,
                color=0x8b0000
            )
            embed_response.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

            view = EffortView(naked_effort, dye_mod, frame_mod, mystic_mod, base_val)
            await message.channel.send(embed=embed_response, view=view)

        except Exception as e:
            print("\n================== CRASH REPORT ==================")
            traceback.print_exc()
            print(f"[Effort Radar] ❌ FATAL ERROR: {e}")
            print("==================================================\n")

async def setup(bot):
    await bot.add_cog(EffortListener(bot))