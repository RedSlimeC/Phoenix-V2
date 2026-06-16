import os
import pymongo
import bcrypt
import math
import random
import string
import ntplib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

WHEEL_DAILY_SPINS = 10
WHEEL_AVATAR_SHOP = r"c:\Users\havan\Downloads\Phoenix\src\images\account_icons\Shop"
WHEEL_BADGE_SHOP = r"c:\Users\havan\Downloads\Phoenix\src\images\badge\Shop"
WHEEL_ICON_DIR = r"c:\Users\havan\Downloads\Phoenix\src\images\ui\luckywheel"

class Database:
    def __init__(self, uri="mongodb://localhost:27017/"):
        # NTP Client for secure time
        self.ntp_client = ntplib.NTPClient()
        self._cached_network_time = None
        self._last_ntp_fetch = None

        try:
            self.client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
            self.client.server_info() # Trigger connection check
            self.db = self.client["phoenix"]
            self.users = self.db["accounts"]
            self.messages = self.db["messages"]
            self.session_keys = self.db["session_keys"]
            self.shop_state = self.db["shop_state"]
            self._migrate_existing_users()
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            print("Make sure MongoDB is running on localhost:27017")
            # For demo purposes, we'll continue, but operations will fail
            self.db = None
            self.users = None

    def get_now(self):
        """Returns the current network time if available, otherwise fallback to system time."""
        try:
            # Refresh network time every 10 minutes to avoid overhead and rate limits
            now = datetime.now()
            if self._cached_network_time is None or \
               self._last_ntp_fetch is None or \
               (now - self._last_ntp_fetch).total_seconds() > 600:
                
                response = self.ntp_client.request('pool.ntp.org', version=3, timeout=2)
                self._cached_network_time = datetime.fromtimestamp(response.tx_time, timezone.utc)
                self._last_ntp_fetch = now
                
            # Adjust the cached time by the elapsed time since fetch
            elapsed = now - self._last_ntp_fetch
            return self._cached_network_time + elapsed
        except:
            # Fallback to system time if offline
            return datetime.now(timezone.utc)

    def _migrate_existing_users(self):
        if self.users is not None:
            default_image = r"c:\Users\havan\Downloads\Phoenix\src\images\account_icons\user.png"
            self.users.update_many(
                {"level": {"$exists": False}},
                {"$set": {
                    "level": 1,
                    "xp": 0,
                    "max_xp": 100,
                    "coins": 0,
                    "image": default_image,
                    "unlocked_avatars": [default_image],
                    "unlocked_frames": [],
                    "unlocked_backgrounds": [],
                    "unlocked_badges": [],
                    "equipped_frame": None,
                    "equipped_background": None,
                    "equipped_badges": [],
                    "open_private_chats": [],
                    "last_daily_chat_reward": None,
                    "premium_until": None
                }}
            )
            self.users.update_many(
                {"open_private_chats": {"$exists": False}},
                {"$set": {"open_private_chats": []}}
            )
            self.users.update_many(
                {"last_daily_chat_reward": {"$exists": False}},
                {"$set": {"last_daily_chat_reward": None}}
            )
            self.users.update_many(
                {"unlocked_avatars": {"$exists": False}},
                {"$set": {"unlocked_avatars": [default_image]}}
            )
            self.users.update_many(
                {"unlocked_frames": {"$exists": False}},
                {"$set": {"unlocked_frames": []}}
            )
            self.users.update_many(
                {"unlocked_backgrounds": {"$exists": False}},
                {"$set": {"unlocked_backgrounds": []}}
            )
            self.users.update_many(
                {"unlocked_badges": {"$exists": False}},
                {"$set": {"unlocked_badges": []}}
            )
            self.users.update_many(
                {"equipped_frame": {"$exists": False}},
                {"$set": {"equipped_frame": None}}
            )
            self.users.update_many(
                {"equipped_background": {"$exists": False}},
                {"$set": {"equipped_background": None}}
            )
            self.users.update_many(
                {"equipped_badges": {"$exists": False}},
                {"$set": {"equipped_badges": []}}
            )
            self.users.update_many(
                {"coins": {"$exists": False}},
                {"$set": {"coins": 0}}
            )
            self.users.update_many(
                {"premium_until": {"$exists": False}},
                {"$set": {"premium_until": None}}
            )
            self.users.update_many(
                {"wheel_spins_used": {"$exists": False}},
                {"$set": {"wheel_spins_used": 0, "wheel_last_reset_date": None}}
            )

    def create_user(self, name, email, password, rank=1):
        if self.users.find_one({"$or": [{"name": name}, {"email": email}]}):
            return False, "User already exists"
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        default_image = r"c:\Users\havan\Downloads\Phoenix\src\images\account_icons\user.png"
        user_data = {
            "name": name,
            "email": email,
            "password": hashed_password,
            "rank": rank, # 1: Member, 2: Premium, 8: Mod, 9: Admin
            "level": 1,
            "xp": 0,
            "max_xp": 100,
            "coins": 0,
            "image": default_image,
            "unlocked_avatars": [default_image],
            "unlocked_frames": [],
            "unlocked_backgrounds": [],
            "unlocked_badges": [],
            "equipped_frame": None,
            "equipped_background": None,
            "equipped_badges": [],
            "open_private_chats": [],
            "last_daily_chat_reward": None,
            "premium_until": None,
            "wheel_spins_used": 0,
            "wheel_last_reset_date": None,
            "createdAt": self.get_now()
        }
        self.users.insert_one(user_data)
        return True, "User created successfully"

    def buy_avatar(self, user_id, avatar_path, price):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        
        if user.get("coins", 0) < price:
            return False, "Not enough coins"
            
        unlocked = user.get("unlocked_avatars", [])
        if avatar_path in unlocked:
            return True, "Already unlocked"
            
        unlocked.append(avatar_path)
        self.users.update_one(
            {"_id": user_id},
            {
                "$set": {"coins": user.get("coins", 0) - price},
                "$push": {"unlocked_avatars": avatar_path}
            }
        )
        return True, "Avatar purchased!"

    def buy_frame(self, user_id, frame_path, price):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        
        if user.get("coins", 0) < price:
            return False, "Not enough coins"
            
        unlocked = user.get("unlocked_frames", [])
        if frame_path in unlocked:
            return True, "Already unlocked"
            
        unlocked.append(frame_path)
        self.users.update_one(
            {"_id": user_id},
            {
                "$set": {"coins": user.get("coins", 0) - price},
                "$push": {"unlocked_frames": frame_path}
            }
        )
        return True, "Frame purchased!"

    def buy_background(self, user_id, background_path, price):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        
        if user.get("coins", 0) < price:
            return False, "Not enough coins"
            
        unlocked = user.get("unlocked_backgrounds", [])
        if background_path in unlocked:
            return True, "Already unlocked"
            
        unlocked.append(background_path)
        self.users.update_one(
            {"_id": user_id},
            {
                "$set": {"coins": user.get("coins", 0) - price},
                "$push": {"unlocked_backgrounds": background_path}
            }
        )
        return True, "Background purchased!"

    def buy_badge(self, user_id, badge_path, price):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        
        if user.get("coins", 0) < price:
            return False, "Not enough coins"
            
        unlocked = user.get("unlocked_badges", [])
        if badge_path in unlocked:
            return True, "Already unlocked"
            
        unlocked.append(badge_path)
        self.users.update_one(
            {"_id": user_id},
            {
                "$set": {"coins": user.get("coins", 0) - price},
                "$push": {"unlocked_badges": badge_path}
            }
        )
        return True, "Badge purchased!"

    def equip_frame(self, user_id, frame_path):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        if frame_path and frame_path not in user.get("unlocked_frames", []):
            return False, "Frame not unlocked"
        
        self.users.update_one({"_id": user_id}, {"$set": {"equipped_frame": frame_path}})
        return True, "Frame equipped!"

    def equip_background(self, user_id, background_path):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        if background_path and background_path not in user.get("unlocked_backgrounds", []):
            return False, "Background not unlocked"
        
        self.users.update_one({"_id": user_id}, {"$set": {"equipped_background": background_path}})
        return True, "Background equipped!"

    def equip_badge(self, user_id, badge_path):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        if badge_path not in user.get("unlocked_badges", []):
            return False, "Badge not unlocked"
        
        equipped = user.get("equipped_badges", [])
        if badge_path in equipped:
            return True, "Badge already equipped"
        if len(equipped) >= 2:
            return False, "Max 2 badges allowed"
        
        equipped.append(badge_path)
        self.users.update_one({"_id": user_id}, {"$set": {"equipped_badges": equipped}})
        return True, "Badge equipped!"

    def unequip_badge(self, user_id, badge_path):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        
        equipped = user.get("equipped_badges", [])
        if badge_path in equipped:
            equipped.remove(badge_path)
            self.users.update_one({"_id": user_id}, {"$set": {"equipped_badges": equipped}})
            return True, "Badge unequipped!"
        return False, "Badge not equipped"

    def buy_premium(self, user_id, days):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        
        cost_map = {1: 25, 3: 50, 7: 100, 14: 150, 30: 250}
        cost = cost_map.get(days, 0)
        
        if user.get("coins", 0) < cost:
            return False, "Not enough coins"
            
        now = self.get_now()
        current_premium = user.get("premium_until")
        # Ensure current_premium is offset-aware
        if current_premium and current_premium.tzinfo is None:
            current_premium = current_premium.replace(tzinfo=timezone.utc)
        
        if current_premium and current_premium > now:
            new_until = current_premium + timedelta(days=days)
        else:
            new_until = now + timedelta(days=days)
            
        update_data = {
            "coins": user.get("coins", 0) - cost,
            "premium_until": new_until
        }
        
        # Reward XP based on price (Kaufpreis / 10)
        self.add_xp(user_id, cost // 10)
        
        # If user is rank 1, promote to rank 2. Rank 3+ stays same.
        if user.get("rank", 1) == 1:
            update_data["rank"] = 2
            
        self.users.update_one({"_id": user_id}, {"$set": update_data})
        return True, "Premium extended"

    def toggle_mute(self, target_name):
        user = self.users.find_one({"name": target_name})
        if not user: return False, "User not found"
        
        new_mute_state = not user.get("is_muted", False)
        self.users.update_one({"name": target_name}, {"$set": {"is_muted": new_mute_state}})
        return True, "Muted" if new_mute_state else "Unmuted"

    def is_user_muted(self, user_name):
        user = self.users.find_one({"name": user_name})
        return user.get("is_muted", False) if user else False

    def check_premium_expiry(self, user_id):
        user = self.users.find_one({"_id": user_id})
        if not user or not user.get("premium_until"): return
        
        premium_until = user.get("premium_until")
        # Ensure premium_until is offset-aware
        if premium_until.tzinfo is None:
            premium_until = premium_until.replace(tzinfo=timezone.utc)
        
        if self.get_now() > premium_until:
            # Expired, set rank back to 1 if it was 2
            if user.get("rank") == 2:
                self.users.update_one({"_id": user_id}, {"$set": {"rank": 1}})

    def add_xp(self, user_id, amount):
        user = self.users.find_one({"_id": user_id})
        if not user: return False

        new_xp = user.get("xp", 0) + amount
        new_level = user.get("level", 1)
        max_xp = user.get("max_xp", 100)
        total_coins_gained = 0

        while new_xp >= max_xp:
            new_xp -= max_xp
            new_level += 1
            max_xp = math.ceil(max_xp * 1.42)
            # Reward coins based on reached level
            total_coins_gained += new_level

        update_data = {
            "xp": new_xp,
            "level": new_level,
            "max_xp": max_xp
        }
        
        if total_coins_gained > 0:
            self.users.update_one(
                {"_id": user_id},
                {
                    "$set": update_data,
                    "$inc": {"coins": total_coins_gained}
                }
            )
        else:
            self.users.update_one(
                {"_id": user_id},
                {"$set": update_data}
            )
        return True

    def check_level_up(self, user_id):
        """Checks if the user has enough XP for a level up and processes it."""
        user = self.users.find_one({"_id": user_id})
        if not user: return False
        
        xp = user.get("xp", 0)
        max_xp = user.get("max_xp", 100)
        level = user.get("level", 1)
        
        if xp >= max_xp:
            return self.add_xp(user_id, 0) # Trigger the while loop in add_xp
        return False

    def update_avatar(self, user_id, image_path):
        if self.users is None: return False
        self.users.update_one({"_id": user_id}, {"$set": {"image": image_path}})
        # Update all messages from this user to use the new image
        if self.messages is not None:
            self.messages.update_many({"user_id": user_id}, {"$set": {"user_image": image_path}})
        return True

    def get_rank_name(self, rank):
        ranks = {
            1: "Member",
            2: "Premium Member",
            8: "Moderator",
            9: "Admin"
        }
        return ranks.get(rank, f"Rank {rank}")

    def authenticate_user(self, name_or_email, password):
        user = self.users.find_one({"$or": [{"name": name_or_email}, {"email": name_or_email}]})
        if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
            return True, user
        return False, "Invalid credentials"

    # --- CHAT LOGIC ---
    def send_message(self, user_id, text, channel="General", recipient_name=None):
        user = self.users.find_one({"_id": user_id})
        if not user: return False, "User not found"
        
        if user.get("is_muted", False):
            return False, "You are muted and cannot send messages"
        
        now = self.get_now()
        
        # Daily XP Reward (First message per day)
        last_reward = user.get("last_daily_chat_reward")
        is_new_day = False
        if last_reward is None:
            is_new_day = True
        else:
            # Ensure last_reward is offset-aware
            if last_reward.tzinfo is None:
                last_reward = last_reward.replace(tzinfo=timezone.utc)
            # Compare dates (ignore time)
            if last_reward.date() < now.date():
                is_new_day = True
            
        if is_new_day:
            daily_reward_xp = user.get("level", 1) * 5
            self.add_xp(user_id, daily_reward_xp)
            self.users.update_one(
                {"_id": user_id},
                {"$set": {"last_daily_chat_reward": now}}
            )

        msg_data = {
            "user_id": user_id,
            "user_name": user.get("name"),
            "user_image": user.get("image"),
            "user_level": user.get("level"),
            "user_rank": user.get("rank"),
            "user_background": user.get("equipped_background"),
            "user_frame": user.get("equipped_frame"),
            "user_badges": user.get("equipped_badges", []),
            "text": text,
            "channel": channel,
            "recipient_name": recipient_name,
            "read": False,
            "timestamp": now
        }
        self.messages.insert_one(msg_data)
        return True, "Message sent"

    def get_messages(self, channel="General", user_name=None, limit=50):
        if channel == "Private" and user_name:
            # Get messages where user is sender AND recipient is target, OR user is recipient AND sender is target
            return list(self.messages.find({
                "channel": "Private",
                "$or": [
                    {"user_name": user_name, "recipient_name": self.users.find_one({"name": user_name}).get("name") if self.users.find_one({"name": user_name}) else None}, # This is complex, let's simplify
                ]
            }).sort("timestamp", -1).limit(limit))
        
        # Simplified private message fetch:
        if channel == "Private":
            # For a specific user conversation
            return list(self.messages.find({
                "channel": "Private",
                "$or": [
                    {"user_name": user_name, "recipient_name": self._get_current_username(user_name)}, # Placeholder logic
                ]
            }).sort("timestamp", -1).limit(limit))

        return list(self.messages.find({"channel": channel}).sort("timestamp", -1).limit(limit))

    def get_private_messages(self, my_name, partner_name, limit=50):
        return list(self.messages.find({
            "channel": "Private",
            "$or": [
                {"user_name": my_name, "recipient_name": partner_name},
                {"user_name": partner_name, "recipient_name": my_name}
            ]
        }).sort("timestamp", -1).limit(limit))

    def mark_as_read(self, my_name, partner_name):
        self.messages.update_many(
            {"channel": "Private", "user_name": partner_name, "recipient_name": my_name, "read": False},
            {"$set": {"read": True}}
        )

    def get_unread_private_messages(self, my_name):
        return list(self.messages.find({
            "channel": "Private",
            "recipient_name": my_name,
            "read": False
        }))

    def add_open_chat(self, user_id, partner_name):
        self.users.update_one(
            {"_id": user_id},
            {"$addToSet": {"open_private_chats": partner_name}}
        )

    def remove_open_chat(self, user_id, partner_name):
        self.users.update_one(
            {"_id": user_id},
            {"$pull": {"open_private_chats": partner_name}}
        )

    def delete_message(self, message_id, user_id):
        # Only allow if message belongs to user or user is admin (rank >= 9)
        from bson.objectid import ObjectId
        msg = self.messages.find_one({"_id": ObjectId(message_id)})
        if not msg: return False
        
        user = self.users.find_one({"_id": user_id})
        if not user: return False
        
        if msg["user_id"] == user_id or user.get("rank", 1) >= 9:
            self.messages.delete_one({"_id": ObjectId(message_id)})
            return True
        return False

    # --- AUTO HEAL LOGIC ---
    def get_auto_heal_settings(self, user_id):
        if self.users is None: return None
        user = self.users.find_one({"_id": user_id})
        if not user: return None
        return user.get("auto_heal_settings", {
            "interval": 500,
            "conditions": []
        })

    def save_auto_heal_settings(self, user_id, settings):
        if self.users is None: return False
        self.users.update_one(
            {"_id": user_id},
            {"$set": {"auto_heal_settings": settings}}
        )
        return True

    def get_zoom_settings(self, user_id):
        if self.users is None: return 720
        user = self.users.find_one({"_id": user_id})
        if not user: return 720
        return user.get("zoom_value", 720)

    def save_zoom_settings(self, user_id, value):
        if self.users is None: return False
        self.users.update_one(
            {"_id": user_id},
            {"$set": {"zoom_value": value}}
        )
        return True

    def get_app_settings(self, user_id):
        if self.users is None: return {"always_on_top": True}
        user = self.users.find_one({"_id": user_id})
        if not user: return {"always_on_top": True}
        return user.get("app_settings", {"always_on_top": True})

    def save_app_settings(self, user_id, settings):
        if self.users is None: return False
        self.users.update_one(
            {"_id": user_id},
            {"$set": {"app_settings": settings}}
        )
        return True

    def get_mining_settings(self, user_id):
        if self.users is None: return None
        user = self.users.find_one({"_id": user_id})
        if not user: return None
        return user.get("mining_settings", {
            "enabled": False,
            "delay_ms": 1,
            "region": None
        })

    def save_mining_settings(self, user_id, settings):
        if self.users is None: return False
        self.users.update_one(
            {"_id": user_id},
            {"$set": {"mining_settings": settings}}
        )
        return True

    def get_quest_settings(self, user_id):
        if self.users is None: return None
        user = self.users.find_one({"_id": user_id})
        if not user: return None
        return user.get("quest_settings", {
            "enabled": False,
            "region": None,
            "keywords": ["belohnung", "reward"],
            "click_target": None,
            "space_count": 10,
            "space_interval": 100,
            "delay_after_reward": 300,
            "delay_after_click": 200,
            "quest_window_enabled": False,
            "quest_window_region": None,
            "quest_window_key": "l"
        })

    def save_quest_settings(self, user_id, settings):
        if self.users is None: return False
        self.users.update_one(
            {"_id": user_id},
            {"$set": {"quest_settings": settings}}
        )
        return True

    def get_sequencer_settings(self, user_id):
        if self.users is None: return None
        user = self.users.find_one({"_id": user_id})
        if not user: return None
        return user.get("sequencer_settings", {"enabled": False})

    def save_sequencer_settings(self, user_id, settings):
        if self.users is None: return False
        self.users.update_one(
            {"_id": user_id},
            {"$set": {"sequencer_settings": settings}}
        )
        return True

    def get_current_shop_icons(self, user_id, category="account_icons"):
        import os
        from datetime import datetime, time
        
        shop_path_map = {
            "account_icons": r"c:\Users\havan\Downloads\Phoenix\src\images\account_icons\Shop",
            "frame": r"c:\Users\havan\Downloads\Phoenix\src\images\frame\Shop",
            "avatar_background": r"c:\Users\havan\Downloads\Phoenix\src\images\avatar_background\Shop",
            "badge": r"c:\Users\havan\Downloads\Phoenix\src\images\badge\Shop"
        }
        
        shop_path = shop_path_map.get(category, shop_path_map["account_icons"])
        if not os.path.exists(shop_path): return []
        
        all_icons = [f for f in os.listdir(shop_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        if not all_icons: return []
        
        # Check current shop state for THIS user and category
        state = self.shop_state.find_one({"type": f"current_{category}", "user_id": user_id})
        now = self.get_now()
        
        # Calculate last/next refresh (12:00 and 00:00)
        is_after_noon = now.hour >= 12
        if is_after_noon:
            last_refresh = now.replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        else:
            last_refresh = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            
        needs_refresh = False
        if not state:
            needs_refresh = True
        else:
            state_time = state.get("last_refresh", datetime.min)
            # Ensure state_time is offset-aware
            if state_time.tzinfo is None:
                state_time = state_time.replace(tzinfo=timezone.utc)
            if state_time < last_refresh:
                needs_refresh = True
                
        if needs_refresh:
            # Pick 9 random unique icons
            count = min(9, len(all_icons))
            selected_filenames = random.sample(all_icons, count)
            
            # Generate random prices for each selected icon
            shop_items = []
            for filename in selected_filenames:
                shop_items.append({
                    "filename": filename,
                    "price": random.randint(25, 50)
                })

            new_state = {
                "type": f"current_{category}",
                "user_id": user_id,
                "items": shop_items,
                "last_refresh": now
            }
            self.shop_state.update_one({"type": f"current_{category}", "user_id": user_id}, {"$set": new_state}, upsert=True)
            return shop_items
            
        return state.get("items", [])

    def get_cet_now(self):
        return self.get_now().astimezone(ZoneInfo("Europe/Berlin"))

    def get_next_cet_midnight(self):
        cet = self.get_cet_now()
        tomorrow = (cet + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return tomorrow

    def _list_shop_images(self, shop_path):
        if not os.path.exists(shop_path):
            return []
        return [
            os.path.join(shop_path, f)
            for f in os.listdir(shop_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
        ]

    def _ensure_wheel_daily_reset(self, user_id):
        cet_date = self.get_cet_now().date().isoformat()
        user = self.users.find_one({"_id": user_id})
        if not user:
            return None
        if user.get("wheel_last_reset_date") != cet_date:
            self.users.update_one(
                {"_id": user_id},
                {"$set": {"wheel_spins_used": 0, "wheel_last_reset_date": cet_date}}
            )
            user["wheel_spins_used"] = 0
            user["wheel_last_reset_date"] = cet_date
        return user

    def get_wheel_daily_prizes(self):
        cet_date = self.get_cet_now().date().isoformat()
        state = self.shop_state.find_one({"type": "wheel_daily_pool"})
        if state and state.get("date") == cet_date:
            return state.get("avatar_path"), state.get("badge_path")

        avatars = self._list_shop_images(WHEEL_AVATAR_SHOP)
        badges = self._list_shop_images(WHEEL_BADGE_SHOP)
        avatar_path = random.choice(avatars) if avatars else None
        badge_path = random.choice(badges) if badges else None

        self.shop_state.update_one(
            {"type": "wheel_daily_pool"},
            {"$set": {
                "type": "wheel_daily_pool",
                "date": cet_date,
                "avatar_path": avatar_path,
                "badge_path": badge_path
            }},
            upsert=True
        )
        return avatar_path, badge_path

    def get_wheel_segments(self, user_id):
        user = self._ensure_wheel_daily_reset(user_id)
        if not user:
            return []
        level = max(1, user.get("level", 1))
        avatar_path, badge_path = self.get_wheel_daily_prizes()

        segments = [
            {"type": "coins", "tier": 1, "amount": 5, "label": f"5 Coins",
             "icon_path": os.path.join(WHEEL_ICON_DIR, "coins1.png")},
            {"type": "xp", "tier": 1, "amount": 2 * level, "label": f"{2 * level} XP",
             "icon_path": os.path.join(WHEEL_ICON_DIR, "xp1.png")},
            {"type": "coins", "tier": 2, "amount": 10, "label": f"10 Coins",
             "icon_path": os.path.join(WHEEL_ICON_DIR, "coins2.png")},
            {"type": "xp", "tier": 2, "amount": 4 * level, "label": f"{4 * level} XP",
             "icon_path": os.path.join(WHEEL_ICON_DIR, "xp2.png")},
            {"type": "coins", "tier": 3, "amount": 20, "label": f"20 Coins",
             "icon_path": os.path.join(WHEEL_ICON_DIR, "coins3.png")},
            {"type": "xp", "tier": 3, "amount": 6 * level, "label": f"{6 * level} XP",
             "icon_path": os.path.join(WHEEL_ICON_DIR, "xp3.png")},
            {"type": "coins", "tier": 4, "amount": 40, "label": f"40 Coins",
             "icon_path": os.path.join(WHEEL_ICON_DIR, "coins4.png")},
            {"type": "xp", "tier": 4, "amount": 8 * level, "label": f"{8 * level} XP",
             "icon_path": os.path.join(WHEEL_ICON_DIR, "xp4.png")},
        ]
        if avatar_path:
            segments.append({
                "type": "avatar",
                "path": avatar_path,
                "label": "Avatar",
                "icon_path": avatar_path,
            })
        if badge_path:
            segments.append({
                "type": "badge",
                "path": badge_path,
                "label": "Badge",
                "icon_path": badge_path,
            })
        return segments

    def get_wheel_status(self, user_id):
        user = self._ensure_wheel_daily_reset(user_id)
        if not user:
            return None

        spins_used = user.get("wheel_spins_used", 0)
        next_midnight = self.get_next_cet_midnight()
        diff = next_midnight - self.get_cet_now()
        avatar_path, badge_path = self.get_wheel_daily_prizes()

        return {
            "spins_used": spins_used,
            "spins_remaining": max(0, WHEEL_DAILY_SPINS - spins_used),
            "max_spins": WHEEL_DAILY_SPINS,
            "seconds_until_refresh": max(0, int(diff.total_seconds())),
            "avatar_path": avatar_path,
            "badge_path": badge_path,
            "segments": self.get_wheel_segments(user_id)
        }

    def grant_avatar(self, user_id, avatar_path):
        user = self.users.find_one({"_id": user_id})
        if not user:
            return False, "User not found"
        unlocked = user.get("unlocked_avatars", [])
        if avatar_path in unlocked:
            return False, "Already unlocked"
        self.users.update_one(
            {"_id": user_id},
            {"$push": {"unlocked_avatars": avatar_path}}
        )
        return True, "Avatar unlocked!"

    def grant_badge(self, user_id, badge_path):
        user = self.users.find_one({"_id": user_id})
        if not user:
            return False, "User not found"
        unlocked = user.get("unlocked_badges", [])
        if badge_path in unlocked:
            return False, "Already unlocked"
        self.users.update_one(
            {"_id": user_id},
            {"$push": {"unlocked_badges": badge_path}}
        )
        return True, "Badge unlocked!"

    def _apply_wheel_prize(self, user_id, prize):
        user = self.users.find_one({"_id": user_id})
        if not user:
            return False, "User not found", prize

        level = max(1, user.get("level", 1))
        prize_type = prize["type"]

        if prize_type == "coins":
            self.users.update_one(
                {"_id": user_id},
                {"$inc": {"coins": prize["amount"]}}
            )
            return True, f"+{prize['amount']} Coins!", prize

        if prize_type == "xp":
            self.add_xp(user_id, prize["amount"])
            return True, f"+{prize['amount']} XP!", prize

        if prize_type == "avatar":
            path = prize["path"]
            if path in user.get("unlocked_avatars", []):
                fallback = 2 * level
                self.users.update_one({"_id": user_id}, {"$inc": {"coins": fallback}})
                prize = {**prize, "type": "coins", "amount": fallback, "label": f"{fallback} Coins (Fallback)"}
                return True, f"Already unlocked → {fallback} Coins!", prize
            self.grant_avatar(user_id, path)
            return True, "Avatar unlocked!", prize

        if prize_type == "badge":
            path = prize["path"]
            if path in user.get("unlocked_badges", []):
                fallback = 2 * level
                self.users.update_one({"_id": user_id}, {"$inc": {"coins": fallback}})
                prize = {**prize, "type": "coins", "amount": fallback, "label": f"{fallback} Coins (Fallback)"}
                return True, f"Already unlocked → {fallback} Coins!", prize
            self.grant_badge(user_id, path)
            return True, "Badge unlocked!", prize

        return False, "Unknown prize", prize

    def spin_wheel(self, user_id):
        user = self._ensure_wheel_daily_reset(user_id)
        if not user:
            return False, "User not found", -1, None, []

        if user.get("wheel_spins_used", 0) >= WHEEL_DAILY_SPINS:
            return False, "No spins remaining!", -1, None, []

        segments = self.get_wheel_segments(user_id)
        if not segments:
            return False, "Lucky wheel unavailable", -1, None, []

        prize_index = random.randrange(len(segments))
        prize = segments[prize_index]
        success, message, final_prize = self._apply_wheel_prize(user_id, prize)

        if success:
            self.users.update_one(
                {"_id": user_id},
                {"$inc": {"wheel_spins_used": 1}}
            )

        return success, message, prize_index, final_prize, segments

    def save_session_key(self, user_id, session_key):
        if self.session_keys is None: return False
        self.session_keys.insert_one({
            "user_id": user_id,
            "sessionkey": session_key,
            "timestamp": self.get_now()
        })
        return True
