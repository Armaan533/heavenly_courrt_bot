import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class AdSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.currency_mode = "Both"
        self.gem_rate = 0
        self.selling_cards_fixed = []
        self.selling_cards_offers = []
        self.selling_cards_custom = []
        self.selling_items = []
        self.selling_bits = []
        self.exchanges = []

    def format_price(self, price_str: str):
        try:
            val = float(price_str.split()[0])
            if self.currency_mode == "Tickets" or self.gem_rate == 0:
                return f"{price_str} 🎟️"
            elif self.currency_mode == "Gems":
                return f"{val * self.gem_rate:g} 💎"
            else:
                return f"{price_str} 🎟️ | {val * self.gem_rate:g} 💎"
        except:
            return f"{price_str} 🎟️"

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
        
    for ex in session.exchanges:
        lines.append(ex)
        lines.append("")

    if session.selling_bits:
        lines.append("**SELLING BITS 🌸**")
        for bit in session.selling_bits:
            lines.append(bit)
        lines.append("")
        
    if session.selling_items:
        lines.append("**SELLING ITEMS**")
        for item, price, stock in session.selling_items:
            lines.append(f"{item} = {session.format_price(price)} ({stock})")
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
            self.session.selling_cards_fixed.append((self.card_code, self.card_name, self.price.value.strip()))
        else:
            self.session.selling_cards_offers.append((self.card_code, self.card_name))
            
        await interaction.response.edit_message(content=f"✅ Added `{self.card_code}` to ad!", view=self.view_to_restore)

class ItemPriceModal(discord.ui.Modal, title="Set Item Details"):
    price = discord.ui.TextInput(label="Price in Tickets", placeholder="e.g. 2 or 2.5 each")
    stock = discord.ui.TextInput(label="Stock Available", placeholder="e.g. 10")

    def __init__(self, session, item_name, max_stock, view_to_restore):
        super().__init__()
        self.session = session
        self.item_name = item_name
        self.view_to_restore = view_to_restore
        self.stock.default = str(max_stock)

    async def on_submit(self, interaction: discord.Interaction):
        self.session.selling_items.append((self.item_name, self.price.value.strip(), self.stock.value.strip()))
        await interaction.response.edit_message(content=f"✅ Added {self.item_name} to ad!", view=self.view_to_restore)

class BitStockModal(discord.ui.Modal, title="List Bits"):
    amount = discord.ui.TextInput(label="Amount to list", placeholder="e.g. 5000")
    
    def __init__(self, session, bit_name, max_stock, view_to_restore):
        super().__init__()
        self.session = session
        self.bit_name = bit_name
        self.view_to_restore = view_to_restore
        self.amount.default = str(max_stock)
        
    async def on_submit(self, interaction: discord.Interaction):
        self.session.selling_bits.append(f"{self.amount.value.strip()} · {self.bit_name}")
        await interaction.response.edit_message(content=f"✅ Added {self.bit_name} to ad!", view=self.view_to_restore)

class KarutaSelectorView(discord.ui.View):
    def __init__(self, cog, session, target_msg, mode="cards"):
        super().__init__(timeout=300)
        self.cog = cog
        self.session = session
        self.target_msg = target_msg
        self.mode = mode
        self.update_options()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message("❌ This scanning session belongs to someone else.", ephemeral=True)
            return False
        return True

    def update_options(self):
        self.clear_items()
        
        if not self.target_msg.embeds: return
        embed = self.target_msg.embeds[0]
        desc = embed.description or ""
        lines = [l for l in desc.split("\n") if "·" in l]
        
        options = []
        for line in lines[:25]:
            parts = [p.strip().replace("*", "").replace("`", "") for p in line.split("·")]
            if len(parts) < 2: continue
            
            if self.mode == "cards":
                code = parts[0].split()[-1] if parts[0].split() else parts[0]
                name = parts[-1]
                options.append(discord.SelectOption(label=f"{code} - {name}"[:100], value=f"{code}||{name}"))
            else:
                first_part = parts[0].split()
                if len(first_part) > 1:
                    emoji = first_part[0]
                    stock = first_part[1].replace(",", "")
                else:
                    emoji = ""
                    stock = first_part[0].replace(",", "")
                    
                name = parts[-1]
                val_string = f"{emoji}||{name}||{stock}"
                display_label = f"{emoji} {name} (x{stock})" if emoji else f"{name} (x{stock})"
                options.append(discord.SelectOption(label=display_label[:100], value=val_string[:100]))
                
        if not options:
            self.add_item(discord.ui.Button(label="No valid items found on this page.", disabled=True))
            return

        select = discord.ui.Select(placeholder="Select an item to add to your ad...", options=options)
        
        async def select_callback(interaction: discord.Interaction):
            val = select.values[0]
            if self.mode == "cards":
                code, name = val.split("||")
                await interaction.response.send_modal(CardPriceModal(self.session, code, name, self))
            elif self.mode == "bits":
                emoji, name, stock = val.split("||")
                await interaction.response.send_modal(BitStockModal(self.session, name, stock, self))
            else:
                emoji, name, stock = val.split("||")
                display_name = f"{emoji} {name}" if emoji else name
                await interaction.response.send_modal(ItemPriceModal(self.session, display_name, stock, self))
                
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
            await interaction.response.edit_message(content="✅ Scanning complete.", view=None)
            await interaction.followup.send("🛠️ **Ad Control Panel**", view=AdMainMenuView(self.cog, self.session), ephemeral=True)
        finish_btn.callback = finish_callback
        self.add_item(finish_btn)

