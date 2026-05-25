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

    @discord.ui.button(label="Place Bid", style=discord.ButtonStyle.primary, emoji="🏷️", custom_id="auction_bid")
    async def place_bid(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cog.state["active"]:
            return await interaction.response.send_message("No active auction right now.", ephemeral=True)
            
        if await is_auction_winner(interaction.user.id):
            return await interaction.response.send_message("✦ You've already won an item recently — you cannot bid again until the winner list is reset.", ephemeral=True)
            
        await interaction.response.send_modal(BidModal(self.cog))

class AuctionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state = {
            "active":          False,
            "item":            None,
            "current_bid":     0,
            "current_bidder":  None,
            "bid_interval":    10,
            "min_bid":         50,
            "end_time":        None,
            "message":         None,
            "channel":         None,
        }
        self.timer_task = None

    def make_embed(self) -> discord.Embed:
        s = self.state
        embed = discord.Embed(title="✦ Heavenly Court Live Auction ✦", color=EMBED_COLOR)
        embed.description = f"### 🎁 {s['item']}"
        
        bid_text = f"## {s['current_bid']} pts" if s["current_bid"] > 0 else "## No bids yet!"
        embed.add_field(name="💰 Current Highest Bid", value=bid_text, inline=False)
        
        bidder = s["current_bidder"].mention if s["current_bidder"] else "—"
        embed.add_field(name="👑 Highest Bidder", value=bidder, inline=True)
        
        if s["end_time"]:
            unix_time = int(s["end_time"].timestamp())
            embed.add_field(name="⏱️ Ends In", value=f"<t:{unix_time}:R>", inline=True)
            
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
        
        if s["current_bidder"]:
            winner = s["current_bidder"]
            bid = s["current_bid"]
            
            try:
                await remove_points(winner.id, bid)
            except ValueError:
                await add_points(winner.id, -bid)
                
            await add_auction_winner(winner.id)
                
            end_embed = discord.Embed(
                title="✦ Auction Ended!",
                description=f"### 🎁 {item}\n🎉 Won by {winner.mention} for **{bid}** pts ✦",
                color=0x9b59b6
            )
            if s["message"]:
                await s["message"].edit(embed=end_embed, view=None)
                
            await channel.send(
                f"🎉 {winner.mention} won **{item}** for **{bid}** contribution points!\n"
                "Please open a ticket to claim your prize. ✦"
            )
        else:
            end_embed = discord.Embed(
                title="✦ Auction Ended — No Bids",
                description=f"### 🎁 {item}\nReceived no bids.",
                color=0xe74c3c
            )
            if s["message"]:
                await s["message"].edit(embed=end_embed, view=None)
            await channel.send(f"The auction for **{item}** ended with no bids.")

        self.state["item"] = None
        self.state["message"] = None

    async def process_bid(self, interaction: discord.Interaction, bid_str: str):
        s = self.state
        if not s["active"]:
            return await interaction.response.send_message("No active auction right now.", ephemeral=True)
            
        if await is_auction_winner(interaction.user.id):
            return await interaction.response.send_message("✦ You've already won an item recently — you cannot bid again until the winner list is reset.", ephemeral=True)
            
        try:
            bid = int(bid_str.strip())
        except ValueError:
            return await interaction.response.send_message("Please enter a valid number.", ephemeral=True)
            
        min_next = s["current_bid"] + s["bid_interval"] if s["current_bid"] > 0 else s["min_bid"]
        if bid < min_next:
            return await interaction.response.send_message(
                f"✦ Bid rejected — minimum bid is **{min_next}** pts "
                f"(current: {s['current_bid']} + interval: {s['bid_interval']}).",
                ephemeral=True
            )
            
        user_pts = await get_points(interaction.user.id)
        if user_pts < bid:
            return await interaction.response.send_message(
                f"✦ Not enough points — you have **{user_pts}** pts but bid requires **{bid}** pts.",
                ephemeral=True
            )
            
        previous_bidder = s["current_bidder"]
        
        s["current_bid"]    = bid
        s["current_bidder"] = interaction.user
        
        if s["message"]:
            await s["message"].edit(embed=self.make_embed())
            
        await interaction.response.send_message(
            f"✦ Bid of **{bid}** pts placed successfully!",
            ephemeral=True
        )
        
        if previous_bidder and previous_bidder.id != interaction.user.id:
            outbid_embed = discord.Embed(
                title="⚠️ You've been outbid!",
                description=f"You were just outbid on **{s['item']}** in the Heavenly Court auction!\n\nThe new highest bid is **{bid} pts**.",
                color=0xe74c3c
            )
            try:
                await previous_bidder.send(embed=outbid_embed)
            except discord.Forbidden:
                if s["channel"]:
                    warn_msg = await s["channel"].send(f"⚠️ {previous_bidder.mention}, you were just outbid on **{s['item']}**!")
                    await warn_msg.delete(delay=10)

    auction_group = app_commands.Group(name="auction", description="Manage the item auction system")

    @auction_group.command(name="start", description="Start a new item auction")
    @app_commands.describe(
        item="The name of the item being auctioned",
        duration="How many minutes the auction lasts",
        min_bid="Starting minimum bid",
        interval="Minimum interval to raise bids"
    )
    @app_commands.default_permissions(administrator=True)
    async def auction_start(self, interaction: discord.Interaction, item: str, duration: int, min_bid: int, interval: int):
        if self.state["active"]:
            return await interaction.response.send_message("✦ An auction is already running. Cancel it or let it finish first.", ephemeral=True)

        channel = interaction.guild.get_channel(AUCTION_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message("✦ Auction channel not found", ephemeral=True)

        end_time = discord.utils.utcnow() + timedelta(minutes=duration)

        self.state.update({
            "active":         True,
            "item":           item,
            "current_bid":    0,
            "current_bidder": None,
            "bid_interval":   interval,
            "min_bid":        min_bid,
            "end_time":       end_time,
            "channel":        channel,
        })

        view = AuctionView(self)
        embed = self.make_embed()
        
        msg = await channel.send(embed=embed, view=view)
        self.state["message"] = msg

        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.auction_timer(duration * 60))

        await interaction.response.send_message(f"✦ Auction for **{item}** started in {channel.mention}!", ephemeral=True)

    @auction_group.command(name="cancel", description="Cancel the active auction")
    @app_commands.default_permissions(administrator=True)
    async def auction_cancel(self, interaction: discord.Interaction):
        if not self.state["active"]:
            return await interaction.response.send_message("✦ No active auction to cancel.", ephemeral=True)

        if self.timer_task:
            self.timer_task.cancel()
        self.state["active"] = False

        if self.state["message"]:
            embed = discord.Embed(
                title="✦ Auction Cancelled",
                description=f"The auction for **{self.state['item']}** was cancelled by an admin.",
                color=0xe74c3c
            )
            await self.state["message"].edit(embed=embed, view=None)

        self.state["item"] = None
        self.state["message"] = None

        await interaction.response.send_message("✦ Auction cancelled successfully.", ephemeral=True)

    winner_group = app_commands.Group(name="auction_winners", description="Manage the auction winner lock out list")

    @winner_group.command(name="add", description="add someone to the winner list so they cannot bid")
    @app_commands.default_permissions(administrator=True)
    async def winner_add(self, interaction: discord.Interaction, member: discord.Member):
        await add_auction_winner(member.id)
        await interaction.response.send_message(f"✦ {member.mention} has been added to the auction winner list.", ephemeral=True)

    @winner_group.command(name="remove", description="Remove someone from the winner list so they can bid again")
    @app_commands.default_permissions(administrator=True)
    async def winner_remove(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await remove_auction_winner(member.id)
            await interaction.response.send_message(f"✦ {member.mention} has been removed from the winner list.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(f"✦ {member.mention} is not in the winner list.", ephemeral=True)

    @winner_group.command(name="list", description="View everyone currently locked out from bidding")
    @app_commands.default_permissions(administrator=True)
    async def winner_list(self, interaction: discord.Interaction):
        winners = await get_auction_winners()
        if not winners:
            return await interaction.response.send_message("✦ The winner list is currently empty.", ephemeral=True)
            
        mentions = [f"<@{uid}>" for uid in winners]
        embed = discord.Embed(title="✦ Locked Out Auction Winners", description="\n".join(mentions), color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @winner_group.command(name="clear", description="Wipe the entire winner list")
    @app_commands.default_permissions(administrator=True)
    async def winner_clear(self, interaction: discord.Interaction):
        await clear_auction_winners()
        await interaction.response.send_message("✦ The auction winner list has been wiped.!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AuctionCog(bot))