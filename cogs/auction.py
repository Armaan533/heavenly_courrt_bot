import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
from datetime import timedelta

from utils.database import (
    get_points, remove_points, add_points, 
    is_auction_winner, add_auction_winner, remove_auction_winner, get_auction_winners, clear_auction_winners
)
from constants import *

# --- THEME OVERRIDES ---
CRIMSON_RED = 0x8b0000 
E_SPARKLE = "<:eight_side_sparkle:1516681364806570105>"    
E_ITEM    = "<:red_lotus:1516679367743377448>"   
E_CHAR    = "<:red_lotus:1516679367743377448>"   
E_SERIES  = "<:book_ig:1516683126066253844>"    
E_CARD    = "<:red_lotus:1516679367743377448>"    
E_TIME    = "<:celestial_hourglass:1516684938509029396>"   
E_SUCCESS = "✅"    
E_ERROR   = "❌" 

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

    @discord.ui.button(label="Place Bid", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji.from_str(E_SPARKLE), custom_id="auction_bid")
    async def place_bid(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cog.state["active"]:
            return await interaction.response.send_message("No active auction right now.", ephemeral=True)
            
        if await is_auction_winner(interaction.user.id):
            return await interaction.response.send_message(f"{E_CHAR} You've already won an item recently — you cannot bid again until the winner list is reset.", ephemeral=True)
            
        await interaction.response.send_modal(BidModal(self.cog))

class AuctionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bid_lock = asyncio.Lock()
        self.state = {}
        self.reset_state() 
        self.timer_task = None

    def reset_state(self):
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
            "host":             None,
            "card_image_url":   None, 
            "character":        None,
            "series":           None,
            "kci":              None,
            "print":            None,
            "edition":          None,
        }

    def make_embed(self) -> discord.Embed:
        s = self.state
        embed = discord.Embed(title="✦ . HEAVENLY COURT AUCTION . ✦", color=CRIMSON_RED)
        
        desc = f"{E_SPARKLE} *A new treasure has entered the pavilion.*\n━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if s.get("type") == "Card":
            char = s.get("character", "Unknown")
            series = s.get("series", "Unknown")
            kci = s.get("kci", "Unknown")
            prnt = s.get("print", "Unknown")
            ed = s.get("edition", "Unknown")
            
            desc += f"{E_CHAR} **Character:** {char}\n"
            if series != "Unknown" and series != char:
                desc += f"{E_SERIES} **Series:** {series}\n\n"
            else:
                desc += "\n"
            
            desc += f"{E_CARD} **Card Details:**\n"
            desc += f"| **Code:** `{kci}` | **Print:** `{prnt}` | **Edition:** `{ed}` |\n\n"
            
            if s.get("card_image_url"):
                embed.set_thumbnail(url=s["card_image_url"])
            if s.get("bottom_image_url"):
                embed.set_image(url=s["bottom_image_url"])
                
        else:
            desc += f"{E_ITEM} **Item:** {s['item']}\n\n"
            if s.get("thumbnail_url"):
                embed.set_thumbnail(url=s["thumbnail_url"])
            if s.get("bottom_image_url"):
                embed.set_image(url=s["bottom_image_url"])
        
        desc += f"{E_SPARKLE} **Auction Details:**\n"
        desc += f"✦ Starting Bid: `{s['min_bid']}` pts\n"
        desc += f"✦ Minimum Raise: `+{s['bid_interval']}` pts\n\n"
        
        bid_text = f"**{s['current_bid']}** pts" if s["current_bid"] > 0 else "No bids yet!"
        bidder = s["current_bidder"].mention if s["current_bidder"] else "—"
        
        desc += f"💰 **Current Bid:** {bid_text}\n"
        desc += f"👑 **Highest Bidder:** {bidder}\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if s.get("end_time"):
            unix_time = int(s["end_time"].timestamp())
            desc += f"{E_TIME} **Ends:** <t:{unix_time}:R>\n"
            
        host = s.get("host")
        if host:
            desc += f"**Hosted by {host.display_name}**"
            
        embed.description = desc
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
        
        disabled_view = discord.ui.View()
        disabled_view.add_item(discord.ui.Button(label="Auction Ended", style=discord.ButtonStyle.secondary, emoji="🔒", disabled=True))
        
        if s["current_bidder"]:
            winner = s["current_bidder"]
            bid = s["current_bid"]
            
            try: remove_points(winner.id, bid)
            except ValueError: add_points(winner.id, -bid)
                
            await add_auction_winner(winner.id)
            
            if s["message"]:
                end_embed = self.make_embed()
                end_embed.title = "✦ . AUCTION ENDED . ✦"
                end_embed.color = 0x36393f 
                await s["message"].edit(embed=end_embed, view=disabled_view)
                
            display_name = s.get("character") if s.get("type") == "Card" else s["item"]
            await channel.send(
                f"🎉 {winner.mention} won **{display_name}** for **{bid}** pts!\n"
                f"Please open a ticket to claim your prize. {E_CHAR}"
            )
        else:
            if s["message"]:
                end_embed = self.make_embed()
                end_embed.title = "✦ . AUCTION FAILED — NO BIDS . ✦"
                end_embed.color = 0x36393f
                await s["message"].edit(embed=end_embed, view=disabled_view)
            
            display_name = s.get("character") if s.get("type") == "Card" else s["item"]
            await channel.send(f"The auction for **{display_name}** ended with no bids.")

        self.reset_state()

    async def process_bid(self, interaction: discord.Interaction, bid_str: str):
        async with self.bid_lock:
            s = self.state
            if not s["active"]:
                return await interaction.response.send_message("No active auction right now.", ephemeral=True)
                
            if await is_auction_winner(interaction.user.id):
                return await interaction.response.send_message(f"{E_CHAR} You've already won an item recently.", ephemeral=True)
                
            try: bid = int(bid_str.strip())
            except ValueError: return await interaction.response.send_message("Please enter a valid number.", ephemeral=True)
                
            min_next = s["current_bid"] + s["bid_interval"] if s["current_bid"] > 0 else s["min_bid"]
            if bid < min_next:
                return await interaction.response.send_message(f"{E_CHAR} Minimum bid is **{min_next}** pts.", ephemeral=True)
                
            user_pts = await get_points(interaction.user.id)
            if user_pts < bid:
                return await interaction.response.send_message(f"{E_CHAR} Not enough points. You have **{user_pts}** pts.", ephemeral=True)
                
            previous_bidder = s["current_bidder"]
            s["current_bid"] = bid
            s["current_bidder"] = interaction.user
            
            # --- ⏱️ ANTI-SNIPE MECHANIC ---
            time_remaining = (s["end_time"] - discord.utils.utcnow()).total_seconds()
            if time_remaining < 60:
                s["end_time"] = discord.utils.utcnow() + timedelta(seconds=60)
                if self.timer_task: self.timer_task.cancel()
                self.timer_task = asyncio.create_task(self.auction_timer(60))
                
                if s["channel"]:
                    snipe_embed = discord.Embed(description=f"{E_TIME} **Anti-Snipe Triggered!** Timer extended by 60 seconds.", color=CRIMSON_RED)
                    warn_msg = await s["channel"].send(embed=snipe_embed)
                    await warn_msg.delete(delay=10) 

            if s["message"]: await s["message"].edit(embed=self.make_embed())
            await interaction.response.send_message(f"{E_SUCCESS} Bid of **{bid}** pts placed successfully!", ephemeral=True)
            
            if previous_bidder and previous_bidder.id != interaction.user.id:
                display_name = s.get("character") if s.get("type") == "Card" else s["item"]
                outbid_embed = discord.Embed(title="⚠️ You've been outbid!", description=f"You were outbid on **{display_name}**! New highest bid is **{bid} pts**.", color=CRIMSON_RED)
                try: await previous_bidder.send(embed=outbid_embed)
                except discord.Forbidden:
                    if s["channel"]:
                        warn_msg = await s["channel"].send(f"⚠️ {previous_bidder.mention}, you were just outbid on **{display_name}**!")
                        await warn_msg.delete(delay=10)

    auction_group = app_commands.Group(name="auction", description="Manage the item auction system")

    # 1. COMMAND: AUCTION CARD 
    @auction_group.command(name="card", description="Start a new Karuta Card auction")
    @app_commands.describe(
        min_bid="Starting minimum bid",
        interval="Minimum interval to raise bids",
        hours="How many hours the auction lasts",
        channel="Optional: Select the channel to post the auction in",
        bottom_image="Optional: Upload a large image for the bottom"
    )
    @app_commands.default_permissions(administrator=True)
    async def auction_card(self, interaction: discord.Interaction, min_bid: int, interval: int, hours: int = 24, channel: discord.TextChannel = None, bottom_image: discord.Attachment = None):
        if self.state.get("active"):
            return await interaction.response.send_message(f"{E_ERROR} An auction is already running.", ephemeral=True)

        if hours <= 0: return await interaction.response.send_message(f"{E_ERROR} Hours must be > 0.", ephemeral=True)

        target_channel = channel or interaction.guild.get_channel(AUCTION_CHANNEL_ID)
        if not target_channel: return await interaction.response.send_message(f"{E_ERROR} Channel not found.", ephemeral=True)

        await interaction.response.send_message(f"{E_SUCCESS} Configuration saved! **{interaction.user.mention}, please run `kci <card_code>` in this channel now.**", ephemeral=False)

        def karuta_check(m):
            # Same ID check as your giveaway script
            return (m.author.id == 646937666251915264 and m.channel.id == target_channel.id and len(m.embeds) > 0 and "Card Details" in (m.embeds[0].title or ""))

        try:
            karuta_msg = await self.bot.wait_for('message', timeout=120.0, check=karuta_check)
        except asyncio.TimeoutError:
            self.reset_state()
            return await target_channel.send(f"{E_ERROR} Auction setup timed out. Please run the command again.")

        # Parse Karuta exactly like giveaway.py
        embed_data = karuta_msg.embeds[0]
        lines = [l.strip() for l in (embed_data.description or "").split("\n") if l.strip()]
        if not lines: return await target_channel.send(f"{E_ERROR} Could not read card metadata.")

        stats_line = lines[0]
        for line in lines:
            if "·" in line and "#" in line: 
                stats_line = line
                break

        parts = [p.strip().replace("*", "").replace("`", "") for p in stats_line.split("·") if "★" not in p and "☆" not in p]
        
        code = parts[0] if len(parts) > 0 else "Unknown"
        print_num = parts[1] if len(parts) > 1 else "Unknown"
        edition = parts[2] if len(parts) > 2 else "Unknown"
        series = parts[3] if len(parts) > 3 else "Unknown"
        character_name = parts[-1] if len(parts) > 0 else "Unknown"
        
        card_image_url = embed_data.thumbnail.url if embed_data.thumbnail else None

        self.state.update({
            "active": True, 
            "type": "Card", 
            "item": character_name, 
            "current_bid": 0, 
            "current_bidder": None, 
            "bid_interval": interval, 
            "min_bid": min_bid,
            "end_time": discord.utils.utcnow() + timedelta(hours=hours), 
            "channel": target_channel,
            "bottom_image_url": bottom_image.url if bottom_image else None, 
            "host": interaction.user,
            "card_image_url": card_image_url, 
            "character": character_name, 
            "series": series, 
            "kci": code, 
            "print": print_num, 
            "edition": edition,
        })

        # Cleanup the kci prompt
        try:
            setup_msg = await interaction.original_response()
            await setup_msg.delete()
        except: pass

        try:
            async for hist_msg in target_channel.history(limit=10):
                if hist_msg.author.id == interaction.user.id and hist_msg.content.lower().startswith("kci"):
                    await hist_msg.delete()
                    break
        except: pass

        msg = await target_channel.send(embed=self.make_embed(), view=AuctionView(self))
        self.state["message"] = msg
        
        if self.timer_task: self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.auction_timer(hours * 3600))


    @auction_group.command(name="item", description="Start a new custom Item auction")
    @app_commands.describe(
        item_name="The name of the item being auctioned",
        min_bid="Starting minimum bid",
        interval="Minimum interval to raise bids",
        hours="How many hours the auction lasts",
        channel="Optional: Select the channel to post the auction in",
        thumbnail="Optional: Upload an image for the top right corner",
        bottom_image="Optional: Upload a large image for the bottom"
    )
    @app_commands.default_permissions(administrator=True)
    async def auction_item(self, interaction: discord.Interaction, item_name: str, min_bid: int, interval: int, hours: int = 24, channel: discord.TextChannel = None, thumbnail: discord.Attachment = None, bottom_image: discord.Attachment = None):
        if self.state.get("active"):
            return await interaction.response.send_message(f"{E_ERROR} An auction is already running.", ephemeral=True)

        if hours <= 0: return await interaction.response.send_message(f"{E_ERROR} Hours must be > 0.", ephemeral=True)

        target_channel = channel or interaction.guild.get_channel(AUCTION_CHANNEL_ID)
        if not target_channel: return await interaction.response.send_message(f"{E_ERROR} Channel not found.", ephemeral=True)

        self.state.update({
            "active": True, 
            "type": "Item", 
            "item": item_name, 
            "current_bid": 0, 
            "current_bidder": None, 
            "bid_interval": interval, 
            "min_bid": min_bid,
            "end_time": discord.utils.utcnow() + timedelta(hours=hours), 
            "channel": target_channel,
            "thumbnail_url": thumbnail.url if thumbnail else None, 
            "bottom_image_url": bottom_image.url if bottom_image else None, 
            "host": interaction.user,
        })

        msg = await target_channel.send(embed=self.make_embed(), view=AuctionView(self))
        self.state["message"] = msg
        
        if self.timer_task: self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.auction_timer(hours * 3600))

        await interaction.response.send_message(f"{E_SUCCESS} Item Auction started in {target_channel.mention}!", ephemeral=True)


    @auction_group.command(name="cancel", description="Cancel the active auction")
    @app_commands.default_permissions(administrator=True)
    async def auction_cancel(self, interaction: discord.Interaction):
        if not self.state.get("active"): 
            return await interaction.response.send_message(f"{E_ERROR} No active auction to cancel.", ephemeral=True)
            
        if self.timer_task: 
            self.timer_task.cancel()

        if self.state["message"]:
            try:
                embed = discord.Embed(title="✦ . AUCTION CANCELLED . ✦", description=f"The auction was cancelled by an admin.", color=0x36393f)
                disabled_view = discord.ui.View()
                disabled_view.add_item(discord.ui.Button(label="Cancelled", style=discord.ButtonStyle.secondary, disabled=True))
                await self.state["message"].edit(embed=embed, view=disabled_view)
            except Exception:
                pass # Safety catch if the message was already deleted

        self.reset_state() # Hard reset guaranteed!
        await interaction.response.send_message(f"{E_SUCCESS} Auction cancelled.", ephemeral=True)


    winner_group = app_commands.Group(name="auction_winners", description="Manage the auction winner lock out list")

    @winner_group.command(name="add", description="add someone to the winner list so they cannot bid")
    @app_commands.default_permissions(administrator=True)
    async def winner_add(self, interaction: discord.Interaction, member: discord.Member):
        await add_auction_winner(member.id)
        await interaction.response.send_message(f"{E_SUCCESS} {member.mention} has been added to the winner list.", ephemeral=True)

    @winner_group.command(name="remove", description="Remove someone from the winner list so they can bid again")
    @app_commands.default_permissions(administrator=True)
    async def winner_remove(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await remove_auction_winner(member.id)
            await interaction.response.send_message(f"{E_SUCCESS} {member.mention} has been removed from the winner list.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(f"{E_ERROR} {member.mention} is not in the winner list.", ephemeral=True)

    @winner_group.command(name="list", description="View everyone currently locked out from bidding")
    @app_commands.default_permissions(administrator=True)
    async def winner_list(self, interaction: discord.Interaction):
        winners = await get_auction_winners()
        if not winners: return await interaction.response.send_message(f"{E_ERROR} The winner list is currently empty.", ephemeral=True)
        mentions = [f"<@{uid}>" for uid in winners]
        await interaction.response.send_message(embed=discord.Embed(title=f"Locked Out Auction Winners", description="\n".join(mentions), color=CRIMSON_RED), ephemeral=True)

    @winner_group.command(name="clear", description="Wipe the entire winner list")
    @app_commands.default_permissions(administrator=True)
    async def winner_clear(self, interaction: discord.Interaction):
        await clear_auction_winners()
        await interaction.response.send_message(f"{E_SUCCESS} The auction winner list has been wiped!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AuctionCog(bot))