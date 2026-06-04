import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import time

class AdSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.currency_mode = "Both"
        self.gem_rate = 0
        self.selling_cards_fixed = []
        self.selling_cards_offers = []
        self.selling_cards_custom = []
        self.buying_cards = []
        self.selling_items = []
        self.selling_frames = []

    def format_price(self, tickets: int):
        if self.currency_mode == "Tickets" or self.gem_rate == 0:
            return f"{tickets} 🎟️"
        elif self.currency_mode == "Gems":
            return f"{tickets * self.gem_rate} 💎"
        else:
            return f"{tickets} 🎟️ | {tickets * self.gem_rate} 💎"

def generate_ad_text(session: AdSession):
    lines = []
    
    if session.selling_cards_fixed:
        lines.append("**SELLING CARDS**")
        if session.currency_mode == "Both" and session.gem_rate > 0:
            lines.append(f"[CONVERSION RATE = 1 🎟️ : {session.gem_rate} 💎]")
        for code, name, price in session.selling_cards_fixed:
            lines.append(f"{session.format_price(price)} `{code}` · {name}")
        lines.append("")
            
    if session.selling_cards_offers:
        lines.append("**TAKING OFFER**")
        for code, name in session.selling_cards_offers:
            lines.append(f"`{code}` · {name}")
        lines.append("")
        
    if session.selling_cards_custom:
        lines.append("**CUSTOM NAME SECTION**")
        for text in session.selling_cards_custom:
            lines.append(text)
        lines.append("")
        
    if session.selling_items:
        lines.append("**SELLING ITEMS**")
        for item, price, stock in session.selling_items:
            lines.append(f"{item} {session.format_price(price)} ({stock}x)")
        lines.append("")
        
    if session.selling_frames:
        lines.append("**SELLING FRAMES**")
        for frame, price, stock in session.selling_frames:
            lines.append(f"{frame} {session.format_price(price)} ({stock}x)")
        lines.append("")
        
    if not lines:
        return "Your ad is completely empty!"
        
    return "\n".join(lines)

class CardPriceModal(discord.ui.Modal, title="Set Card Details"):
    price = discord.ui.TextInput(label="Price in Tickets (Leave blank for Offers)", required=False, placeholder="e.g. 10")
    custom_note = discord.ui.TextInput(label="Custom Category (Optional)", required=False, placeholder="e.g. Burn Price, Worker")

    def __init__(self, session, card_code, card_name, view_to_restore):
        super().__init__()
        self.session = session
        self.card_code = card_code
        self.card_name = card_name
        self.view_to_restore = view_to_restore

    async def on_submit(self, interaction: discord.Interaction):
        if self.custom_note.value:
            self.session.selling_cards_custom.append(f"`{self.card_code}` · {self.card_name} - {self.custom_note.value}")
        elif self.price.value:
            try:
                self.session.selling_cards_fixed.append((self.card_code, self.card_name, int(self.price.value.strip())))
            except ValueError:
                return await interaction.response.send_message("❌ Price must be a number.", ephemeral=True)
        else:
            self.session.selling_cards_offers.append((self.card_code, self.card_name))
            
        await interaction.response.edit_message(content=f"✅ Added `{self.card_code}` to ad! Select another or hit Finish.", view=self.view_to_restore)

