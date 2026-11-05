# Abu Rayhon Beruniy nomidagi Urganch davlat akademik litseyi
## Professional Telegram Murojaatlar Tizimi va Administrator Web-Paneli

Ushbu tizim litsey o‘quvchilari, ota-onalar, o‘qituvchilar va fuqarolarning litsey rahbariyatiga murojaat, taklif, ariza va shikoyatlarini qabul qilish, ro‘yxatga olish, mas'ul xodimlarga taqsimlash, holatlarini nazorat qilish hamda batafsil hisobot va statistikalar yuritish uchun mo‘ljallangan to‘liq avtomatlashtirilgan professional dasturiy majmuadir.

> ⚠️ **Muhim qoida:** Tizimda anonim murojaatlar qabul qilinmaydi. Har bir murojaat yuboruvchining shaxsiy ma'lumotlari (F.I.Sh., telefon raqami, fuqaro toifasi) majburiy tartibda olinadi va tasdiqlangach bazaga kiritiladi.

---

## 1. Asosiy Texnologiyalar

- **Dasturlash tili:** Python 3.11+
- **Telegram Bot Framework:** aiogram 3.x (FSM, Router, Middleware, Callback Data)
- **Ma'lumotlar bazasi:** PostgreSQL 16 (JSONB, Tranzaksiyalar, Indekslar)
- **ORM & Migratsiyalar:** SQLAlchemy 2.0 (Asinxron) & Alembic
- **Kesh & Sessiyalar:** Redis 7 (aiogram RedisStorage, Rate Limiting, OTP kesh)
- **Web Administrator Paneli:** FastAPI + Uvicorn (Asinxron REST API)
- **Frontend Interfeysi:** Zamonaviy Responsive Dashboard (Tailwind CSS, Vue 3, Chart.js)
- **Hisobot generatorlari:** OpenPyXL (Excel .xlsx) va ReportLab (PDF)
- **Konteynerlashtirish:** Docker va Docker Compose

---

## 2. Loyiha Arxitekturasi

