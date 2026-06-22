import csv
import os

WISHLIST_DB = {}

def load_wishlist_data(filepath="final_readable_master.csv"):
    """Reads the CSV file and loads it into the WISHLIST_DB dictionary."""
    if not os.path.exists(filepath):
        print(f"⚠️ Warning: {filepath} not found!")
        return

    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                char_name = row['character'].strip().lower()
                series_name = row['series'].strip()
                wishlist_count = int(row['wishlist'].strip())
                
                WISHLIST_DB[char_name] = {
                    "original_name": row['character'].strip(),
                    "series": series_name,
                    "wishlists": wishlist_count
                }
                
        print(f"✅ Successfully loaded {len(WISHLIST_DB)} characters into the Wishlist Database!")
        
    except Exception as e:
        print(f"❌ Error loading wishlist data: {e}")

load_wishlist_data()