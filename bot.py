import sqlite3
import telebot
from telebot import types

# التوكن
TOKEN = "8659968699:AAHA0Wmsjp6Cf-qtlV8P4D57-Fm0iHX2VbM"
bot = telebot.TeleBot(TOKEN)

# تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        points INTEGER DEFAULT 1000
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id INTEGER,
                        channel_username TEXT UNIQUE
                    )''')
    conn.commit()
    conn.close()

init_db()

# القائمة الرئيسية
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🔗 تبادل اشتراك")
    btn2 = types.KeyboardButton("💰 رصيد النقاط")
    btn3 = types.KeyboardButton("➕ إضافة قناتي")
    btn4 = types.KeyboardButton("ℹ️ المساعدة")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# أمر التشغيل /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.clear_step_handler(message)
    user_id = message.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (user_id, points) VALUES (?, 1000)", (user_id,))
        conn.commit()
        msg = f"أهلاً بك {message.from_user.first_name}! 🚀\nتم إضافة 1000 نقطة هدية للبدء.\nاختر من القائمة للبدء:"
    else:
        msg = f"مرحباً بك مجدداً {message.from_user.first_name}! 👋\nاختر من القائمة بالأسفل:"
        
    conn.close()
    bot.send_message(message.chat.id, msg, reply_markup=main_keyboard())

# زر رصيد النقاط
@bot.message_handler(func=lambda message: message.text == "💰 رصيد النقاط")
def check_points(message):
    bot.clear_step_handler(message)
    user_id = message.from_user.id
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    points = row[0] if row else 0
    bot.reply_to(message, f"💰 رصيدك الحالي: {points} نقطة.")

# زر المساعدة
@bot.message_handler(func=lambda message: message.text == "ℹ️ المساعدة")
def help_message(message):
    bot.clear_step_handler(message)
    text = ("ℹ️ **كيفية استخدام البوت:**\n\n"
            "1. أضف البوت مشرفاً في قناتك.\n"
            "2. اضغط على **➕ إضافة قناتي** وادخل يوزر القناة (مثال: @my_channel).\n"
            "3. اشترك في قنوات الأعضاء من زر **🔗 تبادل اشتراك** لجمع النقاط وتطوير قناتك!")
    bot.reply_to(message, text, parse_mode="Markdown")

# زر إضافة قناتي
@bot.message_handler(func=lambda message: message.text == "➕ إضافة قناتي")
def add_channel_start(message):
    bot.clear_step_handler(message)
    user_id = message.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    points = row[0] if row else 0
    # الشرط المعدل: يسمح بمرور أي شخص يمتلك نقطة واحدة على الأقل
    if points < 1:
        bot.reply_to(message, "❌ ليس لديك نقاط كافية لإضافة قناة! اشترك في قنوات أخرى لجمع النقاط.")
        return

    msg = bot.reply_to(message, "أرسل يوزر قناتك العامة الآن مع الـ @ (مثال: @my_channel):\n\n⚠️ تنبيه: يجب رفع البوت مشرفاً في القناة أولاً ليتمكن من التأكد من الاشتراكات.")
    bot.register_next_step_handler(msg, process_channel_username)

def process_channel_username(message):
    if message.text in ["🔗 تبادل اشتراك", "💰 رصيد النقاط", "➕ إضافة قناتي", "ℹ️ المساعدة"]:
        return
        
    username = message.text.strip()
    if not username.startswith("@"):
        bot.reply_to(message, "❌ يوزر غير صحيح! أرسل اليوزر يبدأ بـ @")
        return

    user_id = message.from_user.id
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO channels (owner_id, channel_username) VALUES (?, ?)", (user_id, username))
        conn.commit()
        bot.reply_to(message, f"✅ تم إضافة القناة {username} بنجاح!\nسيتم خصم نقطة مع كل مشترك جديد يأتيك.")
    except sqlite3.IntegrityError:
        bot.reply_to(message, "⚠️ هذه القناة مضافة بالفعل في النظام!")
    finally:
        conn.close()

# زر تبادل اشتراك
@bot.message_handler(func=lambda message: message.text == "🔗 تبادل اشتراك")
def exchange_subs(message):
    bot.clear_step_handler(message)
    user_id = message.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, channel_username, owner_id FROM channels WHERE owner_id != ? LIMIT 1", (user_id,))
    channel = cursor.fetchone()
    conn.close()

    if not channel:
        bot.reply_to(message, "لا توجد قنوات متاحة للتبادل حالياً! جرب لاحقاً.")
        return

    ch_id, ch_username, ch_owner = channel
    markup = types.InlineKeyboardMarkup()
    btn_link = types.InlineKeyboardButton("📢 دخول القناة", url=f"https://t.me/{ch_username.replace('@', '')}")
    btn_check = types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data=f"check_{ch_id}_{ch_username}_{ch_owner}")
    markup.add(btn_link)
    markup.add(btn_check)

    bot.send_message(message.chat.id, f"اشترك في القناة التالية للحصول على نقطة:\n👉 {ch_username}", reply_markup=markup)

# التحقق من الاشتراك
@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def callback_check_sub(call):
    _, ch_id, ch_username, ch_owner = call.data.split("_")
    user_id = call.from_user.id
    ch_owner = int(ch_owner)

    try:
        member = bot.get_chat_member(ch_username, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            conn = sqlite3.connect("bot_database.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (user_id,))
            cursor.execute("UPDATE users SET points = points - 1 WHERE user_id = ?", (ch_owner,))
            conn.commit()
            conn.close()

            bot.answer_callback_query(call.id, "✅ تم التحقق! تم منحك 1 نقطة.")
            bot.edit_message_text("✅ تم الاشتراك وحصلت على 1 نقطة!", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد!", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠️ تأكد من رفع البوت مشرفاً في القناة أولاً!", show_alert=True)

# أمر سري للأدمن لشحن النقاط (/addpoints 500)
@bot.message_handler(commands=['addpoints'])
def add_points_admin(message):
    try:
        amount = int(message.text.split()[1])
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # التأكد من وجود المستخدم في قاعدة البيانات أولاً قبل تحديث النقاط
        cursor.execute("INSERT OR IGNORE INTO users (user_id, points) VALUES (?, 0)", (message.from_user.id,))
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, message.from_user.id))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🎉 تمت إضافة {amount} نقطة لحسابك بنجاح!")
    except Exception as e:
        bot.reply_to(message, "اكتب الأمر هكذا: /addpoints 500")

# تشغيل البوت
bot.infinity_polling()
