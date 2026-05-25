import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta

from utils.database import get_points, remove_points, add_points
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
        state = self.cog.state
        
        if not state["active"]:
            return await interaction.response.send_message("No active auction right now.", ephemeral=True)
            
        if interaction.user.id in state["winner_ids"]:
            return await interaction.response.send_message(
                "✦ You've already won an item this auction — you can't bid on further items.",
                ephemeral=True
            )
            
        await interaction.response.send_modal(BidModal(self.cog))


class AuctionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state = {
            "active":          False,
            "items":           [],
            "current_index":   0,
            "current_bid":     0,
            "current_bidder":  None,
            "bid_interval":    10,
            "min_bid":         50,
            "duration":        300,
            "end_time":        None,
            "message":         None,
            "channel":         None,
            "winner_ids":      set(),
            "winners":         {},
        }
        self.timer_task = None

    def make_embed(self) -> discord.Embed:
        s = self.state
        item_num = s["current_index"] + 1
        total    = len(s["items"])
        item     = s["items"][s["current_index"]]
        
        remaining = max(0, int((s["end_time"] - discord.utils.utcnow()).total_seconds())) if s["end_time"] else 0
        mins, secs = divmod(remaining, 60)
        time_str = f"{mins}m {secs}s"
        
        embed = discord.Embed(title=f"✦ Auction — Item {item_num} of {total}", color=EMBED_COLOR)
        embed.add_field(name="Item", value=item, inline=False)
        embed.add_field(name="Current Bid", value=f"**{s['current_bid']}** pts" if s["current_bid"] > 0 else "No bids yet", inline=True)
        embed.add_field(name="Highest Bidder", value=s["current_bidder"].mention if s["current_bidder"] else "—", inline=True)
        embed.add_field(name="Min Bid", value=f"{s['min_bid']} pts", inline=True)
        embed.add_field(name="Bid Interval", value=f"+{s['bid_interval']} pts minimum", inline=True)
        embed.add_field(name="Time Remaining", value=time_str, inline=True)
        embed.set_footer(text="Heavenly Court ✦ Monthly Auction — bids are final once placed")
        return embed

    async def update_embed(self):
        if self.state["message"]:
            try:
                await self.state["message"].edit(embed=self.make_embed())
            except Exception as e:
                print(f"embed update error: {e}")

    async def timer_loop(self):
        try:
            while True:
                await asyncio.sleep(5)
                if not self.state["active"]:
                    break
                await self.update_embed()
                if discord.utils.utcnow() >= self.state["end_time"]:
                    await self.end_current_item()
                    break
        except asyncio.CancelledError:
            pass

    async def start_item(self, index: int):
        s = self.state
        s["current_index"]  = index
        s["current_bid"]    = 0
        s["current_bidder"] = None
        s["end_time"]       = discord.utils.utcnow() + timedelta(seconds=s["duration"])
        s["active"]         = True
        
        view  = AuctionView(self)
        embed = self.make_embed()
        msg   = await s["channel"].send(embed=embed, view=view)
        s["message"] = msg
        
        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.timer_loop())

    async def end_current_item(self):
        s = self.state
        s["active"] = False
        channel  = s["channel"]
        item_num = s["current_index"] + 1
        item     = s["items"][s["current_index"]]
        
        if s["current_bidder"]:
            winner = s["current_bidder"]
            bid    = s["current_bid"]
            
            try:
                await remove_points(winner.id, bid)
            except ValueError:
                await add_points(winner.id, -bid)
                
            s["winner_ids"].add(winner.id)
            s["winners"][s["current_index"]] = winner.id
            
            end_embed = discord.Embed(
                title=f"✦ Item {item_num} — Sold!",
                description=f"**{item}** won by {winner.mention} for **{bid}** pts ✦",
                color=0x9b59b6
            )
            if s["message"]:
                await s["message"].edit(embed=end_embed, view=None)
            await channel.send(f"🎉 {winner.mention} won **{item}** for **{bid}** contribution points!")
        else:
            end_embed = discord.Embed(
                title=f"✦ Item {item_num} — No Bids",
                description=f"**{item}** received no bids and has been passed.",
                color=0xe74c3c
            )
            if s["message"]:
                await s["message"].edit(embed=end_embed, view=None)
            await channel.send(f"Item {item_num} had no bids — moving on.")

        await asyncio.sleep(5)
        next_index = s["current_index"] + 1
        
        if next_index < len(s["items"]):
            countdown = await channel.send("✦ Next item starting in **10 seconds**...")
            await asyncio.sleep(10)
            try:
                await countdown.delete()
            except Exception:
                pass
            await self.start_item(next_index)
        else:
            await channel.send(
                "✦ The auction has concluded!\n\n"
                "Winners may open a ticket to claim their prizes. "
                "Please include your winning item when opening the ticket. ✦"
            )
            s["winner_ids"].clear()
            s["winners"].clear()
            s["items"] = []

    async def process_bid(self, interaction: discord.Interaction, bid_str: str):
        s = self.state
        if not s["active"]:
            return await interaction.response.send_message("No active auction right now.", ephemeral=True)
            
        if interaction.user.id in s["winner_ids"]:
            return await interaction.response.send_message(
                "✦ You've already won an item this auction — you can't bid further.",
                ephemeral=True
            )
            
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
            
        s["current_bid"]    = bid
        s["current_bidder"] = interaction.user
        await self.update_embed()
        
        await interaction.response.send_message(
            f"✦ Bid of **{bid}** pts placed successfully!",
            ephemeral=True
        )

    @commands.group(name="auction", invoke_without_command=True)
    @commands.guild_only()
    async def auction_cmd(self, ctx):
        embed = discord.Embed(
            title="✦ Auction Commands",
            description="A simple guide to running the auction:",
            color=EMBED_COLOR
        )
        
        commands_list = (
            "**`,auction setup <minutes> <min_bid> <interval> Item1|Item2|Item3|Item4|Item5`**\n"
            "Prepares the 5 items. *(Example: `,auction setup 5 50 10 Sword|Shield|Potion|Ring|Cape`)*\n\n"
            "**`,auction start`**\n"
            "Begins the auction once it is set up.\n\n"
            "**`,auction extend <minutes>`**\n"
            "Adds extra time to the current item.\n\n"
            "**`,auction status`**\n"
            "Shows what is currently being auctioned and the highest bid.\n\n"
            "**`,auction cancel`**\n"
            "Stops the current auction completely."
        )
        
        embed.add_field(name="Command List", value=commands_list, inline=False)
        embed.set_footer(text="Heavenly Court ✦ Auction System")
        await ctx.send(embed=embed)

    @auction_cmd.command(name="start")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def auction_start(self, ctx):
        if not self.state["items"]:
            return await ctx.send("✦ No auction prepared — use `,auction setup` first.")
        if self.state["active"]:
            return await ctx.send("✦ An auction is already running.")
            
        await ctx.send("✦ Starting the auction!")
        await self.start_item(0)

    @auction_cmd.command(name="cancel")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def auction_cancel(self, ctx):
        if self.timer_task:
            self.timer_task.cancel()
        self.state["active"] = False
        self.state["items"]  = []
        await ctx.send("✦ Auction cancelled.")

    @auction_cmd.command(name="status")
    @commands.guild_only()
    async def auction_status(self, ctx):
        if not self.state["active"] and not self.state["items"]:
            return await ctx.send("✦ No auction running or prepared.")
        if self.state["active"]:
            await ctx.send(embed=self.make_embed())
        else:
            await ctx.send(embed=discord.Embed(
                description="✦ Auction prepared but not started yet. Use `,auction start`.",
                color=EMBED_COLOR
            ))

async def setup(bot):
    await bot.add_cog(AuctionCog(bot))