```text
urganch_murojaat_bot/
├── app/
│   ├── admin/
│   │   └── templates/
│   │       └── index.html         # Responsive Administrator Dashboard SPA (Vue 3 + Tailwind)
│   ├── api/                       # FastAPI REST API endpointlari
│   │   ├── appeals.py             # Murojaatlar (filtr, saralash, biriktirish, javob yozish)
│   │   ├── audit.py               # Audit jurnali (xavfsizlik loglari)
│   │   ├── auth.py                # Telegram OTP orqali xavfsiz autentifikatsiya
│   │   ├── deps.py                # Dependency injection, JWT, RBAC huquqlar tekshiruvi
│   │   ├── reports.py             # Excel va PDF eksport
│   │   ├── settings.py            # Bot matnlari va sozlamalarini boshqarish
│   │   ├── staff.py               # Xodimlar va mas'ullarni boshqarish
│   │   ├── stats.py               # Dashboard ko'rsatkichlari va tahliliy ma'lumotlar
│   │   └── users.py               # Telegram bot foydalanuvchilarini nazorat qilish
│   ├── bot/                       # Telegram Bot yadrosi
│   │   ├── dispatcher.py          # aiogram Dispatcher va middleware'lar
│   │   ├── middlewares.py         # Throttling (Spam himoya), DB sessiya, Shaxsiy chat filtri
│   │   └── runner.py              # Botni ishga tushiruvchi modul
│   ├── database/                  # Ma'lumotlar bazasi yadrosi
│   │   ├── base.py                # DeclarativeBase, TimestampMixin
│   │   └── session.py             # Asinxron sessionmaker va tranzaksiya boshqaruvi
│   ├── handlers/                  # aiogram handlerlari
│   │   ├── _files.py              # Fayllarni tekshirish va FSMga qo'shish yordamchisi
│   │   ├── appeal.py              # 8 bosqichli yangi murojaat yuborish jarayoni
│   │   ├── errors.py              # Xatoliklarni qayta ishlash
│   │   ├── followup.py            # Qo'shimcha ma'lumot so'ralganda javob berish
│   │   ├── my_appeals.py          # Mening murojaatlarim va paginatsiya
│   │   ├── start.py               # /start, /help, /cancel, Biz haqimizda, Bog'lanish
│   │   └── status.py              # Raqam bo'yicha murojaat holatini tekshirish
│   ├── keyboards/                 # Klaviaturalar
│   │   ├── inline.py              # Inline tugmalar va CallbackData fabrika
│   │   └── reply.py               # Bosh menyu va navigatsiya reply tugmalari
│   ├── models/                    # SQLAlchemy ma'lumotlar modellari
│   │   ├── appeal.py              # Appeal, AppealMessage, Attachment, AppealStatusHistory
│   │   ├── audit.py               # AuditLog va Setting modellari
│   │   ├── staff.py               # Staff modeli (Super admin, Admin, Xodim)
│   │   └── user.py                # Telegram User modeli
│   ├── services/                  # Biznes-mantiq servis qatlami
│   │   ├── appeal_service.py      # Murojaatlar biznes-mantig'i
│   │   ├── audit_service.py       # Tizim harakatlarini auditga yozish
│   │   ├── auth_service.py        # Telegram OTP generatsiyasi, JWT, Cookie
│   │   ├── notification_service.py# Telegram orqali xabarnomalar yuborish
│   │   ├── permissions.py         # RBAC rollar asosida ruxsat berish
│   │   ├── report_service.py      # Excel va PDF hisobot generatsiyasi
│   │   ├── settings_service.py    # Tizim sozlamalari (Redis kesh bilan)
│   │   ├── staff_service.py       # Xodimlarni boshqarish
│   │   ├── stats_service.py       # Dashboard ko'rsatkichlari va grafiklar
│   │   └── user_service.py        # Foydalanuvchilar boshqaruvi
│   ├── states/                    # FSM holatlari (AppealForm, CheckStatus, FollowUp)
│   ├── utils/                     # Yordamchi modullar
│   │   ├── appeal_text.py         # Xabarlar matnini formatlash
│   │   ├── enums.py               # Holatlar, toifalar, rollar enumlari
│   │   ├── files.py               # Fayl turlari va hajmini tekshirish
│   │   ├── formatting.py          # Xavfsiz HTML, sana va vaqt formatlash
│   │   ├── locks.py               # Parallel so'rovlarni boshqarish
│   │   ├── rate_limit.py          # Redis rate limiter
│   │   ├── texts.py               # Standart bot xabarlari matnlari
│   │   └── validators.py          # Ism, telefon, mavzu validatsiyasi
│   └── web_app.py                 # FastAPI Web ilovasi
├── config/
│   └── settings.py                # Pydantic-settings konfiguratsiyasi
├── deploy/
│   ├── backup.sh                  # PostgreSQL avtomatik zaxira olish skripti
│   └── nginx.conf                 # Production Nginx konfiguratsiyasi
├── migrations/                    # Alembic migratsiyalari
├── tests/                         # Avtomatlashtirilgan testlar (17 ta to'liq test)
├── .env.example                   # Muhit o'zgaruvchilari namunasi
├── bot_main.py                    # Alohida bot ishga tushirish skripti
├── docker-compose.yml             # Docker compose konfiguratsiyasi
├── Dockerfile                     # Docker konteyner fayli
├── main.py                        # Yagona ishga tushirish nuqtasi (Bot + Web)
├── requirements.txt               # Bog'liqliklar ro'yxati
└── web_main.py                    # Alohida web panel ishga tushirish skripti
```

---

## 3. Asosiy Funksiyalar va Imkoniyatlar

