"""UzbAI V2 Telegram bot: aiogram 3 + Google Gemini + SQLite."""
import asyncio, logging, os, sqlite3, time
from pathlib import Path
from html import escape
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from google import genai

BOT_TOKEN=os.environ["BOT_TOKEN"].strip()
GEMINI_API_KEY=os.environ["GEMINI_API_KEY"].strip()
MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash").strip()
ADMIN_IDS={int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip()}
DB=Path(os.getenv("DB_PATH","uzbai_data.db"))
if not BOT_TOKEN or not GEMINI_API_KEY or not ADMIN_IDS:
    raise RuntimeError("BOT_TOKEN, GEMINI_API_KEY va ADMIN_IDS sozlanishi shart.")

logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO"),format="%(asctime)s %(levelname)s %(message)s")
log=logging.getLogger("uzbai")
bot=Bot(BOT_TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp=Dispatcher()
gemini=genai.Client(api_key=GEMINI_API_KEY)
last_request={}
MODES={
 "standart":"Sen UzbAI nomli muloyim va aniq o'zbek AI yordamchisisan. Foydalanuvchi tilida javob ber.",
 "tarix":"Sen tarix o'qituvchisisan. Tarixiy fakt va sanalarni aniq tushuntir.",
 "geografiya":"Sen geografiya o'qituvchisisan. Geografik mavzularni sodda tushuntir.",
 "dasturlash":"Sen dasturlash murabbiyisan. Kodni xavfsiz, tushunarli va bosqichma-bosqich tushuntir.",
 "matematika":"Sen matematika o'qituvchisisan. Masalalarni bosqichma-bosqich yechib tushuntir."
}
def db():
    DB.parent.mkdir(parents=True,exist_ok=True)
    return sqlite3.connect(DB,timeout=20)
def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,mode TEXT DEFAULT 'standart',banned INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,role TEXT,content TEXT)")
def register(m):
    with db() as c:
        c.execute("INSERT INTO users(id,name) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name",(m.from_user.id,m.from_user.full_name))
def user_info(uid):
    with db() as c: return c.execute("SELECT mode,banned FROM users WHERE id=?",(uid,)).fetchone()
def history(uid):
    with db() as c: rows=c.execute("SELECT role,content FROM history WHERE user_id=? ORDER BY id DESC LIMIT 12",(uid,)).fetchall()
    return [{"role":r,"parts":[{"text":t}]} for r,t in reversed(rows)]
def save_turn(uid,prompt,answer):
    with db() as c:
        c.executemany("INSERT INTO history(user_id,role,content) VALUES(?,?,?)",[(uid,"user",prompt),(uid,"model",answer)])
        c.execute("DELETE FROM history WHERE user_id=? AND id NOT IN (SELECT id FROM history WHERE user_id=? ORDER BY id DESC LIMIT 20)",(uid,uid))
@dp.message(CommandStart())
async def start(m:Message):
    register(m)
    await m.answer("🤖 <b>UzbAI V2</b> ga xush kelibsiz!\nGemini AI yordamida savollaringizga javob beraman.\n\n/mode — rejimlar\n/clear — suhbatni tozalash\n/help — yordam")
@dp.message(Command("help"))
async def help_cmd(m:Message):
    await m.answer("<b>Buyruqlar</b>\n/mode — rejimni tanlash\n/setmode dasturlash — rejimni almashtirish\n/clear — tarixni tozalash\n/admin — admin statistikasi")
@dp.message(Command("mode"))
async def mode_cmd(m:Message):
    await m.answer("Mavjud rejimlar: "+", ".join(MODES)+"\nMisol: /setmode tarix")
@dp.message(Command("setmode"))
async def setmode(m:Message):
    p=(m.text or "").split(maxsplit=1)
    if len(p)!=2 or p[1].lower() not in MODES:
        await m.answer("Rejim: "+", ".join(MODES)); return
    register(m)
    with db() as c: c.execute("UPDATE users SET mode=? WHERE id=?",(p[1].lower(),m.from_user.id))
    await m.answer("✅ Rejim o'zgardi: <b>"+escape(p[1].lower())+"</b>")
@dp.message(Command("clear"))
async def clear(m:Message):
    with db() as c: c.execute("DELETE FROM history WHERE user_id=?",(m.from_user.id,))
    await m.answer("🧹 Suhbat tarixi tozalandi.")
@dp.message(Command("admin"))
async def admin(m:Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("⛔ Ruxsat yo'q."); return
    with db() as c:
        count=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        banned=c.execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]
    await m.answer(f"🛠 <b>UzbAI admin</b>\nFoydalanuvchilar: {count}\nBloklangan: {banned}")
@dp.message(F.text,F.chat.type=="private")
async def chat(m:Message):
    uid=m.from_user.id
    register(m)
    info=user_info(uid)
    if info and info[1]:
        await m.answer("⛔ Botdan foydalanish cheklangan."); return
    prompt=(m.text or "").strip()
    if not prompt: return
    if len(prompt)>12000:
        await m.answer("Xabar 12 000 belgidan oshmasin."); return
    now=time.monotonic()
    if now-last_request.get(uid,0)<2:
        await m.answer("⏳ Iltimos, biroz kuting."); return
    last_request[uid]=now
    mode=info[0] if info else "standart"
    contents=history(uid)+[{"role":"user","parts":[{"text":prompt}]}]
    try:
        await bot.send_chat_action(m.chat.id,ChatAction.TYPING)
        result=await gemini.aio.models.generate_content(model=MODEL,contents=contents,config={"system_instruction":MODES.get(mode,MODES["standart"]),"temperature":0.7})
        answer=(result.text or "").strip() or "Javob yaratilmadi. Qayta urinib ko'ring."
        save_turn(uid,prompt,answer)
        for start in range(0,len(answer),3900): await m.answer(escape(answer[start:start+3900]))
    except Exception as e:
        log.exception("Gemini error for user %s",uid)
        kind=type(e).__name__.lower()
        if "quota" in kind or "resourceexhausted" in kind: msg="Gemini API limiti vaqtincha tugadi."
        elif "permission" in kind or "unauthenticated" in kind: msg="Gemini API kalitini tekshirish kerak."
        else: msg="AI xizmatida vaqtinchalik xatolik. Keyinroq urinib ko'ring."
        await m.answer("⚠️ "+msg)
async def health_handler(reader, writer):
    try:
        await reader.read(1024)
        body = b"UzbAI is running"
        writer.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + body
        )
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    init_db()
    port = int(os.getenv("PORT", "10000"))
    server = await asyncio.start_server(health_handler, "0.0.0.0", port)
    log.info("UzbAI web health server listening on port %s", port)
    log.info("UzbAI Telegram bot started: model=%s", MODEL)
    try:
        async with server:
            await dp.start_polling(bot)
    finally:
        server.close()
        await server.wait_closed()
        await bot.session.close()
        await gemini.aio.aclose()

if __name__=="__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt,SystemExit): log.info("Bot stopped.")
