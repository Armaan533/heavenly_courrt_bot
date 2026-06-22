import discord
from discord.ext import commands
import csv
import os
import re
import json

KARUTA_BOT_ID = 646937666251915264
GEM_RATE = 19

class KarutaPricingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wishlist_db = {}
        self.frame_db = {}
        self.pending_prices = {}
        self.wishlist_filepath = "final_readable_master.csv"
        self.frame_filepath = "frames_db.json"
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

        if os.path.exists(self.frame_filepath):
            try:
                with open(self.frame_filepath, 'r', encoding='utf-8') as file:
                    self.frame_db = json.load(file)
            except Exception:
                pass
        else:
            self.frame_db = {"Noble Frame": 15, "Cyberpunk Frame": 25}
            self.save_frame_database()

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

    def save_frame_database(self):
        try:
            with open(self.frame_filepath, 'w', encoding='utf-8') as file:
                json.dump(self.frame_db, file, indent=4)
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
        is_lp = False

        if 1 <= print_num <= 9:
            sp_rates = {1: (1.5, 2.2), 2: (1.8, 2.3), 3: (1.5, 1.8), 4: (2.0, 2.3), 5: (2.1, 2.4), 6: (1.8, 2.8), 7: (2.0, 2.4)}
            rate_min, rate_max = sp_rates.get(edition, (2.0, 2.4))
            base_min = wl / rate_max
            base_max = wl / rate_min

        elif 10 <= print_num <= 99:
            is_lp = True
            lp_configs = {
                1: {"base": (8.0, 14.0), "brackets": [(1000, 200, 0.1), (2000, 1000, 0.5), (5000, 2000, 1.0)], "spike_threshold": 5000, "spike_val": 5.0},
                2: {"base": (8.0, 15.0), "brackets": [(1000, 400, 0.3), (2500, 1200, 0.7), (6000, 2500, 1.2)], "spike_threshold": 5000, "spike_val": 6.0},
                3: {"base": (8.0, 15.0), "brackets": [(1000, 150, 0.1), (2000, 500, 0.3), (5000, 1200, 0.8)], "spike_threshold": 5000, "spike_val": 4.0},
                4: {"base": (7.1, 13.1), "brackets": [(1000, 300, 0.2), (2000, 800, 0.4), (5000, 2000, 0.9)], "spike_threshold": 5000, "spike_val": 4.5},
                5: {"base": (8.2, 12.2), "brackets": [(1500, 600, 0.3), (3000, 1200, 0.5), (6000, 3000, 1.4)], "spike_threshold": 5000, "spike_val": 5.5},
                6: {"base": (8.1, 11.1), "brackets": [(1000, 250, 0.1), (2000, 700, 0.3), (4000, 1500, 0.6)], "spike_threshold": 4000, "spike_val": 3.0},
                7: {"base": (9.2, 12.2), "brackets": [(1000, 500, 0.3), (3000, 2000, 0.9), (7000, 5000, 2.0)], "spike_threshold": 6000, "spike_val": 7.0}
            }
            cfg = lp_configs.get(edition, lp_configs[1])
            base_min, base_max = cfg["base"]
            
            remaining_wl = wl
            current_floor = 0
            for limit, step, mod in cfg["brackets"]:
                bracket_capacity = limit - current_floor
                wl_in_this_bracket = min(remaining_wl, bracket_capacity)
                if wl_in_this_bracket > 0:
                    bonus = (wl_in_this_bracket / step) * mod
                    base_min += bonus
                    base_max += bonus
                    remaining_wl -= wl_in_this_bracket
                current_floor = limit
            
            if wl > cfg["spike_threshold"]:
                base_min += cfg["spike_val"]
                base_max += cfg["spike_val"]

        elif 100 <= print_num <= 999:
            mp_rates = {1: (70, 100), 2: (65, 95), 3: (60, 90), 4: (55, 85), 5: (65, 80), 6: (55, 70), 7: (50, 65)}
            rate_min, rate_max = mp_rates.get(edition, (55, 70))
            base_min = wl / rate_max
            base_max = wl / rate_min

        else:
            hp_rates = {1: (750, 950), 2: (720, 840), 3: (590, 700), 4: (380, 470), 5: (200, 240), 6: (190, 220), 7: (140, 180)}
            rate_min, rate_max = hp_rates.get(edition, (190, 220))
            base_min = wl / rate_max
            base_max = wl / rate_min

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
            if frame_name in self.frame_db:
                frame_cost = self.frame_db[frame_name]
                frame_status = f"{frame_name} (+{frame_cost}🎟️)"
            else:
                frame_status = f"{frame_name} (Price Unmapped)"

        cosmetic_total += frame_cost

        worker_bonus = 0.0
        if worker_stats.get("has_stats"):
            s_count = worker_stats.get("s_grades", 0)
            a_count = worker_stats.get("a_grades", 0)
            worker_bonus += (s_count * 1.5) + (a_count * 0.5)
            
        total_min = max(1, round(base_min + cosmetic_total + worker_bonus))
        total_max = max(1, round(base_max + cosmetic_total + worker_bonus))
        
        return {
            "min_tix": total_min,
            "max_tix": total_max,
            "base_range": f"{round(base_min, 1)}-{round(base_max, 1)}🎟️" if not is_lp else f"{round(base_min, 1)}🎟️*",
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
            parts = re.split(r'\s*[·•・‧|∙⋅◈🔹🔸♦✨]\s*', header_line)
            print_part_idx = -1
            
            for i, part in enumerate(parts):
                if "#" in part:
                    print_match = re.search(r'#(\d+)', part)
                    if print_match:
                        print_num = int(print_match.group(1))
                        print_part_idx = i
                        
            if print_part_idx != -1 and print_part_idx + 1 < len(parts):
                ed_match = re.search(r'(\d+)', parts[print_part_idx + 1])
                if ed_match:
                    edition = int(ed_match.group(1))

            eligible_text_parts = []
            char_part = None
            for part in parts:
                if "**" in part:
                    char_part = part
                    continue
                clean_p = part.strip()
                if not clean_p or "#" in clean_p or "★" in clean_p:
                    continue
                if edition is not None and clean_p == str(edition):
                    continue
                if print_num is not None and clean_p == str(print_num):
                    continue
                if len(clean_p) <= 7 and clean_p.isalnum() and parts.index(part) == 0:
                    continue
                eligible_text_parts.append(clean_p)

            if char_part:
                raw_char = char_part.replace('**', '').strip()
                if "alias of" in raw_char:
                    cosmetics["has_alias"] = True
                    alias_match = re.search(r'alias of\s+([^)]+)', raw_char)
                    if alias_match:
                        char_name = alias_match.group(1).strip()
                    else:
                        char_name = raw_char.split('(')[0].strip()
                else:
                    char_name = raw_char
                if eligible_text_parts:
                    series_name = eligible_text_parts[0]
            else:
                if len(eligible_text_parts) >= 2:
                    series_name = eligible_text_parts[0]
                    char_name = eligible_text_parts[1]

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

        return char_name, series_name, edition, print_num, cosmetics, worker_stats

    async def generate_price_embed(self, channel, user_id, char_name, series_name, edition, print_num, cosmetics, worker_stats, wl_count):
        calcs = self.calculate_card_value(edition, print_num, wl_count, cosmetics, worker_stats)
        
        embed = discord.Embed(
            title=f"💳 Strategic Valuation Breakdown", 
            description=f"Market analysis tool for <@{user_id}>", 
            color=0x2f3136
        )
        embed.add_field(name="🃏 Asset Identity", value=f"**{char_name}**\n*Ed {edition} · #{print_num}*", inline=True)
        embed.add_field(name="📊 Public Demand", value=f"💌 **{wl_count:,}** Wishlists", inline=True)
        
        cosmetic_desc = []
        if calcs['dye_cost']: cosmetic_desc.append(f"🎨 Dye Layer: `+{calcs['dye_cost']}🎟️`")
        if calcs['sketch_cost']: cosmetic_desc.append(f"✍️ Sketch Matrix: `+{calcs['sketch_cost']}🎟️`")
        if calcs['alias_cost']: cosmetic_desc.append(f"🏷️ Identity Alias: `+1🎟️`")
        if calcs['frame_status'] != "None": cosmetic_desc.append(f"🖼️ Frame Profile: {calcs['frame_status']}")
        
        if not cosmetic_desc: cosmetic_desc.append("*No premium modifications recorded.*")
        embed.add_field(name="💎 Cosmetic Assets", value="\n".join(cosmetic_desc), inline=False)
        
        if calcs['worker_bonus'] > 0:
            embed.add_field(name="⚙️ Workforce Scaling", value=f"Bonus efficiency modifier applied: `+{calcs['worker_bonus']}🎟️`", inline=False)

        min_gems = calcs['min_tix'] * GEM_RATE
        max_gems = calcs['max_tix'] * GEM_RATE
        
        embed.add_field(
            name="🏁 Net Valuation Assessment", 
            value=f"🎟️ **{calcs['min_tix']:,} – {calcs['max_tix']:,} Tickets**\n🔮 **{min_gems:,} – {max_gems:,} Gems**", 
            inline=False
        )
        embed.set_footer(text="Values aggregated from active market datasets.")
        
        await channel.send(embed=embed)

    async def process_karuta_embed(self, message: discord.Message):
        if message.author.id != KARUTA_BOT_ID or not message.embeds:
            return

        embed = message.embeds[0]
        title = str(embed.title) if embed.title else ""

        if "Card Details" in title or "Card Information" in title:
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
                            cdata['worker_stats'], wishlists
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
                                cdata['worker_stats'], wishlists
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
            char_name, series_name, edition, print_num, cosmetics, worker_stats = self.parse_kci_message(embed)
            
            if not char_name or not series_name or edition is None or print_num is None:
                return

            db_key = f"{char_name.lower()}||{series_name.lower()}"
            if db_key in self.wishlist_db:
                wl_count = self.wishlist_db[db_key]["wishlists"]
                await self.generate_price_embed(
                    channel, payload.user_id, char_name, series_name, 
                    edition, print_num, cosmetics, worker_stats, wl_count
                )
            else:
                self.pending_prices[(char_name.lower(), series_name.lower())] = (
                    payload.channel_id, payload.user_id, {
                        "char_name": char_name, "series_name": series_name,
                        "edition": edition, "print_num": print_num,
                        "cosmetics": cosmetics, "worker_stats": worker_stats
                    }
                )
                await channel.send(
                    f"⚠️ **{char_name}** does not have a wishlist count in the database.\n"
                    f"Please run `klu {char_name}` to automatically resolve and print the valuation matrix!",
                    delete_after=15
                )
        except Exception:
            pass

    @commands.command(name="fadd")
    @commands.has_permissions(administrator=True)
    async def add_frame_price(self, ctx, ticket_value: int, *, frame_name: str):
        self.frame_db[frame_name.strip()] = ticket_value
        self.save_frame_database()
        await ctx.send(f"✅ Added **{frame_name}** to the frame database at **{ticket_value}🎟️**.")

async def setup(bot):
    await bot.add_cog(KarutaPricingCog(bot))