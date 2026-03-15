# 🛡️ Universal Qorovul Bot (Universal Guard)

Universal Qorovul Bot - bu guruhlarni har tomonlama himoya qilish, xabarlarni sanash va moderatsiya qilish uchun mo'ljallangan kuchli Telegram bot. Bot orqali guruhingizni spam, reklama va nojo'ya xabarlardan tozalab, a'zolarning faolligini kuzatishingiz mumkin.

## ✨ Xususiyatlari

- **🛡️ Qorovul (Security):**
  - Anti-spam va flood himoyasi.
  - Tashqi havolalarni (link) bloklash.
  - Forward xabarlarni cheklash.
  - Nojo'ya so'zlar filtr (Bad words).
  - Tungi rejim (Night mode) - belgilangan vaqtda guruhni yopish.
  - Arabcha harflar va sticker spam filtrlar.

- **📢 Reklama Tozalash (Ad Cleaner):**
  - Kanal va bot usernamelarini bloklash.
  - Inline reklama tugmalarini o'chirish.
  - Kontakt va joylashuv spamlarini tozalash.
  - Maxsus reklama patternlari bo'yicha filtrlash.

- **📊 Sanoqchi (Message Counter):**
  - Har bir a'zoning xabar sonini hisoblash.
  - Top faol a'zolar ro'yxati (Kunlik, haftalik va umumiy).
  - Guruh statistikasi.

- **👥 Sanaydi (Referral System):**
  - Guruhga odam qo'shganlarni hisoblash.
  - Odam yig'ish bo'yicha Top 10 ro'yxati.
  - Majburiy a'zolik (Kanalga a'zo bo'lmagunicha sanamaslik).

- **📌 Moderatsiya:**
  - Ogohlantirish (Warn) tizimi.
  - Mute, Ban, Kick va TempBan (vaqtli ban).
  - Pin/Unpin buyruqlari.
  - Xush kelibsiz (Welcome) xabarlarini sozlash.

## 🚀 O'rnatish

1. **Repozitoriyani yuklab oling:**
   ```bash
   git clone https://github.com/stormdeveloper-glitch/unversal-bot.git
   cd unversal-bot
   ```

2. **Kutubxonalarni o'rnating:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfiguratsiya:**
   `.env.example` faylini `.env` deb nomlang va ichiga `BOT_TOKEN` va `OWNER_IDS` kabilarni kiriting.

4. **Botni ishga tushiring:**
   ```bash
   python bot.py
   ```

## 📋 Asosiy Buyruqlar

### Moderatsiya
- `/warn` — Ogohlantirish berish.
- `/mute [min]` — Vaqtinchalik yozishni cheklash.
- `/ban` — Guruhdan haydash.
- `/tempban [vaqt]` — Belgilangan vaqtga ban berish (masalan: `1h`, `1d`).

### Sozlamalar
- `/settings` — Sozlamalar panelini ochish.
- `/nightmode` — Tungi rejimni sozlash.
- `/setwelcome` — Xush kelibsiz xabarini o'rnatish.
- `/rules` — Guruh qoidalarini ko'rish/o'rnatish.

### Statistika
- `/me` — Mening statistikamaz.
- `/top` — Eng faol a'zolar.
- `/groupstats` — Guruh umumiy statistikasi.

### Sanaydi
- `/meni` — Qancha odam qo'shganim.
- `/sanaydi_top` — Eng ko'p odam qo'shganlar.

## 🛡️ Arxitektura

- `bot.py` — Botning asosiy ishga tushirish nuqtasi.
- `config.py` — Sozlamalar va filtrlar.
- `handlers/` — Buyruqlar va xabar ishlovchi funksiyalar.
- `data_manager.py` — Ma'lumotlarni saqlash (JSON).

## 📄 Litsenziya

Ushbu loyiha shaxsiy foydalanish uchun yaratilgan.