class ItemPriceModal(discord.ui.Modal, title="Set Item Details"):
    price = discord.ui.TextInput(label="Price in Tickets", placeholder="e.g. 2")
    stock = discord.ui.TextInput(label="Stock Available", placeholder="e.g. 10")

    def __init__(self, session, item_name, is_frame, view_to_restore):
        super().__init__()
        self.session = session
        self.item_name = item_name
        self.is_frame = is_frame
        self.view_to_restore = view_to_restore

    async def on_submit(self, interaction: discord.Interaction):
        try:
            p = int(self.price.value.strip())
            s = int(self.stock.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Must be valid numbers.", ephemeral=True)

        if self.is_frame:
            self.session.selling_frames.append((self.item_name, p, s))
        else:
            self.session.selling_items.append((self.item_name, p, s))
            
        await interaction.response.edit_message(content=f"✅ Added {self.item_name} to ad! Select another or hit Finish.", view=self.view_to_restore)

class KarutaSelectorView(discord.ui.View):
    def __init__(self, session, target_msg, mode="cards"):
        super().__init__(timeout=300)
        self.session = session
        self.target_msg = target_msg
        self.mode = mode
        self.update_options()

    def update_options(self):
        self.clear_items()
        
        if not self.target_msg.embeds: return
        embed = self.target_msg.embeds[0]
        desc = embed.description or ""
        lines = [l for l in desc.split("\n") if "·" in l]
        
        options = []
        for line in lines[:25]:
            parts = [p.strip().replace("*", "").replace("`", "") for p in line.split("·")]
            if not parts: continue
            
            emoji = parts[0].split()[0] if parts[0].split() else ""
            
            if self.mode == "cards":
                code = parts[0].split()[-1] if parts[0].split() else parts[0]
                name = parts[-1]
                options.append(discord.SelectOption(label=f"{code} - {name}"[:100], value=f"{code}||{name}"))
            else:
                name = parts[-1]
                options.append(discord.SelectOption(label=f"{emoji} {name}"[:100], value=f"{emoji}||{name}"))
                
        if not options:
            self.add_item(discord.ui.Button(label="No valid items found on this page.", disabled=True))
            return

        select = discord.ui.Select(placeholder="Select an item to add to your ad...", options=options)
        
        async def select_callback(interaction: discord.Interaction):
            val = select.values[0]
            if self.mode == "cards":
                code, name = val.split("||")
                await interaction.response.send_modal(CardPriceModal(self.session, code, name, self))
            else:
                emoji, name = val.split("||")
                display_name = f"{emoji} {name}" if emoji else name
                await interaction.response.send_modal(ItemPriceModal(self.session, display_name, self.mode == "frames", self))
                
        select.callback = select_callback
        self.add_item(select)
        
        refresh_btn = discord.ui.Button(label="🔄 Refresh Page", style=discord.ButtonStyle.secondary)
        async def refresh_callback(interaction: discord.Interaction):
            try:
                new_msg = await interaction.channel.fetch_message(self.target_msg.id)
                self.target_msg = new_msg
                self.update_options()
                await interaction.response.edit_message(view=self)
            except:
                await interaction.response.send_message("❌ Could not fetch updated message.", ephemeral=True)
        refresh_btn.callback = refresh_callback
        self.add_item(refresh_btn)
        
        finish_btn = discord.ui.Button(label="✅ Finish Scanning", style=discord.ButtonStyle.success)
        async def finish_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="✅ Scanning complete. Return to your Ad Control Panel.", view=None)
        finish_btn.callback = finish_callback
        self.add_item(finish_btn)

class GenericMarketModal(discord.ui.Modal, title="Add Item Details"):
    price = discord.ui.TextInput(label="Price in Tickets", placeholder="e.g. 5")
    stock = discord.ui.TextInput(label="Stock Available", placeholder="e.g. 2500")

    def __init__(self, session, item_name, emoji):
        super().__init__()
        self.session = session
        self.item_name = item_name
        self.emoji = emoji

    async def on_submit(self, interaction: discord.Interaction):
        try:
            p = int(self.price.value.strip())
            s = int(self.stock.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Must be valid numbers.", ephemeral=True)
            
        display_name = f"{self.emoji} {self.item_name}" if self.emoji else self.item_name
        self.session.selling_items.append((display_name, p, s))
        await interaction.response.send_message(f"✅ Added {display_name} to selling items!", ephemeral=True)

class GenericCategoryView(discord.ui.View):
    def __init__(self, session):
        super().__init__()
        self.session = session
        
    @discord.ui.button(label="Gold")
    async def btn_g(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GenericMarketModal(self.session, "Gold", "💰"))
    @discord.ui.button(label="Bits")
    async def btn_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GenericMarketModal(self.session, "Bits", "🪨"))
    @discord.ui.button(label="Droplet")
    async def btn_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GenericMarketModal(self.session, "Droplet", "💧"))
    @discord.ui.button(label="Blessing")
    async def btn_bl(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GenericMarketModal(self.session, "Blessing", "✨"))

