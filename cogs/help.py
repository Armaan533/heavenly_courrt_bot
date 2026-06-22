import discord
from discord.ext import commands

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Main Menu", 
                description="Return to the index overview.", 
                emoji="🏠"
            ),
            discord.SelectOption(
                label="Service Booths", 
                description="Browse or register as a server companion provider.", 
                emoji="🧪"
            ),
            discord.SelectOption(
                label="Frames Catalog", 
                description="Review catalog values, market rates, and liquid costs.", 
                emoji="🖼️"
            ),
            discord.SelectOption(
                label="Lent List Tracker", 
                description="Track out-lent or borrowed card assets across channels.", 
                emoji="📦"
            ),
            discord.SelectOption(
                label="Card Pricing Engine", 
                description="Value cards using live currency ranges via reactions.", 
                emoji="💳"
            ),
            discord.SelectOption(
                label="Effort Telemetry", 
                description="Calibrate optimization boundaries for workers.", 
                emoji="⚡"
            ),
            discord.SelectOption(
                label="Trading & Live Auctions", 
                description="Build customized ads and bid on premium drops.", 
                emoji="💹"
            ),
        ]
        super().__init__(placeholder="Select a module category to view commands...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(color=0x6b1614)
        selection = self.values[0]

        if selection == "Main Menu":
            embed.title = "<:eight_side_sparkle:1516681364806570105> Heavenly Court Directory"
            embed.description = (
                "Welcome to the server guide index. Select an engine option from the dropdown menu below "
                "to view specific details, command syntaxes, and interaction guidelines.\n\n"
                "**Active Public Modules:**\n"
                "🔹 <:two_flowers:1516684386546880614> **Service Booths** — Provider networks and profiles[cite: 5]\n"
                "🔹 <:for_john:1517226175901208696> **Frames Catalog** — Market values and liquid trade costs[cite: 4]\n"
                "🔹 <:book_ig:1516683126066253844> **Lent List Tracker** — Asset allocation ledgers[cite: 6]\n"
                "🔹 <:for_booster:1517226639438778503> **Card Pricing Engine** — Reaction valuations and smart loops\n"
                "🔹 <:emoji_for_oddny:1517225564023554219> **Effort Telemetry** — Passive workforce optimization matrices[cite: 3]\n"
                "🔹 <:red_lotus:1516679367743377448> **Trading & Live Auctions** — Marketplace generators and bidding[cite: 1, 2]"
            )
            embed.set_footer(text="Select an index option below to proceed.")

        elif selection == "Service Booths":
            embed.title = "<:two_flowers:1516684386546880614> Service Booth System"
            embed.description = (
                "**Available Commands:**\n"
                "• **/services list** — Opens the public directory where you can select categories (Dye Jobs, Frame Testers, Sketchers) to view provider pricing, availability, and image portfolios[cite: 5].\n"
                "• **/services add** — Launches an interactive setup menu to register your workspace profile to the server[cite: 5].\n"
                "• **/services update** — Lets you update your info texts, append new display images, or clear out old galleries[cite: 5].\n"
                "• **/services delete** — Instantly removes your active service listing from server records[cite: 5].\n\n"
                "🎫 **Want to become a provider?**\n"
                "If you want to register as a service provider, please **create a ticket** in the server first to receive the required access role!"
            )

        elif selection == "Frames Catalog":
            embed.title = "<:for_john:1517226175901208696> Frames Catalog & Showroom"
            embed.description = (
                "**Available Commands:**\n"
                "• **/frame menu** — Displays the premium showroom gallery sorted cleanly by frame group classes with built-in page swapping controls[cite: 4].\n"
                "• **/frame lookup <frame name>** — Uses an autocomplete engine to instantly fetch frame information[cite: 4]. Displays a premium image preview, the standard **Market Value**, and its exact **Liquid Cost** requirements[cite: 4]."
            )

        elif selection == "Lent List Tracker":
            embed.title = "<:book_ig:1516683126066253844> Card Ledgers & Lent Lists"
            embed.description = (
                "**Available Commands:**\n"
                "• `,lent [user]` — Accesses a member's tracked out-lent card ledger entries[cite: 6].\n"
                "• `,lent borrowed [user]` — Performs a reverse lookup detailing cards a user is holding from other lenders[cite: 6].\n"
                "• `,lent add <@user>` — Launches a tracker calibration menu[cite: 6]. Run `kci` or `kwi` right after, and the engine will capture the item profile and append it to your active logs[cite: 6].\n"
                "• `,lent remove` — Spawns an interactive selection menu to instantly clear a card tracking profile from your storage disks[cite: 6]."
            )

        elif selection == "Card Pricing Engine":
            embed.title = "<:for_booster:1517226639438778503> Custom Card Pricing Engine"
            embed.description = (
                "**How to Use:**\n"
                "Simply click the 💵 reaction attached underneath any valid Karuta `kci` (Card Info) block. "
                "The bot reads the embed and generates a customized market price matrix tailored exactly to our layout.\n\n"
                "**Key Metrics Evaluated:**\n"
                "• **Standalone Base Price:** Calculated using progressive tax-brackets for low prints to avoid erratic price spikes.\n"
                "• **Extras Pricing:** Factors in precise Frame costs, Normal (+2🎟️) or Mystic (+25🎟️) dye attributes, Inkwell sketches, and Character Identity Aliases (+1🎟️).\n"
                "• **Smart Loop System:** If a character's wishlist is missing, the bot registers a pending order. Running `klu <name>` anywhere in the server updates the master file and automatically prints your price breakdown without clicking again!"
            )

        elif selection == "Effort Telemetry":
            embed.title = "<:emoji_for_oddny:1517225564023554219> Passive Effort Telemetry"
            embed.description = (
                "**How to Trigger:**\n"
                "• Test any card display showing baseline worker properties (`base value` logging text) in chat[cite: 3]. The engine will intercept the stats passively[cite: 3].\n\n"
                "**Interactive Features:**\n"
                "• **Calibration Buttons:** The system appends interactive buttons mapped to card conditions: *Damaged, Poor, Good, Excellent, or Mint*[cite: 3].\n"
                "• **Telemetry Outputs:** Selecting a card quality yields a detailed report itemizing your true base core value without temporary grab/drop additions, ideal cosmetic modifications (Dyes, Frames, Mystics), and maximum performance margins[cite: 3]."
            )

        elif selection == "Trading & Live Auctions":
            embed.title = "<:red_lotus:1516679367743377448> Trade Ads & Contribution Auctions"
            embed.description = (
                "**Automated Ad Generator:**\n"
                "• **/ad create** — Initiates a private ad builder session. Select your trading currency preferences (Tickets, Gems, or Both) and apply a global conversion rate[cite: 1]. Run `k!c`, `k!i`, or `k!bi` to let the bot capture your assets and attach user-customized pricing tags inside automated select menus[cite: 1].\n"
                "• **/ad help** — Reviews the trade ad script building blocks[cite: 1].\n\n"
                "**Live Auctions Integration:**\n"
                "• Click the interactive **Place Bid** button on live items hosted in the auction hub[cite: 2]. Bids are checked against your contribution points, and immediate outbid flags are dispatched via direct messages[cite: 2]."
            )

        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown())


class InteractiveHelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def public_help_command(self, ctx):
        embed = discord.Embed(
            title="<:eight_side_sparkle:1516681364806570105> Heavenly Court Directory",
            description=(
                "Welcome to the server guide index. Select a module category from the dropdown menu below "
                "to view specific details, command syntaxes, and interaction guidelines.\n\n"
                "**Active Public Modules:**\n"
                "🔹 <:two_flowers:1516684386546880614> **Service Booths** — Provider networks and profiles[cite: 5]\n"
                "🔹 <:for_john:1517226175901208696> **Frames Catalog** — Market values and liquid trade costs[cite: 4]\n"
                "🔹 <:book_ig:1516683126066253844> **Lent List Tracker** — Asset allocation ledgers[cite: 6]\n"
                "🔹 <:for_booster:1517226639438778503> **Card Pricing Engine** — Reaction valuations and smart loops\n"
                "🔹 <:emoji_for_oddny:1517225564023554219> **Effort Telemetry** — Passive workforce optimization matrices[cite: 3]\n"
                "🔹 <:red_lotus:1516679367743377448> **Trading & Live Auctions** — Marketplace generators and bidding[cite: 1, 2]"
            ),
            color=0x6b1614
        )
        embed.set_footer(text="Select an index option below to proceed.")
        
        view = HelpMenuView()
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    bot.help_command = None
    await bot.add_cog(InteractiveHelpCog(bot))