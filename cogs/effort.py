import discord
from discord.ext import commands
import re
import traceback

class EffortView(discord.ui.View):
    def __init__(self, mint_core, dye, frame, mystic_frame, base_val):
        super().__init__(timeout=300)
        self.mint_core = mint_core
        self.dye = dye
        self.frame = frame
        self.mystic_frame = mystic_frame
        self.base_val = base_val

    @discord.ui.button(label="Advanced Diagnostics", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticks = chr(96) * 3
        
        adv_desc = f"**⟡ Identified Baseline:** `{self.base_val} ✧`\n"
        adv_desc += f"**⟡ Projected Mint Core:** `{self.mint_core} ✧`\n"
        adv_desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        adv_desc += "**🎨 Cosmetics Optimization:**\n"
        adv_desc += f"{ticks}ini\n"
        adv_desc += f"[ Dye ]          -> {self.mint_core + self.dye} [+ {self.dye}]\n"
        adv_desc += f"[ Frame ]        -> {self.mint_core + self.frame} [+ {self.frame}]\n"
        adv_desc += f"[ Dye & Frame ]  -> {self.mint_core + self.dye + self.frame} [+ {self.dye + self.frame}]\n"
        adv_desc += f"[ Mystic Frame ] -> {self.mint_core + self.mystic_frame} [+ {self.mystic_frame}]\n"
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
        
        max_optimized = self.mint_core + self.mystic_frame + self.base_val + max_vanity
        adv_desc += f"[ Maximum Theoretical ]\n"
        adv_desc += f"Max Vanity + S Toughness -> {max_optimized}\n"
        adv_desc += f"{ticks}\n"
        adv_desc += "*( ⚠️ Effort telemetry is currently in testing. Please report any math inconsistencies! )*"
        
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
        
        content_parts = []
        if embed.author and embed.author.name: content_parts.append(embed.author.name)
        if embed.title: content_parts.append(embed.title)
        if embed.description: content_parts.append(embed.description)
        for field in embed.fields:
            content_parts.append(field.name)
            content_parts.append(field.value)
            
        raw_text = " ".join(content_parts)
        
        # Strip all markdown formatting to make reading numbers bulletproof
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

            # Extract combat and cosmetic mods to find the "Naked" core
            style_val, _ = parse_stat("Style")
            tough_val, _ = parse_stat("Toughness")
            vanity_val, _ = parse_stat("Vanity")
            
            effort_match = re.search(r'Effort\s+(\d+)', clean_text, re.IGNORECASE)
            current_effort = int(effort_match.group(1)) if effort_match else base_val
            
            naked_core = current_effort - style_val - tough_val - vanity_val

            # Dynamically scale Damaged/Poor cards up to their 100% Mint potential
            if naked_core < 25:
                mint_core = round(naked_core * 3.5)
            elif naked_core < 50:
                mint_core = round(naked_core * 2.0)
            elif naked_core < 100:
                mint_core = round(naked_core * 1.3)
            else:
                mint_core = naked_core

            # Flawless Karuta Cosmetic Math
            dye_val = base_val
            frame_val = 30
            mystic_dye_val = max(base_val + 10, 30)
            mystic_frame_val = frame_val + mystic_dye_val

            ticks = chr(96) * 3
            
            desc = f"**⟡ Identified Baseline:** `{base_val} ✧`\n"
            desc += f"**⟡ Projected Mint Core:** `{mint_core} ✧`\n"
            desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
            desc += "**🎨 Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            desc += f"[ Dye ]          -> {mint_core + dye_val} [+ {dye_val}]\n"
            desc += f"[ Frame ]        -> {mint_core + frame_val} [+ {frame_val}]\n"
            desc += f"[ Dye & Frame ]  -> {mint_core + dye_val + frame_val} [+ {dye_val + frame_val}]\n"
            desc += f"[ Mystic Frame ] -> {mint_core + mystic_frame_val} [+ {mystic_frame_val}]\n"
            desc += f"{ticks}\n"
            desc += "*( ⚠️ Effort telemetry is currently in testing. Please report any math inconsistencies! )*"

            embed_response = discord.Embed(
                title="[ EFFORT TELEMETRY LOG ]",
                description=desc,
                color=0x8b0000
            )
            embed_response.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

            view = EffortView(mint_core, dye_val, frame_val, mystic_frame_val, base_val)
            
            print(f"[Effort Radar] 📊 Heavenly Court UI Generated for Base {base_val}. Sending...")
            await message.channel.send(embed=embed_response, view=view)

        except Exception as e:
            print("\n================== CRASH REPORT ==================")
            traceback.print_exc()
            print(f"[Effort Radar] ❌ FATAL ERROR: {e}")
            print("==================================================\n")

async def setup(bot):
    await bot.add_cog(EffortListener(bot))