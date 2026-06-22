import discord
from discord.ext import commands
import csv
import os
import re

# Standard Karuta Bot ID
KARUTA_BOT_ID = 432610292342587392

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
        
        if message.author.id != KARUTA_BOT_ID or not message.embeds:
            return

        embed = message.embeds[0]
        
        if not embed.title or "Character Lookup" not in embed.title:
            return
            
        print(f"\n--- [DEBUG] KARUTA KLU DETECTED ---")

        if not embed.description:
            print("[DEBUG] FAILED: Embed has no description text.")
            return

        description = embed.description

        char_name = None
        series_name = None
        wishlists = None

        lines = description.split('\n')
        for line in lines:
            clean_line = line.replace('*', '').replace('_', '').strip()
            
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

        print(f"[DEBUG] Extracted -> Char: '{char_name}', Series: '{series_name}', WL: '{wishlists}'")

        if char_name and series_name and wishlists is not None:
            try:
                search_query = char_name.lower()
                needs_update = False
                
                if search_query in self.wishlist_db:
                    if self.wishlist_db[search_query]['wishlists'] != wishlists:
                        print(f"🔄 [DEBUG] Updating existing character: {char_name} (from {self.wishlist_db[search_query]['wishlists']} to {wishlists})")
                        self.wishlist_db[search_query]['wishlists'] = wishlists
                        needs_update = True
                    else:
                        print(f"⏭️ [DEBUG] No update needed for {char_name}. WL count is already {wishlists}.")
                else:
                    print(f"🌟 [DEBUG] New Character Found! Adding {char_name} to database.")
                    self.wishlist_db[search_query] = {
                        "name": char_name,
                        "series": series_name,
                        "wishlists": wishlists
                    }
                    needs_update = True

                if needs_update:
                    self.save_database()
                    await message.add_reaction("✅")
                    
            except Exception as e:
                print(f"❌ [DEBUG] Save process failure: {e}")
        else:
            print("❌ [DEBUG] FAILED: Could not parse all required data fields from the embed.")
        
        print(f"-----------------------------------\n")

    # --- EVENT LISTENERS ---
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Fires when Karuta sends a new lookup embed."""
        await self.process_karuta_embed(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        """
        Using the RAW API payload ensures we catch Karuta's slash command edits 
        even if the message wasn't inside the bot's internal cache!
        """
        author_data = payload.data.get("author", {})
        if str(author_data.get("id")) != str(KARUTA_BOT_ID) and payload.data.get("author") is not None:
            pass

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(payload.channel_id)

            if channel:
                message = await channel.fetch_message(payload.message_id)
                await self.process_karuta_embed(message)
                
        except discord.errors.NotFound:
            pass
        except Exception as e:
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