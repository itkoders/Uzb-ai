# UzbAI V2

Telegram AI yordamchi bot — aiogram 3 va Google Gemini API asosida.

## Imkoniyatlar
- Gemini AI orqali savol-javob
- O'zbek tilidagi standart, tarix, geografiya, dasturlash va matematika rejimlari
- Har bir foydalanuvchi uchun so'nggi suhbat konteksti
- SQLite orqali foydalanuvchi va chat tarixini saqlash
- Admin ID orqali cheklangan statistika buyrug'i
- Xabar uzunligi va tez-tez so'rov yuborishga qarshi oddiy cheklovlar

## Ishga tushirish
1. Python 3.11+ o'rnating.
2. `pip install -r requirements.txt`
3. `.env.example` nusxasidan `.env` yarating va qiymatlarni kiriting.
4. `python uzbeai.py` buyrug'ini bajaring.

## Render
Render'da Background Worker yarating. Build: `pip install -r requirements.txt`; Start: `python uzbeai.py`.
Quyidagi Environment qiymatlarini Render dashboard'da maxfiy kiriting: `BOT_TOKEN`, `GEMINI_API_KEY`, `ADMIN_IDS`. API kalitlarini GitHub'ga joylamang.

## Muhim: SQLite va Render
Hozircha alohida PostgreSQL ishlatilmaydi. Render worker'ning oddiy fayl tizimi doimiy saqlash kafolatiga ega emas; restart yoki redeploy paytida SQLite ma'lumotlari yo'qolishi mumkin. Doimiy ma'lumot kerak bo'lsa keyin persistent disk yoki PostgreSQL ulash lozim.

## Xavfsizlik
- Haqiqiy token va API kalitini `.env` yoki Render Environment'da saqlang; repoga yubormang.
- Admin Telegram ID raqamlarini vergul bilan ajrating.
- Ushbu repoda maxfiy kalitlar yo'q.
