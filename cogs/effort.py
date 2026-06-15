import discord
from discord.ext import commands
import re
import random
import traceback

class EffortView(discord.ui.View):
    def __init__(self, mint_core, dye, frame, base_val, current_quality):
        super().__init__(timeout=300)
        self.mint_core = mint_core
        self.dye = dye
        self.frame = frame
        self.base_val = base_val
        self.current_quality = current_quality

    @discord.ui.button(label="Advanced Diagnostics", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticks = chr(96) * 3
        adv_desc = f"**⟡ Identified Baseline:** `{self.base_val} ✧`\n"
        
        if self.current_quality != "Mint":
            adv_desc += f"**⟡ Projected Mint Effort:** `{self.mint_core} ✧` (Currently {self.current_quality})\n"
        else:
            adv_desc += f"**⟡ Current Mint Effort:** `{self.mint_core} ✧`\n"
            
        adv_desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        adv_desc += "**🎨 Cosmetics Optimization:**\n"
        adv_desc += f"{ticks}ini\n"
        adv_desc += f"[ Dye ]          -> {self.mint_core + self.dye} [+ {self.dye}]\n"
        adv_desc += f"[ Frame ]        -> {self.mint_core + self.frame} [+ {self.frame}]\n"
        adv_desc += f"[ Dye & Frame ]  -> {self.mint_core + self.dye + self.frame} [+ {self.dye + self.frame}]\n"
        adv_desc += f"[ Mystic Frame ] -> {self.mint_core + self.frame * 2} [+ {self.frame * 2}]\n"
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
        
        max_optimized = self.mint_core + (self.frame * 2) + self.base_val + max_vanity
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
        
        # Violent text sanitization to completely remove markdown and weird invisible characters
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
                
            print(f"[Effort Radar] ✅ Math Sequence Started! Base Value: {base_val}")

            reaction_emojis = ["🧮", "📈", "⚙️", "💠", "📡", "🧩"]
            try:
                await message.add_reaction(random.choice(reaction_emojis))
            except:
                pass

            def parse_stat(stat_name):
                match = re.search(r'(\d+)\s+\(([S-F])\)\s+' + stat_name, clean_text, re.IGNORECASE)
                if match:
                    return int(match.group(1)), match.group(2).upper()
                return 0, "F"

            _, well_grade = parse_stat("Wellness")
            _, pur_grade = parse_stat("Purity")
            _, quick_grade = parse_stat("Quickness")
            _, grab_grade = parse_stat("Grabber")
            _, drop_grade = parse_stat("Dropper")
            
            effort_match = re.search(r'Effort\s+(\d+)', clean_text, re.IGNORECASE)
            current_effort = int(effort_match.group(1)) if effort_match else base_val

            def get_mint_potential(grade, cap_pct):
                grade_mults = {"S": 1.0, "A": 0.85, "B": 0.70, "C": 0.55, "D": 0.40, "E": 0.25, "F": 0.10}
                return base_val * cap_pct * grade_mults.get(grade, 0.10)
                
            well_mint = get_mint_potential(well_grade, 0.25)
            pur_mint = get_mint_potential(pur_grade, 0.25)
            quick_mint = get_mint_potential(quick_grade, 0.20)
            grab_mint = get_mint_potential(grab_grade, 0.15)
            drop_mint = get_mint_potential(drop_grade, 0.15)
            
            mint_core = round(base_val + well_mint + pur_mint + quick_mint + grab_mint + drop_mint)
            
            ratio = current_effort / mint_core if mint_core > 0 else 1
            if ratio >= 0.95:
                quality = "Mint"
            elif ratio >= 0.80:
                quality = "Excellent"
            elif ratio >= 0.60:
                quality = "Good"
            elif ratio >= 0.40:
                quality = "Poor"
            else:
                quality = "Damaged"

            dye_mod = base_val
            frame_mod = 30 

            ticks = chr(96) * 3
            desc = f"**⟡ Identified Baseline:** `{base_val} ✧`\n"
            if quality != "Mint":
                desc += f"**⟡ Projected Mint Effort:** `{mint_core} ✧` (Currently {quality})\n"
            else:
                desc += f"**⟡ Current Mint Effort:** `{mint_core} ✧`\n"
                
            desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
            desc += "**🎨 Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            desc += f"[ Dye ]          -> {mint_core + dye_mod} [+ {dye_mod}]\n"
            desc += f"[ Frame ]        -> {mint_core + frame_mod} [+ {frame_mod}]\n"
            desc += f"[ Dye & Frame ]  -> {mint_core + dye_mod + frame_mod} [+ {dye_mod + frame_mod}]\n"
            desc += f"[ Mystic Frame ] -> {mint_core + frame_mod * 2} [+ {frame_mod * 2}]\n"
            desc += f"{ticks}"

            embed_response = discord.Embed(
                title="[ EFFORT TELEMETRY LOG ]",
                description=desc,
                color=0x8b0000
            )
            embed_response.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

            view = EffortView(mint_core, dye_mod, frame_mod, base_val, quality)
            
            print("[Effort Radar] 📊 Math calculated! Attempting to send to Discord...")
            await message.channel.send(embed=embed_response, view=view)
            print("[Effort Radar] ✅ MISSION ACCOMPLISHED! Message Sent.")

        except Exception as e:
            print("\n================== CRASH REPORT ==================")
            traceback.print_exc()
            print(f"[Effort Radar] ❌ FATAL ERROR: {e}")
            print("==================================================\n")

async def setup(bot):
    await bot.add_cog(EffortListener(bot))