class ManualItemModal(discord.ui.Modal, title="Add Manual Item"):
    name = discord.ui.TextInput(label="Item Name", placeholder="e.g. Work Permit, Generosity")
    emoji = discord.ui.TextInput(label="Emoji (Optional)", placeholder="e.g. 📜, ✨", required=False)
    price = discord.ui.TextInput(label="Price in Tickets", placeholder="e.g. 5")
    stock = discord.ui.TextInput(label="Stock", placeholder="e.g. 10")
    
    def __init__(self, cog, session):
        super().__init__()
        self.cog = cog
        self.session = session
        
    async def on_submit(self, interaction: discord.Interaction):
        display = f"{self.emoji.value.strip()} {self.name.value.strip()}" if self.emoji.value.strip() else self.name.value.strip()
        self.session.selling_items.append((display, self.price.value.strip(), self.stock.value.strip()))
        await interaction.response.edit_message(content=f"✅ Added {display}!", view=None)
        await interaction.followup.send("🛠️ **Ad Control Panel**", view=AdMainMenuView(self.cog, self.session), ephemeral=True)

class TicketGemModal(discord.ui.Modal, title="Ticket/Gem Exchange"):
    selling = discord.ui.TextInput(label="Type 'Tickets' or 'Gems' to sell", default="Tickets")
    rate = discord.ui.TextInput(label="Rate (How many Gems per Ticket?)", placeholder="e.g. 20")
    stock = discord.ui.TextInput(label="Stock Available", placeholder="e.g. 5000")
    
    def __init__(self, cog, session):
        super().__init__()
        self.cog = cog
        self.session = session
        
    async def on_submit(self, interaction: discord.Interaction):
        if self.selling.value.strip().lower() == "tickets":
            text = f"**SELLING TICKETS 🎟️ | BUYING GEMS 💎**\n{self.rate.value.strip()} 💎 = 1 🎟️\nSTOCK : {self.stock.value.strip()} 🎟️"
        else:
            text = f"**SELLING GEMS 💎 | BUYING TICKETS 🎟️**\n{self.rate.value.strip()} 💎 = 1 🎟️\nSTOCK : {self.stock.value.strip()} 💎"
        self.session.exchanges.append(text)
        await interaction.response.edit_message(content="✅ Exchange added!", view=None)
        await interaction.followup.send("🛠️ **Ad Control Panel**", view=AdMainMenuView(self.cog, self.session), ephemeral=True)

class GoldExchangeModal(discord.ui.Modal, title="Gold Exchange"):
    rate = discord.ui.TextInput(label="Rate (Gold per Ticket)", placeholder="e.g. 2600")
    stock = discord.ui.TextInput(label="Stock Available", placeholder="e.g. 50000")
    
    def __init__(self, cog, session):
        super().__init__()
        self.cog = cog
        self.session = session
        
    async def on_submit(self, interaction: discord.Interaction):
        text = f"**SELLING GOLD 💰**\n{self.rate.value.strip()} 💰 : 1 🎟️\nSTOCK : {self.stock.value.strip()} 💰"
        self.session.exchanges.append(text)
        await interaction.response.edit_message(content="✅ Exchange added!", view=None)
        await interaction.followup.send("🛠️ **Ad Control Panel**", view=AdMainMenuView(self.cog, self.session), ephemeral=True)

