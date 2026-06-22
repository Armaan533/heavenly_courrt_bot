import discord
from discord.ext import commands
import csv
import os
import re
import json
from frame_prices import FRAME_DB

KARUTA_BOT_ID = 646937666251915264
GEM_RATE = 19

class KarutaPricingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wishlist_db = {}
        self.pending_prices = {}
        self.wishlist_filepath = "final_readable_master.csv"
        self.load_databases()

    def load_databases(self):
        if os.path.exists(self.wishlist_filepath):
            try:
                with open(self.wishlist_filepath, mode='r', encoding='utf-8-sig') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        char_name = row['character'].strip()
                        series_name = row['series'].strip()
                        key = f"{char_name.lower()}||{series_name.lower()}"
                        self.wishlist_db[key] = {
                            "name": char_name,
                            "series": series_name,
                            "wishlists": int(row['wishlist'].strip())
                        }
            except Exception:
                pass

        if "" in self.wishlist_db:
            del self.wishlist_db[""]

    def save_wishlist_database(self):
        try:
            with open(self.wishlist_filepath, mode='w', newline='', encoding='utf-8-sig') as file:
                fieldnames = ['character', 'series', 'wishlist']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for data in self.wishlist_db.values():
                    writer.writerow({
                        'character': data['name'],
                        'series': data['series'],
                        'wishlist': data['wishlists']
                    })
        except Exception:
            pass

    def update_db_entry(self, char_name: str, series_name: str, wishlists: int) -> bool:
        char_lower = char_name.lower()
        series_lower = series_name.lower()
        matched_key = None
        
        for key in self.wishlist_db.keys():
            k_char, k_series = key.split('||', 1)
            if k_char == char_lower:
                if k_series == series_lower or series_lower.endswith('...') and k_series.startswith(series_lower[:-3].strip()) or k_series.endswith('...') and series_lower.startswith(k_series[:-3].strip()):
                    matched_key = key
                    break

        needs_update = False
        if matched_key:
            entry = self.wishlist_db[matched_key]
            if entry['wishlists'] != wishlists:
                entry['wishlists'] = wishlists
                needs_update = True
            if entry['series'].endswith('...') and not series_name.endswith('...'):
                entry['series'] = series_name
                new_key = f"{char_lower}||{series_name.lower()}"
                self.wishlist_db[new_key] = entry
                del self.wishlist_db[matched_key]
                needs_update = True
        else:
            new_key = f"{char_lower}||{series_lower}"
            self.wishlist_db[new_key] = {"name": char_name, "series": series_name, "wishlists": wishlists}
            needs_update = True
            
        return needs_update

    def calculate_card_value(self, edition: int, print_num: int, wl: int, cosmetics: dict, worker_stats: dict):
        base_min, base_max = 0.0, 0.0

        # --- SINGLE PRINTS ---
        if 1 <= print_num <= 9:
            sp_rates = {1: (1.5, 2.2), 2: (1.8, 2.3), 3: (1.5, 1.8), 4: (2.0, 2.3), 5: (2.1, 2.4), 6: (1.8, 2.8), 7: (2.0, 2.4)}
            rate_min, rate_max = sp_rates.get(edition, (2.0, 2.4))
            base_min = wl / rate_max
            base_max = wl / rate_min

        # --- LOW PRINTS ---
        elif 10 <= print_num <= 99:
            lp_configs = {
                1: {"base": (8.0, 14.0), "brackets": [(1000, 200, 0.1), (3000, 1000, 0.5), (5000, 2000, 1.0)], "spike_threshold": 5000, "spike_val": 5.0},
                2: {"base": (8.0, 15.0), "brackets": [(1200, 400, 0.3), (2500, 1200, 0.7), (5000, 2500, 1.2)], "spike_threshold": 5000, "spike_val": 6.0},
                3: {"base": (8.0, 15.0), "brackets": [(1000, 150, 0.1), (2500, 500, 0.3), (5000, 1200, 0.8)], "spike_threshold": 5000, "spike_val": 4.0},
                4: {"base": (7.1, 13.1), "brackets": [(1000, 300, 0.2), (2500, 800, 0.4), (5000, 2000, 0.9)], "spike_threshold": 5000, "spike_val": 4.5},
                5: {"base": (8.2, 12.2), "brackets": [(1200, 600, 0.3), (3000, 1200, 0.5), (6000, 3000, 1.4)], "spike_threshold": 6000, "spike_val": 5.5},
                6: {"base": (8.1, 11.1), "brackets": [(1000, 250, 0.1), (2500, 700, 0.3), (4000, 1500, 0.6)], "spike_threshold": 4000, "spike_val": 3.0},
                7: {"base": (9.2, 12.2), "brackets": [(1500, 500, 0.3), (3500, 2000, 0.9), (8500, 5000, 2.0)], "spike_threshold": 6000, "spike_val": 7.0}
            }
            cfg = lp_configs.get(edition, lp_configs[1])
            rate_min, rate_max = cfg["base"]
            
            rate_modifier = 0.0
            remaining_wl = wl
            current_floor = 0
            
            for limit, step, mod in cfg["brackets"]:
                bracket_capacity = limit - current_floor
                wl_in_this_bracket = min(remaining_wl, bracket_capacity)
                if wl_in_this_bracket > 0:
                    bonus = (wl_in_this_bracket / step) * mod
                    rate_modifier += bonus
                    remaining_wl -= wl_in_this_bracket
                current_floor = limit
            
            if wl > cfg["spike_threshold"]:
                rate_modifier += cfg["spike_val"]

            # Calculate final Rate (WL per Ticket divisor)
            final_rate_min = rate_min + rate_modifier
            final_rate_max = rate_max + rate_modifier

            # Calculate ACTUAL ticket value (WL divided by Rate)
            base_min = wl / final_rate_max if final_rate_max > 0 else 0
            base_max = wl / final_rate_min if final_rate_min > 0 else 0

        # --- MID PRINTS ---
        elif 100 <= print_num <= 999:
            mp_rates = {1: (70, 100), 2: (65, 95), 3: (60, 90), 4: (55, 85), 5: (65, 80), 6: (55, 70), 7: (50, 65)}
            rate_min, rate_max = mp_rates.get(edition, (55, 70))
            base_min = wl / rate_max
            base_max = wl / rate_min

        # --- HIGH PRINTS ---
        else:
            hp_rates = {1: (750, 950), 2: (720, 840), 3: (590, 700), 4: (380, 470), 5: (200, 240), 6: (190, 220), 7: (140, 180)}
            rate_min, rate_max = hp_rates.get(edition, (190, 220))
            base_min = wl / rate_max
            base_max = wl / rate_min

        # --- COSMETICS ---
        cosmetic_total = 0.0
        dye_cost = 0
        if cosmetics.get("has_dye"):
            dye_cost = 25 if cosmetics.get("is_mystic") else 2
            cosmetic_total += dye_cost
            
        sketch_cost = cosmetics.get("inkwell", 0) / GEM_RATE
        cosmetic_total += sketch_cost
        
        alias_cost = 1 if cosmetics.get("has_alias") else 0
        cosmetic_total += alias_cost
        
        frame_name = cosmetics.get("frame", "")
        frame_cost = 0
        frame_status = "None"
        if frame_name:
            cleaned_f = frame_name.lower().strip()
            search_keys = [cleaned_f, f"{cleaned_f} frame"]
            matched_key = None
            
            for sk in search_keys:
                if sk in FRAME_DB:
                    matched_key = sk
                    break
                    
            if matched_key:
                frame_cost = FRAME_DB[matched_key].get("market", 0)
                display_name = matched_key.replace(" frame", "").title()
                frame_status = f"{display_name} Frame (+{frame_cost} 🎟️)"
            else:
                frame_status = f"{frame_name} (Price Unmapped)"

        cosmetic_total += frame_cost

        # --- WORKER BONUS ---
        worker_bonus = 0.0
        if worker_stats.get("has_stats"):
            s_count = worker_stats.get("s_grades", 0)
            a_count = worker_stats.get("a_grades", 0)
            worker_bonus += (s_count * 1.5) + (a_count * 0.5)
            
        total_min = max(1, round(base_min + cosmetic_total + worker_bonus))
        total_max = max(1, round(base_max + cosmetic_total + worker_bonus))
        
        return {
            "base_min": base_min,
            "base_max": base_max,
            "min_tix": total_min,
            "max_tix": total_max,
            "dye_cost": dye_cost,
            "sketch_cost": round(sketch_cost, 1),
            "alias_cost": alias_cost,
            "frame_status": frame_status,
            "worker_bonus": round(worker_bonus, 1)
        }

    def parse_kci_message(self, embed):
        full_text_parts = []
        if embed.description: full_text_parts.append(embed.description)
        for field in embed.fields:
            if field.value: full_text_parts.append(field.value)
        full_text = "\n".join(full_text_parts)

        image_url = None
        if embed.image and embed.image.url:
            image_url = embed.image.url
        elif embed.thumbnail and embed.thumbnail.url:
            image_url = embed.thumbnail.url

        char_name, series_name = None, None
        edition, print_num = None, None
        cosmetics = {"has_dye": False, "is_mystic": False, "inkwell": 0, "has_alias": False, "frame": ""}
        worker_stats = {"has_stats": False, "s_grades": 0, "a_grades": 0}

        header_line = ""
        for line in full_text.splitlines():
            if "#" in line:
                header_line = line
                break

        if header_line:
            clean_header = header_line.replace('*', '').replace('_', '').replace('~', '').strip()
            print_match = re.search(r'#(\d+)', clean_header)
            if print_match:
                print_num = int(print_match.group(1))

            parts = re.split(r'\s*[·•・‧|∙⋅]\s*', clean_header)
            for i, p in enumerate(parts):
                if '#' in p:
                    if i + 1 < len(parts):
                        ed_match = re.search(r'(\d+)', parts[i+1])
                        if ed_match:
                            edition = int(ed_match.group(1))
                    if i + 2 < len(parts):
                        series_name = parts[i+2].strip()
                    if i + 3 < len(parts):
                        raw_char = parts[i+3].strip()
                        if "alias of" in raw_char:
                            cosmetics["has_alias"] = True
                            alias_match = re.search(r'alias of\s+([^)]+)', raw_char)
                            if alias_match:
                                char_name = alias_match.group(1).strip()
                            else:
                                char_name = raw_char.split('(')[0].strip()
                        else:
                            char_name = raw_char
                    break

        for line in full_text.splitlines():
            clean = line.replace('*', '').replace('_', '').replace('`', '').strip()
            if "Framed with" in clean:
                cosmetics["frame"] = clean.split("Framed with")[-1].strip()
            elif "Dyed with" in clean:
                cosmetics["has_dye"] = True
                dye_info = clean.split("Dyed with")[-1].strip()
                if "mystic" in dye_info.lower():
                    cosmetics["is_mystic"] = True
            elif "Inkwell is at" in clean:
                ink_match = re.search(r'Inkwell is at\s+([\d,]+)', clean)
                if ink_match:
                    cosmetics["inkwell"] = int(ink_match.group(1).replace(',', ''))
            elif "Ink:" in clean:
                ink_match = re.search(r'Ink:\s+([\d,]+)', clean)
                if ink_match:
                    cosmetics["inkwell"] = int(ink_match.group(1).replace(',', ''))
                    
            if any(stat in clean for stat in ["Vanity", "Toughness", "Quickness", "Effort"]):
                worker_stats["has_stats"] = True
                grades = re.findall(r'\b([SA])\b', clean.upper())
                for g in grades:
                    if g == 'S': worker_stats["s_grades"] += 1
                    if g == 'A': worker_stats["a_grades"] += 1

        return char_name, series_name, edition, print_num, cosmetics, worker_stats, image_url

    async def generate_price_embed(self, channel, user_id, char_name, series_name, edition, print_num, cosmetics, worker_stats, wl_count, image_url):
        calcs = self.calculate_card_value(edition, print_num, wl_count, cosmetics, worker_stats)
        
        embed = discord.Embed(
            title="<:eight_side_sparkle:1516681364806570105> Card Pricing",
            color=0x6b1614
        )
        embed.description = f"Requested by <@{user_id}>"

        if image_url:
            embed.set_thumbnail(url=image_url)

        embed.add_field(
            name="<:book_ig:1516683126066253844> Card Info", 
            value=f"**{char_name}** • *{series_name}*\nEdition {edition} • #{print_num} • 💌 {wl_count:,}", 
            inline=False
        )
        
        base_min_rnd = round(calcs['base_min'], 1)
        base_max_rnd = round(calcs['base_max'], 1)
        embed.add_field(
            name="<:red_lotus:1516679367743377448> Standalone Price", 
            value=f"`🎟️ {base_min_rnd} - {base_max_rnd}`", 
            inline=False
        )
        
        extras_text = ""
        if calcs['frame_status'] != "None":
            extras_text += f"**Frame:** {calcs['frame_status']}\n"
        if calcs['dye_cost']:
            d_type = "Mystic" if cosmetics.get("is_mystic") else "Normal"
            extras_text += f"**Dye ({d_type}):** +{calcs['dye_cost']} 🎟️\n"
        if calcs['sketch_cost']:
            extras_text += f"**Sketch:** +{calcs['sketch_cost']} 🎟️\n"
        if calcs['alias_cost']:
            extras_text += f"**Alias:** +{calcs['alias_cost']} 🎟️\n"
        if calcs['worker_bonus'] > 0:
            extras_text += f"**Worker Stats:** +{calcs['worker_bonus']} 🎟️\n"
            
        if extras_text:
            embed.add_field(name="<:two_flowers:1516684386546880614> Extras", value=extras_text.strip(), inline=False)
            
        min_gems = calcs['min_tix'] * GEM_RATE
        max_gems = calcs['max_tix'] * GEM_RATE
        
        embed.add_field(
            name="<:for_booster:1517226639438778503> Total Price", 
            value=f"**🎟️ {calcs['min_tix']:,} - {calcs['max_tix']:,}**\n**💎 {min_gems:,} - {max_gems:,}**", 
            inline=False
        )

        if print_num <= 9:
            embed.set_footer(text="⚠️ Single Print detected. Prices are estimates—always take offers!")
        
        await channel.send(embed=embed)

    async def process_karuta_embed(self, message: discord.Message):
        if message.author.id != KARUTA_BOT_ID or not message.embeds:
            return

        embed = message.embeds[0]
        title = str(embed.title) if embed.title else ""

        if "Card Details" in title or "Card Information" in title:
            full_text_parts = []
            if embed.description: full_text_parts.append(embed.description)
            for field in embed.fields:
                if field.value: full_text_parts.append(field.value)
            full_text = "\n".join(full_text_parts).lower()

            if any(x in full_text for x in ["condition", "dropped on", "grabbed by", "inkwell"]):
                try:
                    await message.add_reaction("💵")
                except:
                    pass
            return

        if "Character Lookup" in title:
            full_text_parts = []
            if embed.description: full_text_parts.append(embed.description)
            for field in embed.fields:
                if field.value: full_text_parts.append(field.value)
            full_text = "\n".join(full_text_parts)

            char_name, series_name, wishlists = None, None, None
            for line in full_text.splitlines():
                clean_line = line.replace('*', '').replace('_', '').replace('`', '').strip()
                if clean_line.startswith('Character'):
                    parts = re.split(r'[·:]', clean_line, maxsplit=1)
                    if len(parts) > 1: char_name = parts[1].strip()
                elif clean_line.startswith('Series'):
                    parts = re.split(r'[·:]', clean_line, maxsplit=1)
                    if len(parts) > 1: series_name = parts[1].strip()
                elif clean_line.startswith('Wishlisted'):
                    parts = re.split(r'[·:]', clean_line, maxsplit=1)
                    if len(parts) > 1:
                        wl_str = parts[1].replace(',', '').strip()
                        if wl_str.isdigit(): wishlists = int(wl_str)

            if char_name and series_name and wishlists is not None:
                if self.update_db_entry(char_name, series_name, wishlists):
                    self.save_wishlist_database()
                
                hk = (char_name.lower(), series_name.lower())
                if hk in self.pending_prices:
                    ch_id, u_id, cdata = self.pending_prices.pop(hk)
                    channel = self.bot.get_channel(ch_id)
                    if channel:
                        await self.generate_price_embed(
                            channel, u_id, cdata['char_name'], cdata['series_name'],
                            cdata['edition'], cdata['print_num'], cdata['cosmetics'],
                            cdata['worker_stats'], wishlists, cdata['image_url']
                        )

        elif "Character Results" in title:
            full_text_parts = []
            if embed.description: full_text_parts.append(embed.description)
            for field in embed.fields:
                if field.value: full_text_parts.append(field.value)
            full_text = "\n".join(full_text_parts)

            chunks = re.split(r'(?=\d+\s*\.\s*[♡❤❤️♥️🤍💖])', full_text)
            needs_save = False
            for chunk in chunks:
                chunk = chunk.replace('*', '').replace('_', '').replace('~', '').replace('`', '').strip()
                match = re.match(r'^\d+\s*\.\s*[♡❤❤️♥️🤍💖]?([\d,]+)\s*·\s*(.*?)\s*·\s*(.+)$', chunk)
                
                if match:
                    wishlists = int(match.group(1).replace(',', ''))
                    s_name = match.group(2).strip()
                    c_name = match.group(3).strip()
                    
                    if self.update_db_entry(c_name, s_name, wishlists):
                        needs_save = True
                    
                    hk = (c_name.lower(), s_name.lower())
                    if hk in self.pending_prices:
                        ch_id, u_id, cdata = self.pending_prices.pop(hk)
                        channel = self.bot.get_channel(ch_id)
                        if channel:
                            await self.generate_price_embed(
                                channel, u_id, cdata['char_name'], cdata['series_name'],
                                cdata['edition'], cdata['print_num'], cdata['cosmetics'],
                                cdata['worker_stats'], wishlists, cdata['image_url']
                            )
            if needs_save:
                self.save_wishlist_database()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.process_karuta_embed(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        author_data = payload.data.get("author")
        if author_data and str(author_data.get("id")) != str(KARUTA_BOT_ID):
            return
                
        try:
            channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
            if not channel:
                return
            message = await channel.fetch_message(payload.message_id)
            if message.author.id == KARUTA_BOT_ID:
                await self.process_karuta_embed(message)
        except:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or str(payload.emoji) != "💵":
            return
            
        try:
            channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            if message.author.id != KARUTA_BOT_ID or not message.embeds:
                return
                
            embed = message.embeds[0]
            char_name, series_name, edition, print_num, cosmetics, worker_stats, image_url = self.parse_kci_message(embed)
            
            if not char_name or not series_name or edition is None or print_num is None:
                return

            db_key = f"{char_name.lower()}||{series_name.lower()}"
            if db_key in self.wishlist_db:
                wl_count = self.wishlist_db[db_key]["wishlists"]
                await self.generate_price_embed(
                    channel, payload.user_id, char_name, series_name, 
                    edition, print_num, cosmetics, worker_stats, wl_count, image_url
                )
            else:
                self.pending_prices[(char_name.lower(), series_name.lower())] = (
                    payload.channel_id, payload.user_id, {
                        "char_name": char_name, "series_name": series_name,
                        "edition": edition, "print_num": print_num,
                        "cosmetics": cosmetics, "worker_stats": worker_stats,
                        "image_url": image_url
                    }
                )
                await channel.send(
                    f"⚠️ **{char_name}** does not have a wishlist count in the database.\n"
                    f"Please run `klu {char_name}` to automatically resolve and price the card!",
                    delete_after=15
                )
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(KarutaPricingCog(bot))