### Foydalanuvchi (Telegram Bot):
1. **8 bosqichli qat'iy tekshiruvli murojaat yuborish:**
   - F.I.Sh. (kamida 2 so'z, faqat harflar).
   - Telefon raqami (Telegram Contact tugmasi yoki qo'lda `+998XXXXXXXXX`).
   - Foydalanuvchi toifasi: *O‘quvchi, O‘qituvchi, Ota-ona, Boshqa fuqaro*.
   - Murojaat yo‘nalishi: *Ta'lim sifati, O‘qituvchilar faoliyati, O‘quvchilar masalalari, Sharoit va infratuzilma, Taklif, Shikoyat, Boshqa masalalar*.
   - Murojaat mavzusi (5–200 belgi).
   - Batafsil matn (20–3500 belgi).
   - Rasm, video, PDF va hujjatlarni biriktirish (ko'pi bilan 5 ta, 20 MB gacha). Xavfli kengaytmalar (.exe, .bat, .js va b.) to'liq bloklangan.
   - Barcha ma'lumotlarni ko'rib chiqish va tasdiqlash.
2. **Noyob Murojaat ID tizimi:**
   - Har bir murojaatga `URG-2026-000001` formatida atomar takrorlanmas raqam beriladi.
3. **Murojaatim holatini tekshirish:**
   - Raqam orqali istalgan vaqtda murojaatning joriy holati va tarixini bilish.
4. **Mening murojaatlarim:**
   - Foydalanuvchi o'zining barcha yuborgan murojaatlarini qulay sahifalab ko'rishi mumkin.
5. **Qo‘shimcha ma'lumot yuborish:**
   - Agar mas'ul xodim qo'shimcha ma'lumot so'rasa, foydalanuvchi botdagi «✍️ Javob yozish» tugmasi orqali to'g'ridan-to'g'ri o'sha murojaatga qo'shimcha matn va fayllar biriktirib yubora oladi.
6. **Avtomatik xabarnomalar:**
   - Holat o'zgarganda (Qabul qilindi, Ko'rib chiqilmoqda, Hal qilindi, Rad etildi) foydalanuvchiga Telegram orqali xabar yuboriladi.

### Administrator Web-Paneli (Dashboard):
1. **Xavfsiz Kirish (Telegram OTP):**
   - Parol talab qilinmaydi. Xodim Telegram ID sini kiritadi -> Bot unga 6 xonali bir martalik tasdiqlash kodi yuboradi -> Kod kiritilgach HttpOnly xavfsiz JWT sessiya ochiladi.
2. **Dashboard va Statistik grafiklar:**
   - Murojaatlar dinamikasi (kunlik, haftalik, oylik chiziqli grafik).
   - Yo'nalishlar bo'yicha taqsimot (aylana diagramma).
   - Xodimlar samaradorligi: biriktirilgan, hal qilingan, rad etilgan, jarayonda va yakunlash foizi %.
   - O'rtacha javob berish va o'rtacha hal qilish vaqtlari.
3. **Murojaatlarni to'liq boshqarish:**
   - Tezkor qidiruv (raqam, ism, telefon, matn).
   - Kengaytirilgan filtrlar (holat, yo'nalish, sana oralig'i, xodim).
   - Murojaatni mas'ul xodimga biriktirish.
   - Holatni o'zgartirish (izoh bilan).
   - Fuqaroga rasmiy javob yozish (to'g'ridan-to'g'ri fuqaroning Telegramiga yetkaziladi).
   - Fuqarodan qo'shimcha ma'lumot so'rash.
   - Biriktirilgan fayllarni (hujjat, rasm, video) ko'rish va yuklab olish.
4. **Xodimlarni boshqarish (RBAC):**
   - **Super Admin:** barcha sozlamalar, boshqa adminlar, xodimlar va ma'lumotlarni to'liq boshqaradi.
   - **Administrator:** barcha murojaatlarni ko'radi, mas'ullarga biriktiradi, hisobotlarni yuklab oladi.
   - **Mas'ul xodim:** faqat o'ziga biriktirilgan murojaatlarni ko'radi va ularga javob yozadi.
5. **Hisobotlarni eksport qilish:**
   - **Excel (.xlsx):** Barcha ustunlar, avtofiltr, chiroyli ranglar va alohida statistik varaq bilan.
   - **PDF (.pdf):** Rasmiy litsey blanki ko'rinishidagi landshaft tahliliy hisobot.
6. **Audit Jurnali:**
   - Har bir harakat (tizimga kirish, holat o'zgartirish, javob yozish, hisobot yuklab olish) ishtirokchi, IP-manzil va vaqt bilan saqlanadi.

---

## 4. O'rnatish va Ishga Tushirish

### 1-usul: Docker va Docker Compose (Tavsiya etiladi - Production/VPS uchun)

Docker o'rnatilgan VPS serverda tizimni 2 daqiqada ishga tushirish mumkin:

1. Loyiha papkasiga kiring:
   ```bash
   cd urganch_murojaat_bot
   ```

2. `.env` faylida o'zingizning Telegram ID raqamingizni `SUPER_ADMIN_IDS` ga yozing:
   ```env
   BOT_TOKEN=9143648687:AAFzGYojS7SpugHcJVgVCRUurh5ZETPPlcc
   SUPER_ADMIN_IDS=SIZNING_TELEGRAM_ID
   SECRET_KEY=ixtiyoriy-uzun-maxfiy-kalit-belgilari
   ```

3. Konteynerlarni bir buyruq bilan yig'ing va ishga tushiring:
   ```bash
   docker compose up -d --build
   ```

4. Konteynerlar holatini tekshirish:
   ```bash
   docker compose ps
   ```

5. Loglarni ko'rish:
   ```bash
   docker compose logs -f
   ```

Web-panelga kirish: `http://SERVER_IP:8000/admin`

---

### 2-usul: Lokal kompyuterda ishga tushirish (Windows / Linux)

#### Windows uchun:
1. Virtual muhit yaratish va faollashtirish:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Bog'liqliklarni o'rnatish:
   ```powershell
   pip install -r requirements.txt
   ```

3. `.env` faylini to'g'rilash (PostgreSQL va Redis manzillari). Agar SQLite ishlatmoqchi bo'lsangiz:
   ```env
   DATABASE_URL=sqlite+aiosqlite:///./murojaat.db
   REDIS_URL=redis://localhost:6379/0
   ```

4. Bot va Web panelni bir vaqtda ishga tushirish:
   ```powershell
   python main.py
   ```
   *Yoki faqat botni: `python bot_main.py`*
   *Yoki faqat web-panelni: `python web_main.py`*

#### Linux / Ubuntu uchun:
1. Paketlar va shriftlarni o'rnatish:
   ```bash
   sudo apt update
   sudo apt install -y python3-venv python3-pip fonts-dejavu-core postgresql redis-server
   ```

2. Virtual muhitni yoqish:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Ishga tushirish:
   ```bash
   python main.py
   ```

---

## 5. Administrator Paneliga Kirish Qadamlari

1. Brauzerda oching: `http://localhost:8000/admin` (yoki server IP manzili).
2. `.env` faylidagi `SUPER_ADMIN_IDS` ga kiritilgan Telegram ID raqamingizni yozing.
3. «Tasdiqlash kodini olish» tugmasini bosing.
4. Telegramda `@litseymurojaatbot` sizga 6 xonali kod yuboradi.
5. Kodni kiritib, «Tizimga kirish» tugmasini bosing.

---

## 6. Nginx va SSL Sozlash (Production)

Litsenziyali yoki o'z domeningiz bo'lsa, `deploy/nginx.conf` faylidan foydalaning:

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/murojaat.conf
sudo ln -s /etc/nginx/sites-available/murojaat.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Bepul SSL sertifikat o'rnatish:
```bash
sudo certbot --nginx -d murojaat.litsey.uz
```

---

## 7. Avtomatik Zaxira Nusxasi (Backup)

`deploy/backup.sh` skriptini har kuni kechasi soat 02:00 da avtomatik ishga tushirish uchun crontab ga qo'shing:

```bash
chmod +x deploy/backup.sh
crontab -e
```
Quyidagi satrni qo'shing:
```cron
0 2 * * * /path/to/urganch_murojaat_bot/deploy/backup.sh >> /var/log/murojaat_backup.log 2>&1
```

---

## 8. Testlarni Ishga Tushirish

Loyihadagi barcha funksiyalar (validatsiya, xizmatlar, RBAC huquqlari, API endpointlari) unit testlar bilan qoplangan:

```bash
pytest tests -v
```

Natija:
```text
============================= 17 passed in 1.07s ==============================
```

---

## Muallif va Qo‘llab-quvvatlash

- **Tashkilot:** Abu Rayhon Beruniy nomidagi Urganch davlat akademik litseyi
- **Telegram Bot:** [@litseymurojaatbot](https://t.me/litseymurojaatbot)
- **Status:** Ishga tushirishga to'liq tayyor (Production Ready)
# Anonim-murojaattt