class BitsRateModal(discord.ui.Modal, title="Bits Exchange Rate"):
    rate = discord.ui.TextInput(label="Rate (Bits per Ticket)", placeholder="e.g. 2000")
    
    def __init__(self, cog, session):
        super().__init__()
        self.cog = cog
        self.session = session
        
    async def on_submit(self, interaction: discord.Interaction):
        gem_calc = self.session.gem_rate if self.session.gem_rate > 0 else "XX"
        text = f"**BITS RATE**\n{self.rate.value.strip()} Bits = 1 🎟️ : {gem_calc} 💎"
        self.session.exchanges.append(text)
        await interaction.response.edit_message(content="✅ Bits rate added!", view=None)
        await interaction.followup.send("🛠️ **Ad Control Panel**", view=AdMainMenuView(self.cog, self.session), ephemeral=True)

class ExchangeCategoryView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=300)
        self.cog = cog
        self.session = session
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message("❌ This session belongs to someone else.", ephemeral=True)
            return False
        return True
        
    @discord.ui.button(label="Ticket / Gem Exchange")
    async def btn_t(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketGemModal(self.cog, self.session))
    @discord.ui.button(label="Gold Exchange")
    async def btn_g(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GoldExchangeModal(self.cog, self.session))
    @discord.ui.button(label="Bits Rate")
    async def btn_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BitsRateModal(self.cog, self.session))

class AdMainMenuView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=600)
        self.cog = cog
        self.session = session

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message("❌ This session belongs to someone else.", ephemeral=True)
            return False
        return True

    @discord.ui.select(
        placeholder="Select a category to add to...",
        options=[
            discord.SelectOption(label="Scan Cards", value="cards", emoji="🎴", description="Run k!c to add cards"),
            discord.SelectOption(label="Scan Inventory", value="items", emoji="📦", description="Run k!i to add items/frames"),
            discord.SelectOption(label="Scan Bits", value="bits", emoji="🪨", description="Run k!bi to add bits"),
            discord.SelectOption(label="Add Market Exchanges", value="exchanges", emoji="💹", description="Rates for Gold/Tickets/Gems"),
            discord.SelectOption(label="Add Manual Item", value="manual", emoji="✍️", description="For Blessings or un-scannable items")
        ]
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        val = select.values[0]
        
        if val in ["cards", "items", "bits"]:
            cmd = "k!c" if val == "cards" else "k!i" if val == "items" else "k!bi"
            await interaction.response.edit_message(content=f"👀 I am watching. Please run `{cmd}` in this channel now.", view=None)
            
            def check(m):
                return m.author.id == 646937666251915264 and m.channel.id == interaction.channel.id and len(m.embeds) > 0
            
            try:
                karuta_msg = await self.cog.bot.wait_for('message', check=check, timeout=60.0)
                await interaction.followup.send(
                    f"✅ **Karuta Detected!** Navigate to the correct page on Karuta's message above, then use the menu below to add them to your ad.", 
                    view=KarutaSelectorView(self.cog, self.session, karuta_msg, val), 
                    ephemeral=False
                )
            except asyncio.TimeoutError:
                await interaction.followup.send("❌ Timed out waiting for Karuta. Run `/ad create` again.", ephemeral=True)
                
        elif val == "exchanges":
            await interaction.response.edit_message(content="Select an exchange to configure:", view=ExchangeCategoryView(self.cog, self.session))
        elif val == "manual":
            await interaction.response.send_modal(ManualItemModal(self.cog, self.session))

    @discord.ui.button(label="📜 Generate & Export Ad", style=discord.ButtonStyle.success, row=1)
    async def export_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ad_text = generate_ad_text(self.session)
        await interaction.response.edit_message(content=f"Here is your compiled ad:\n```\n{ad_text}\n```", view=None)

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
            
        await interaction.response.edit_message(content="✅ Settings saved!", view=None)
        await interaction.followup.send("🛠️ **Ad Control Panel**", view=AdMainMenuView(self.cog, self.session), ephemeral=True)

class AdSetupView(discord.ui.View):
    def __init__(self, cog, session):
        super().__init__(timeout=120)
        self.cog = cog
        self.session = session

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message("❌ This session belongs to someone else.", ephemeral=True)
            return False
        return True

    @discord.ui.select(placeholder="Currency Type", options=[discord.SelectOption(label=c) for c in ["Tickets", "Gems", "Both"]], row=0)
    async def currency_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.session.currency_mode = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Start Building Ad", style=discord.ButtonStyle.primary, row=1)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.session.currency_mode == "Both":
            await interaction.response.send_modal(GemRateModal(self.cog, self.session))
        else:
            await interaction.response.edit_message(content="✅ Settings saved!", view=None)
            await interaction.followup.send("🛠️ **Ad Control Panel**", view=AdMainMenuView(self.cog, self.session), ephemeral=True)

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