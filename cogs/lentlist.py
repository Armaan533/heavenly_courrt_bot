import discord
from discord.ext import commands
import json
import os
import re
import asyncio

DATA_FILE = "lent_data.json"

class LentRemoveSelect(discord.ui.Select):
    def __init__(self, lent_cards, callback_func):
        self.callback_func = callback_func
        options = []
        
        # Discord limits select menus to 25 items max
        for code, info in list(lent_cards.items())[:25]:
            options.append(discord.SelectOption(
                label=f"{info['character']}",
                description=f"Code: {code} | Lent to: {info['lent_to_name']}",
                value=code,
                emoji="📦"
            ))
            
        super().__init__(placeholder="Select a card to remove from list...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.values[0])


class LentRemoveView(discord.ui.View):
    def __init__(self, lent_cards, callback_func):
        super().__init__(timeout=120)
        self.add_item(LentRemoveSelect(lent_cards, callback_func))


class LentListCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.load_data()

    def load_data(self):
        """Loads lent list data from JSON"""
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save_data(self):
        """Saves lent list data to JSON"""
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    @commands.group(invoke_without_command=True, aliases=['lentlist'])
    async def lent(self, ctx):
        """Displays the user's lent list. Triggered by ,lent or ,lentlist"""
        user_id = str(ctx.author.id)
        user_data = self.data.get(user_id, {})

        if not user_data:
            embed = discord.Embed(
                title=f"[ {ctx.author.display_name.upper()}'S LENT LIST ]",
                description="⟡ *Your ledger is currently empty.*\n\nUse `,lent add @user` to start tracking cards!",
                color=0x2b2d31
            )
            embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")
            await ctx.send(embed=embed)
            return

        desc = "━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (code, info) in enumerate(user_data.items(), 1):
            desc += f"**{i}.** `{code}` - **{info['character']}** \n> 📦 Lent to: <@{info['lent_to']}>\n\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━"

        embed = discord.Embed(
            title=f"[ {ctx.author.display_name.upper()}'S LENT LIST ]",
            description=desc,
            color=0x8b0000
        )
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")
        await ctx.send(embed=embed)

    @lent.command(name="add")
    async def add_lent(self, ctx, member: discord.Member):
        """Interactive command to add a card to the lent list"""
        user_id = str(ctx.author.id)
        
        prompt_embed = discord.Embed(
            title="[ LENT TRACKER CALIBRATION ]",
            description=f"⟡ Please run `kci` on the card you lent to **{member.display_name}**.\n\n*(Waiting for Karuta's response in this channel...)*",
            color=0x2b2d31
        )
        prompt_msg = await ctx.send(embed=prompt_embed)

        def check(m):
            if not m.author.bot or "karuta" not in m.author.name.lower():
                return False
            if m.channel != ctx.channel:
                return False
            if not m.embeds:
                return False
            
            embed_dict = str(m.embeds[0].to_dict()).lower()
            if "owner" not in embed_dict and "character" not in embed_dict:
                return False
            return True

        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            
            embed = msg.embeds[0]
            raw_text = " ".join([embed.author.name or "", embed.title or "", embed.description or ""] + [f.name + f.value for f in embed.fields])
            
            code_match = re.search(r'🎴\s*\*\*([a-zA-Z0-9]{5,7})\*\*', raw_text)
            if not code_match:
                code_match = re.search(r'\(\s*([a-zA-Z0-9]{5,7})\s*\)', raw_text) 
            
            if not code_match:
                await prompt_msg.edit(embed=discord.Embed(description="❌ **Error:** Could not identify the card code from that embed. Please try again.", color=0xff0000))
                return
            
            code = code_match.group(1)

            char_match = re.search(r'\*\*([^\*]+)\*\*', embed.description or "")
            character = char_match.group(1).strip() if char_match else "Unknown Character"

            # Save to Database
            if user_id not in self.data:
                self.data[user_id] = {}
            
            self.data[user_id][code] = {
                "character": character,
                "lent_to": str(member.id),
                "lent_to_name": member.display_name
            }
            self.save_data()

            success_embed = discord.Embed(
                title="[ LENT TRACKER UPDATED ]",
                description=f"⟡ Successfully tracked **{character}** (`{code}`)\n> 📦 Lent to: <@{member.id}>",
                color=0x2b2d31
            )
            success_embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")
            await prompt_msg.edit(embed=success_embed)

        except asyncio.TimeoutError:
            await prompt_msg.edit(embed=discord.Embed(description="❌ Request timed out. You took too long to run `kci`.", color=0xff0000))

    @lent.command(name="remove")
    async def remove_lent(self, ctx):
        """Dropdown UI to remove a card from the lent list"""
        user_id = str(ctx.author.id)
        user_data = self.data.get(user_id, {})

        if not user_data:
            await ctx.send("⟡ Your lent list is already empty.")
            return

        async def on_select(interaction: discord.Interaction, selected_code: str):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("This isn't your menu!", ephemeral=True)
                return

            if selected_code in self.data[user_id]:
                character = self.data[user_id][selected_code]['character']
                del self.data[user_id][selected_code]
                self.save_data()

                updated_embed = discord.Embed(
                    title="[ LENT TRACKER MODIFICATION ]",
                    description=f"⟡ **{character}** (`{selected_code}`) has been successfully cleared from your ledger.",
                    color=0x8b0000
                )
                updated_embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")
                await interaction.response.edit_message(embed=updated_embed, view=None)

        view = LentRemoveView(user_data, on_select)
        
        embed = discord.Embed(
            title="[ LENT TRACKER MODIFICATION ]",
            description="⟡ Select a card from the dropdown below to remove it from your lent list.",
            color=0x2b2d31
        )
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(LentListCog(bot))