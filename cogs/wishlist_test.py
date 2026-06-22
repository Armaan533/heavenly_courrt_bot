import discord
from discord.ext import commands
import csv
import os
import re

# Standard Karuta Bot ID
KARUTA_BOT_ID = 646937666251915264

class WishlistTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wishlist_db = {}
        self.filepath = "final_readable_master.csv"
        self.load_database()

    def load_database(self):
        if not os.path.exists(self.filepath):
            print(f"⚠️ [Wishlist DB] File '{self.filepath}' not found! Make sure it is next to main.py.")
            return
            
        try:
            with open(self.filepath, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    char_name = row['character'].strip().lower()
                    self.wishlist_db[char_name] = {
                        "name": row['character'].strip(),
                        "series": row['series'].strip(),
                        "wishlists": int(row['wishlist'].strip())
                    }
            print(f"✅ [Wishlist DB] Successfully loaded {len(self.wishlist_db):,} characters!")
        except Exception as e:
            print(f"❌ [Wishlist DB] Error loading data: {e}")

    def save_database(self):
        """Writes the current dictionary back into the CSV file."""
        try:
            with open(self.filepath, mode='w', newline='', encoding='utf-8-sig') as file:
                fieldnames = ['character', 'series', 'wishlist']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                
                writer.writeheader()
                for data in self.wishlist_db.values():
                    writer.writerow({
                        'character': data['name'],
                        'series': data['series'],
                        'wishlist': data['wishlists']
                    })
            print("💾 [Wishlist DB] Successfully saved updates to CSV.")
        except Exception as e:
            print(f"❌ [Wishlist DB] Error saving to CSV: {e}")

    async def process_karuta_embed(self, message: discord.Message):
        """Scans a Karuta lookup message to extract and save wishlist data."""
        
        # FILTER: Ensure it's Karuta
        if message.author.id != KARUTA_BOT_ID:
            return

        # DEBUG 1: Show whenever Karuta sends ANY message
        print(f"\n--- [DEBUG] KARUTA MESSAGE RECEIVED ---")
        print(f"[DEBUG] Embeds found: {len(message.embeds)}")

        if not message.embeds:
            print("[DEBUG] Exiting: Message contains no embeds.")
            print(f"---------------------------------------\n")
            return

        embed = message.embeds[0]
        
        # DEBUG 2: Log what fields Karuta is using for headings
        print(f"[DEBUG] Embed Title: '{embed.title}'")
        print(f"[DEBUG] Embed Author Field: '{embed.author.name if embed.author else 'None'}'")

        if not embed.description:
            print("[DEBUG] Exiting: Embed has no description text.")
            print(f"---------------------------------------\n")
            return

        description = embed.description

        char_name = None
        series_name = None
        wishlists = None

        # Line-by-Line Parsing
        lines = description.split('\n')
        for line in lines:
            clean_line = line.replace('*', '').replace('_', '').strip()
            
            # Use regex split on the middle dot (·) or colons to isolate values safely
            if clean_line.startswith('Character'):
                parts = re.split(r'[·:]', clean_line, maxsplit=1)
                if len(parts) > 1:
                    char_name = parts[1].strip()
            elif clean_line.startswith('Series'):
                parts = re.split(r'[·:]', clean_line, maxsplit=1)
                if len(parts) > 1:
                    series_name = parts[1].strip()
            elif clean_line.startswith('Wishlisted'):
                parts = re.split(r'[·:]', clean_line, maxsplit=1)
                if len(parts) > 1:
                    wl_str = parts[1].replace(',', '').strip()
                    if wl_str.isdigit():
                        wishlists = int(wl_str)

        print(f"[DEBUG] Parsed -> Char: '{char_name}', Series: '{series_name}', WL: '{wishlists}'")

        # Validate that all data was successfully extracted
        if char_name and series_name and wishlists is not None:
            try:
                search_query = char_name.lower()
                needs_update = False
                
                if search_query in self.wishlist_db:
                    if self.wishlist_db[search_query]['wishlists'] != wishlists:
                        print(f"🔄 [DEBUG] Updating entry: {char_name} (from {self.wishlist_db[search_query]['wishlists']} to {wishlists})")
                        self.wishlist_db[search_query]['wishlists'] = wishlists
                        needs_update = True
                    else:
                        print(f"⏭️ [DEBUG] Match current: No updates required for {char_name}.")
                else:
                    print(f"🌟 [DEBUG] New entry detected: Adding {char_name} to database.")
                    self.wishlist_db[search_query] = {
                        "name": char_name,
                        "series": series_name,
                        "wishlists": wishlists
                    }
                    needs_update = True

                if needs_update:
                    self.save_database()
                    await message.add_reaction("✅")
                    print("[DEBUG] Operations completed successfully.")
                    
            except Exception as e:
                print(f"❌ [DEBUG] Database write failure: {e}")
        else:
            print("❌ [DEBUG] FAILED: Could not isolate target structural lines inside description.")
        
        print(f"---------------------------------------\n")

    # --- EVENT LISTENERS ---
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Fires when Karuta sends a new lookup embed."""
        await self.process_karuta_embed(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        """Fires when Karuta edits an embed into an existing message framework."""
        try:
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(payload.channel_id)

            if channel:
                message = await channel.fetch_message(payload.message_id)
                await self.process_karuta_embed(message)
        except Exception:
            pass

    # --- COMMANDS ---

    @commands.command(name="wl", aliases=["wishlist", "check"])
    async def test_wishlist(self, ctx, *, character_name: str):
        """Prefix command to look up a character's wishlist count."""
        search_query = character_name.strip().lower()
        
        if search_query in self.wishlist_db:
            data = self.wishlist_db[search_query]
            
            embed = discord.Embed(
                title="🔍 Wishlist Database Search",
                color=0x6b1614
            )
            embed.add_field(name="Character", value=f"**{data['name']}**", inline=True)
            embed.add_field(name="Series", value=f"*{data['series']}*", inline=True)
            embed.add_field(name="Wishlists", value=f"💌 **{data['wishlists']:,}**", inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Could not find **{character_name}** in the database. Run `klu {character_name}` to automatically add them!", delete_after=10)

    @commands.command(name="wlreload")
    @commands.has_permissions(administrator=True)
    async def reload_wishlist(self, ctx):
        """Allows admins to reload the CSV without restarting the bot."""
        self.wishlist_db.clear()
        self.load_database()
        await ctx.send(f"✅ Reloaded the Wishlist database! Current character count: **{len(self.wishlist_db):,}**")

async def setup(bot):
    await bot.add_cog(WishlistTestCog(bot))