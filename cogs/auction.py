import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import timedelta

from utils.database import (
    get_points, remove_points, add_points, 
    is_auction_winner, add_auction_winner, remove_auction_winner, get_auction_winners, clear_auction_winners
)
from constants import *

CRIMSON_RED = 0x8b0000 
CUSTOM_EMOJI_UI = "<:eight_side_sparkle:1516681364806570105>"
CUSTOM_EMOJI_TITLE = "<:red_lotus:1516679367743377448>"
CUSTOM_EMOJI_TIME = "<:celestial_hourglass:1516684938509029396>"

class BidModal(discord.ui.Modal, title="Place Your Bid"):
    def __init__(self, cog):
        super().__init__()
        state = cog.state
        min_next = state["current_bid"] + state["bid_interval"] if state["current_bid"] > 0 else state["min_bid"]
        self.cog = cog
        
        self.bid_input = discord.ui.TextInput(
            label=f"Your bid (minimum: {min_next} pts)",
            placeholder="Enter your bid amount...",
            min_length=1,
            max_length=10
        )
        self.add_item(self.bid_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.process_bid(interaction, self.bid_input.value)

class AuctionView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Place Bid", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji.from_str(CUSTOM_EMOJI_UI), custom_id="auction_bid")
    async def place_bid(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cog.state["active"]:
            return await interaction.response.send_message("No active auction right now.", ephemeral=True)
            
        if await is_auction_winner(interaction.user.id):
            return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} You've already won an item recently — you cannot bid again until the winner list is reset.", ephemeral=True)
            
        await interaction.response.send_modal(BidModal(self.cog))

class AuctionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bid_lock = asyncio.Lock()
        self.state = {
            "active":           False,
            "type":             None, 
            "item":             None, 
            "current_bid":      0,
            "current_bidder":   None,
            "bid_interval":     10,
            "min_bid":          50,
            "end_time":         None,
            "message":          None,
            "channel":          None,
            "thumbnail_url":    None,
            "bottom_image_url": None,
            "card_image_url":   None, 
            "card_description": None, 
        }
        self.timer_task = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return

        s = self.state
        if not s["active"] or s.get("type") != "Card":
            return
        if not s["channel"] or message.channel.id != s["channel"].id:
            return

        if message.author.id == 432610292342587392 or message.author.name.lower() == "karuta":
            if message.embeds:
                karuta_embed = message.embeds[0]
                updated = False
                
                char_name = karuta_embed.author.name if karuta_embed.author else karuta_embed.title
                if char_name:
                    s["item"] = char_name
                    updated = True

                if karuta_embed.image and karuta_embed.image.url:
                    s["card_image_url"] = karuta_embed.image.url
                    updated = True
                
                if karuta_embed.description:
                    s["card_description"] = karuta_embed.description
                    updated = True
                    
                if updated and s["message"]:
                    await s["message"].edit(embed=self.make_embed())

    def make_embed(self) -> discord.Embed:
        s = self.state
        
        if s.get("type") == "Card":
            embed = discord.Embed(title=f"{CUSTOM_EMOJI_TITLE} Heavenly Court Card Auction {CUSTOM_EMOJI_TITLE}", color=CRIMSON_RED)
            desc = f"### 🃏 {s['item']}"
            
            if s.get("card_description"):
                desc += f"\n\n{s['card_description']}"
            else:
                desc += "\n*(Waiting for card drop...)*"
                
            embed.description = desc
            
            if s.get("card_image_url"):
                embed.set_image(url=s["card_image_url"])
            elif s.get("bottom_image_url"):
                embed.set_image(url=s["bottom_image_url"])
                
        else:
            embed = discord.Embed(title=f"{CUSTOM_EMOJI_TITLE} Heavenly Court Item Auction {CUSTOM_EMOJI_TITLE}", color=CRIMSON_RED)
            embed.description = f"### 🎁 {s['item']}"
            if s.get("bottom_image_url"):
                embed.set_image(url=s["bottom_image_url"])
        
        if s.get("thumbnail_url"):
            embed.set_thumbnail(url=s["thumbnail_url"])
        
        bid_text = f"**{s['current_bid']}** pts" if s["current_bid"] > 0 else "No bids yet!"
        embed.add_field(name="💰 Current Highest Bid", value=bid_text, inline=False)
        
        bidder = s["current_bidder"].mention if s["current_bidder"] else "—"
        embed.add_field(name="👑 Highest Bidder", value=bidder, inline=True)
        
        if s["end_time"]:
            unix_time = int(s["end_time"].timestamp())
            embed.add_field(name=f"{CUSTOM_EMOJI_TIME} Ends In", value=f"<t:{unix_time}:R>", inline=True)
            
        embed.add_field(
            name="📈 Bidding Rules", 
            value=f"**Starting Bid:** {s['min_bid']} pts\n**Minimum Raise:** +{s['bid_interval']} pts", 
            inline=False
        )

        embed.set_footer(text="Heavenly Court ✦ Bids are final once placed")
        return embed

    async def auction_timer(self, duration_seconds: int):
        try:
            await asyncio.sleep(duration_seconds)
            if self.state["active"]:
                await self.end_auction()
        except asyncio.CancelledError:
            pass

    async def end_auction(self):
        s = self.state
        s["active"] = False
        channel = s["channel"]
        item = s["item"]
        
        disabled_view = discord.ui.View()
        ended_button = discord.ui.Button(label="Auction Ended", style=discord.ButtonStyle.secondary, emoji="🔒", disabled=True)
        disabled_view.add_item(ended_button)
        
        if s["current_bidder"]:
            winner = s["current_bidder"]
            bid = s["current_bid"]
            
            try:
                await remove_points(winner.id, bid)
            except ValueError:
                await add_points(winner.id, -bid)
                
            await add_auction_winner(winner.id)
            
            desc = ""
            if s.get("type") == "Card":
                desc = f"### 🃏 {item}"
                if s.get("card_description"):
                    desc += f"\n{s['card_description']}"
                desc += f"\n\n🎉 Won by {winner.mention} for **{bid}** pts!"
            else:
                desc = f"### 🎁 {item}\n🎉 Won by {winner.mention} for **{bid}** pts!"
            
            end_embed = discord.Embed(title=f"{CUSTOM_EMOJI_TITLE} Auction Ended!", description=desc, color=CRIMSON_RED)
            
            if s.get("thumbnail_url"): end_embed.set_thumbnail(url=s["thumbnail_url"])
            if s.get("card_image_url"): end_embed.set_image(url=s["card_image_url"])
            elif s.get("bottom_image_url"): end_embed.set_image(url=s["bottom_image_url"])

            if s["message"]:
                await s["message"].edit(embed=end_embed, view=disabled_view)
                
            await channel.send(
                f"🎉 {winner.mention} won **{item}** for **{bid}** contribution points!\n"
                f"Please open a ticket to claim your prize. {CUSTOM_EMOJI_TITLE}"
            )
        else:
            desc = ""
            if s.get("type") == "Card":
                desc = f"### 🃏 {item}"
                if s.get("card_description"):
                    desc += f"\n{s['card_description']}"
                desc += f"\n\nReceived no bids."
            else:
                desc = f"### 🎁 {item}\nReceived no bids."
                
            end_embed = discord.Embed(title=f"{CUSTOM_EMOJI_TITLE} Auction Ended — No Bids", description=desc, color=0x36393f)
            
            if s.get("thumbnail_url"): end_embed.set_thumbnail(url=s["thumbnail_url"])
            if s.get("card_image_url"): end_embed.set_image(url=s["card_image_url"])
            elif s.get("bottom_image_url"): end_embed.set_image(url=s["bottom_image_url"])

            if s["message"]:
                await s["message"].edit(embed=end_embed, view=disabled_view)
            await channel.send(f"The auction for **{item}** ended with no bids.")

        self.state.update({"type": None, "item": None, "message": None, "thumbnail_url": None, "bottom_image_url": None, "card_image_url": None, "card_description": None})

    async def process_bid(self, interaction: discord.Interaction, bid_str: str):
        async with self.bid_lock:
            s = self.state
            if not s["active"]:
                return await interaction.response.send_message("No active auction right now.", ephemeral=True)
                
            if await is_auction_winner(interaction.user.id):
                return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} You've already won an item recently.", ephemeral=True)
                
            try: bid = int(bid_str.strip())
            except ValueError: return await interaction.response.send_message("Please enter a valid number.", ephemeral=True)
                
            min_next = s["current_bid"] + s["bid_interval"] if s["current_bid"] > 0 else s["min_bid"]
            if bid < min_next:
                return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Minimum bid is **{min_next}** pts.", ephemeral=True)
                
            user_pts = await get_points(interaction.user.id)
            if user_pts < bid:
                return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Not enough points. You have **{user_pts}** pts.", ephemeral=True)
                
            previous_bidder = s["current_bidder"]
            s["current_bid"] = bid
            s["current_bidder"] = interaction.user
            
            time_remaining = (s["end_time"] - discord.utils.utcnow()).total_seconds()
            if time_remaining < 60:
                s["end_time"] = discord.utils.utcnow() + timedelta(seconds=60)
                if self.timer_task: self.timer_task.cancel()
                self.timer_task = asyncio.create_task(self.auction_timer(60))
                
                if s["channel"]:
                    snipe_embed = discord.Embed(description=f"{CUSTOM_EMOJI_TIME} **Anti-Snipe Triggered!** Timer extended by 60 seconds.", color=CRIMSON_RED)
                    warn_msg = await s["channel"].send(embed=snipe_embed)
                    await warn_msg.delete(delay=10) 

            if s["message"]: await s["message"].edit(embed=self.make_embed())
            await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Bid of **{bid}** pts placed successfully!", ephemeral=True)
            
            if previous_bidder and previous_bidder.id != interaction.user.id:
                outbid_embed = discord.Embed(title="⚠️ You've been outbid!", description=f"You were outbid on **{s['item']}**! New highest bid is **{bid} pts**.", color=CRIMSON_RED)
                try: await previous_bidder.send(embed=outbid_embed)
                except discord.Forbidden:
                    if s["channel"]:
                        warn_msg = await s["channel"].send(f"⚠️ {previous_bidder.mention}, you were just outbid on **{s['item']}**!")
                        await warn_msg.delete(delay=10)

    auction_group = app_commands.Group(name="auction", description="Manage the item auction system")

    # 1. NEW COMMAND: AUCTION CARD (No item name requested!)
    @auction_group.command(name="card", description="Start a new Karuta Card auction")
    @app_commands.describe(
        min_bid="Starting minimum bid",
        interval="Minimum interval to raise bids",
        channel="Optional: Select the channel to post the auction in",
        hours="Optional: How many hours the auction lasts",
        minutes="Optional: How many minutes the auction lasts",
        thumbnail="Optional: Upload an image for the top right corner",
        bottom_image="Optional: Upload a large image for the bottom"
    )
    @app_commands.default_permissions(administrator=True)
    async def auction_card(self, interaction: discord.Interaction, min_bid: int, interval: int, channel: discord.TextChannel = None, hours: int = 0, minutes: int = 0, thumbnail: discord.Attachment = None, bottom_image: discord.Attachment = None):
        if self.state["active"]:
            return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} An auction is already running.", ephemeral=True)

        total_minutes = (hours * 60) + minutes
        if total_minutes <= 0: return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Duration must be > 0.", ephemeral=True)

        target_channel = channel or interaction.guild.get_channel(AUCTION_CHANNEL_ID)
        if not target_channel: return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Channel not found.", ephemeral=True)

        self.state.update({
            "active": True, "type": "Card", "item": "Pending Karuta Drop...", 
            "current_bid": 0, "current_bidder": None, "bid_interval": interval, "min_bid": min_bid,
            "end_time": discord.utils.utcnow() + timedelta(minutes=total_minutes), "channel": target_channel,
            "thumbnail_url": thumbnail.url if thumbnail else None, "bottom_image_url": bottom_image.url if bottom_image else None, 
            "card_image_url": None, "card_description": None,
        })

        msg = await target_channel.send(embed=self.make_embed(), view=AuctionView(self))
        self.state["message"] = msg
        if self.timer_task: self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.auction_timer(total_minutes * 60))

        await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Card Auction started in {target_channel.mention}!\n👉 **Drop the card using `k!v` in the channel so the bot can grab its details!**", ephemeral=True)

    # 2. NEW COMMAND: AUCTION ITEM (Requires an item name)
    @auction_group.command(name="item", description="Start a new custom Item auction")
    @app_commands.describe(
        item_name="The name of the item being auctioned",
        min_bid="Starting minimum bid",
        interval="Minimum interval to raise bids",
        channel="Optional: Select the channel to post the auction in",
        hours="Optional: How many hours the auction lasts",
        minutes="Optional: How many minutes the auction lasts",
        thumbnail="Optional: Upload an image for the top right corner",
        bottom_image="Optional: Upload a large image for the bottom"
    )
    @app_commands.default_permissions(administrator=True)
    async def auction_item(self, interaction: discord.Interaction, item_name: str, min_bid: int, interval: int, channel: discord.TextChannel = None, hours: int = 0, minutes: int = 0, thumbnail: discord.Attachment = None, bottom_image: discord.Attachment = None):
        if self.state["active"]:
            return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} An auction is already running.", ephemeral=True)

        total_minutes = (hours * 60) + minutes
        if total_minutes <= 0: return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Duration must be > 0.", ephemeral=True)

        target_channel = channel or interaction.guild.get_channel(AUCTION_CHANNEL_ID)
        if not target_channel: return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Channel not found.", ephemeral=True)

        self.state.update({
            "active": True, "type": "Item", "item": item_name, 
            "current_bid": 0, "current_bidder": None, "bid_interval": interval, "min_bid": min_bid,
            "end_time": discord.utils.utcnow() + timedelta(minutes=total_minutes), "channel": target_channel,
            "thumbnail_url": thumbnail.url if thumbnail else None, "bottom_image_url": bottom_image.url if bottom_image else None, 
            "card_image_url": None, "card_description": None,
        })

        msg = await target_channel.send(embed=self.make_embed(), view=AuctionView(self))
        self.state["message"] = msg
        if self.timer_task: self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.auction_timer(total_minutes * 60))

        await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Item Auction started in {target_channel.mention}!", ephemeral=True)

    @auction_group.command(name="cancel", description="Cancel the active auction")
    @app_commands.default_permissions(administrator=True)
    async def auction_cancel(self, interaction: discord.Interaction):
        if not self.state["active"]: return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} No active auction to cancel.", ephemeral=True)
        if self.timer_task: self.timer_task.cancel()
        self.state["active"] = False

        if self.state["message"]:
            embed = discord.Embed(title=f"{CUSTOM_EMOJI_TITLE} Auction Cancelled", description=f"The auction for **{self.state['item']}** was cancelled by an admin.", color=0x36393f)
            disabled_view = discord.ui.View()
            disabled_view.add_item(discord.ui.Button(label="Cancelled", style=discord.ButtonStyle.secondary, disabled=True))
            await self.state["message"].edit(embed=embed, view=disabled_view)

        self.state.update({"type": None, "item": None, "message": None, "thumbnail_url": None, "bottom_image_url": None, "card_image_url": None, "card_description": None})
        await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} Auction cancelled.", ephemeral=True)

    winner_group = app_commands.Group(name="auction_winners", description="Manage the auction winner lock out list")

    @winner_group.command(name="add", description="add someone to the winner list so they cannot bid")
    @app_commands.default_permissions(administrator=True)
    async def winner_add(self, interaction: discord.Interaction, member: discord.Member):
        await add_auction_winner(member.id)
        await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} {member.mention} has been added to the winner list.", ephemeral=True)

    @winner_group.command(name="remove", description="Remove someone from the winner list so they can bid again")
    @app_commands.default_permissions(administrator=True)
    async def winner_remove(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await remove_auction_winner(member.id)
            await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} {member.mention} has been removed from the winner list.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} {member.mention} is not in the winner list.", ephemeral=True)

    @winner_group.command(name="list", description="View everyone currently locked out from bidding")
    @app_commands.default_permissions(administrator=True)
    async def winner_list(self, interaction: discord.Interaction):
        winners = await get_auction_winners()
        if not winners: return await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} The winner list is currently empty.", ephemeral=True)
        mentions = [f"<@{uid}>" for uid in winners]
        await interaction.response.send_message(embed=discord.Embed(title=f"{CUSTOM_EMOJI_TITLE} Locked Out Auction Winners", description="\n".join(mentions), color=CRIMSON_RED), ephemeral=True)

    @winner_group.command(name="clear", description="Wipe the entire winner list")
    @app_commands.default_permissions(administrator=True)
    async def winner_clear(self, interaction: discord.Interaction):
        await clear_auction_winners()
        await interaction.response.send_message(f"{CUSTOM_EMOJI_TITLE} The auction winner list has been wiped!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AuctionCog(bot))