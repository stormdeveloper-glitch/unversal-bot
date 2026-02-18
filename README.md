# 🛡️ Universal Qorovul Bot — Telegram Guruh Himoyachisi

Guruhingizni har tomonlama himoya qiladigan, xabarlarni sanaydigan va reklamalarni tozalaydigan universal Telegram bot.

## ✨ Xususiyatlar

### 🛡️ Qorovul (Guard)
| Xususiyat | Tavsif |
|-----------|--------|
| Anti-Spam | Flood/spam xabarlarni aniqlash va cheklash |
| Anti-Link | Tashqi havolalarni bloklash |
| Anti-Forward | Boshqa kanallardan forward bloklash |
| Captcha | Yangi a'zolarga matematik tekshiruv |
| So'z Filtri | Nojo'ya so'zlarni avtomatik o'chirish |
| Tungi Rejim | Belgilangan vaqtda faqat adminlar yozadi |
| Warn Tizimi | 3 ta ogohlantirish = avtomatik ban |
| Anti-Sticker | Sticker/GIF spam himoyasi |
| Anti-Arab | Arab yozuvini bloklash (ixtiyoriy) |
| Media Cheklovi | Yangi a'zolarga media taqiqlash |

### 📢 Reklama Tozalash (Ad Cleaner)
| Xususiyat | Tavsif |
|-----------|--------|
| Anti-@kanal | @kanal_nomi va @bot_nomi aniqlash |
| Anti-Inline | Reklama inline tugmalarni bloklash |
| Anti-Kontakt | Kontakt spam aniqlash |
| Anti-Joylashuv | Joylashuv spam bloklash |
| Anti-Forward Spam | Ko'p forward = reklama |
| Anti-Kanal Bot | Kanaldan yozuvchi botlarni bloklash |
| Ad Patterns | O'zbek/Rus/Ingliz reklama matnlarni aniqlash |

### 📊 Sanoqchi (Counter)
| Xususiyat | Tavsif |
|-----------|--------|
| /count | Foydalanuvchi xabar statistikasi |
| /me | O'z statistikangiz |
| /top | Top faol a'zolar (jami) |
| /toptoday | Bugungi top |
| /topweek | Haftalik top |
| /groupstats | Guruh umumiy statistikasi |

## 🚀 O'rnatish

```bash
# 1. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 2. config.py da tokenni kiriting
# Token olish: @BotFather -> /newbot

# 3. Botni ishga tushiring
python bot.py
```

## 📋 Barcha Buyruqlar

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Bot haqida |
| `/help` | Buyruqlar ro'yxati |
| `/settings` | Inline sozlamalar paneli |
| `/warn` | Ogohlantirish (reply) |
| `/mute [daqiqa]` | Ovozni o'chirish (reply) |
| `/unmute` | Ovozni yoqish (reply) |
| `/ban` | Ban qilish (reply) |
| `/unban` | Unban qilish (reply) |
| `/kick` | Chiqarish (reply) |
| `/warns` | Ogohlantirishlar (reply) |
| `/clearwarns` | Tozalash (reply) |
| `/nightmode` | Tungi rejim |
| `/addword` | Taqiqlangan so'z qo'shish |
| `/delword` | Taqiqlangan so'z o'chirish |
| `/log` | Oxirgi harakatlar |
| `/stats` | Bot statistikasi |
| `/count` | Xabar soni (reply) |
| `/me` | O'z statistikam |
| `/top [son]` | Top a'zolar |
| `/toptoday` | Bugungi top |
| `/topweek` | Haftalik top |
| `/groupstats` | Guruh statistikasi |

## 📁 Fayl Tuzilmasi

```
├── bot.py          # Asosiy bot (qorovul)
├── counter.py      # Sanoqchi moduli
├── ad_cleaner.py   # Reklama tozalagich moduli
├── config.py       # Konfiguratsiya va sozlamalar
├── bad_words.json  # Taqiqlangan so'zlar
├── requirements.txt
└── README.md
```