class AdMainMenuView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=600)
        self.cog = cog
        self.session = session

    @discord.ui.select(
        placeholder="Select a category to add to...",
        options=[
            discord.SelectOption(label="Scan Cards (Fixed/Offers)", value="cards", emoji="🎴"),
            discord.SelectOption(label="Scan Items", value="items", emoji="📦"),
            discord.SelectOption(label="Scan Frames", value="frames", emoji="🖼️"),
            discord.SelectOption(label="Add Gold/Bits/Droplets/Blessings", value="generic", emoji="💰"),
            discord.SelectOption(label="Custom Requests (Buying)", value="buying", emoji="🛒")
        ]
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        val = select.values[0]
        
        if val in ["cards", "items", "frames"]:
            await interaction.response.send_message("👀 I am watching. Please run `k!c` or `k!i` in this channel now.", ephemeral=True)
            
            def check(m):
                return m.author.id == 646937666251915264 and m.channel.id == interaction.channel.id
            
            try:
                karuta_msg = await self.cog.bot.wait_for('message', check=check, timeout=60.0)
                await interaction.followup.send(
                    "✅ **Karuta Detected!** Navigate to the correct page on Karuta's message above, then use the menu below to add them to your ad.", 
                    view=KarutaSelectorView(self.session, karuta_msg, val), 
                    ephemeral=False
                )
            except asyncio.TimeoutError:
                await interaction.followup.send("❌ Timed out waiting for Karuta.", ephemeral=True)
                
        elif val == "generic":
            await interaction.response.send_message("Which item?", view=GenericCategoryView(self.session), ephemeral=True)
        else:
            await interaction.response.send_message("Feature expanding soon!", ephemeral=True)

    @discord.ui.button(label="📜 Generate & Export Ad", style=discord.ButtonStyle.success, row=1)
    async def export_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ad_text = generate_ad_text(self.session)
        await interaction.response.send_message(f"Here is your compiled ad:\n```\n{ad_text}\n```", ephemeral=True)

class GemRateModal(discord.ui.Modal, title="Set Global Gem Rate"):
    rate = discord.ui.TextInput(label="1 Ticket = How many Gems?", placeholder="e.g. 15")

    def __init__(self, cog, session):
        super().__init__()
        self.cog = cog
        self.session = session

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.session.gem_rate = int(self.rate.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Must be a valid number.", ephemeral=True)
            
        await interaction.response.send_message("✅ Settings saved! Welcome to your Control Panel.", view=AdMainMenuView(self.cog, self.session), ephemeral=True)

class AdSetupView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=120)
        self.cog = cog
        self.session = session

    @discord.ui.select(placeholder="Currency Type", options=[discord.SelectOption(label=c) for c in ["Tickets", "Gems", "Both"]], row=0)
    async def currency_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.session.currency_mode = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Start Building Ad", style=discord.ButtonStyle.primary, row=1)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.session.currency_mode == "Both":
            await interaction.response.send_modal(GemRateModal(self.cog, self.session))
        else:
            await interaction.response.send_message("✅ Settings saved! Welcome to your Control Panel.", view=AdMainMenuView(self.cog, self.session), ephemeral=True)

class AdGeneratorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    ad_group = app_commands.Group(name="ad", description="Trade Ad Generation System")

    @ad_group.command(name="help", description="Learn how to use the Trade Ad Generator")
    async def ad_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✦ . HEAVENLY COURT AD GENERATOR . ✦",
            description="Welcome to the automated Karuta trading matrix.\n\n**How it works:**\n1. Run `/ad create` to open your Control Panel.\n2. Choose your currency preference and global exchange rates.\n3. Select a category (like Cards or Items) and run your `k!c` or `k!i` command.\n4. The bot will perfectly read your Karuta page and give you a dropdown menu to price your items instantly!\n5. Hit **Generate** to export your perfectly formatted ad.",
            color=0x8b0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ad_group.command(name="create", description="Start building a new trade ad")
    async def ad_create(self, interaction: discord.Interaction):
        session = AdSession(interaction.user.id)
        embed = discord.Embed(
            title="🛠️ Ad Configuration",
            description="Configure your base settings before we start adding items.",
            color=0x8b0000
        )
        await interaction.response.send_message(embed=embed, view=AdSetupView(self, session), ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdGeneratorCog(bot))