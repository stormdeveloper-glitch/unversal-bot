"""
💾 DATA MANAGER — JSON orqali ma'lumotlarni saqlash/yuklash
"""
import json
import logging
import os
from collections import defaultdict

logger = logging.getLogger(__name__)
DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def save_data(state: dict) -> bool:
    """Barcha state ni JSON ga saqlash. Muvaffaqiyat: True."""
    try:
        payload = {
            "group_settings":   {str(k): v for k, v in state["group_settings"].items()},
            "user_warns": {
                str(cid): {str(uid): cnt for uid, cnt in warns.items()}
                for cid, warns in state["user_warns"].items()
            },
            "sanaydi_data": {
                str(cid): {str(uid): d for uid, d in users.items()}
                for cid, users in state.get("sanaydi_data", {}).items()
            },
            "welcome_messages": {str(k): v for k, v in state.get("welcome_messages", {}).items()},
            "group_rules":      {str(k): v for k, v in state.get("group_rules", {}).items()},
            "admin_ids":        list(state.get("admin_ids", [])),
        }
        # Atomik yozish: avval .tmp ga, keyin nomini o'zgartirish
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)
        logger.debug("💾 Ma'lumotlar saqlandi.")
        return True
    except Exception as e:
        logger.error(f"❌ Saqlashda xatolik: {e}")
        return False


def load_data() -> dict:
    """JSON dan ma'lumotlarni yuklash. Fayl yo'q bo'lsa — bo'sh dict."""
    if not os.path.exists(DATA_FILE):
        logger.info("ℹ️ data.json topilmadi — yangi sessiya.")
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        result = {
            "group_settings": {int(k): v for k, v in raw.get("group_settings", {}).items()},
            "user_warns": defaultdict(
                lambda: defaultdict(int),
                {
                    int(cid): defaultdict(int, {int(uid): c for uid, c in w.items()})
                    for cid, w in raw.get("user_warns", {}).items()
                },
            ),
            "sanaydi_data": defaultdict(
                dict,
                {
                    int(cid): {int(uid): d for uid, d in u.items()}
                    for cid, u in raw.get("sanaydi_data", {}).items()
                },
            ),
            "welcome_messages": {int(k): v for k, v in raw.get("welcome_messages", {}).items()},
            "group_rules":      {int(k): v for k, v in raw.get("group_rules", {}).items()},
            "admin_ids":        raw.get("admin_ids", []),
        }
        logger.info("✅ Ma'lumotlar yuklandi.")
        return result
    except Exception as e:
        logger.error(f"❌ Yuklashda xatolik: {e}")
        return {}
