import sqlite3
import telebot
from telebot import types

TOKEN = "8659968699:AAHA0Wmsjp6Cf-qtlV8P4D57-Fm0iHX2VbM"
bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        points INTEGER DEFAULT 10
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id INTEGER,
                        channel_username TEXT
                    )''')
    conn.commit()
    conn.close()

init_db()

def get_user_points(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def update_points(user_id, amount):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, points) VALUES (?, 1000)", (user_id,))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    add_user(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_sub = types.KeyboardButton("🔗 تبادل اشتراك")
    btn_points = types.KeyboardButton("💰 رصيد النقاط")
    btn_add = types.KeyboardButton("➕ إضافة قناتي")
    btn_help = types.KeyboardButton("ℹ️ المساعدة")
    markup.add(btn_sub, btn_points, btn_add, btn_help)
    
    bot.send_message(
        message.chat.id, 
        f"أهلاً بك {message.from_user.first_name}! 🚀\nتم منحك 10 نقاط هدية.\nاختر من القائمة للبدء:", 
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    user_id = message.from_user.id
    
    if message.text == "💰 رصيد النقاط":
        pts = get_user_points(user_id)
        bot.reply_to(message, f"💰 رصيدك الحالي: {pts} نقطة.")
        
    elif message.text == "➕ إضافة قناتي":
        pts = get_user_points(user_id)
        if pts < 1:
            bot.reply_to(message, "❌ ليس لديك نقاط كافية لإضافة قناة! اشترك في قنوات أخرى لجمع النقاط.")
            return
        msg = bot.reply_to(message, "أرسل يوزر قناتك العامة الآن مع الـ @ (مثال: @my_channel):\n⚠️ تنبيه: يجب رفع البوت مشرفاً في القناة أولاً ليتأكد من الاشتراكات.")
        bot.register_next_step_handler(msg, process_add_channel)
        
    elif message.text == "🔗 تبادل اشتراك":
        send_next_channel(message)
        
    elif message.text == "ℹ️ المساعدة":
        bot.reply_to(message, "1. أضف البوت مشرفاً في قناتك.\n2. أضف يوزر قناتك للبوت.\n3. اشترك في قنوات الأعضاء لجمع النقاط وترويج قناتك!")

def process_add_channel(message):
    ch_username = message.text.strip()
    if ch_username.startswith("@"):
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO channels (owner_id, channel_username) VALUES (?, ?)", (message.from_user.id, ch_username))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ تم إضافة القناة {ch_username} بنجاح!\nسيتم خصم نقطة مع كل مشترك جديد يأتيك.")
    else:
        bot.reply_to(message, "❌ يوزر غير صحيح! أرسل اليوزر يبدأ بـ @")

def send_next_channel(message):
    user_id = message.from_user.id
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, owner_id, channel_username FROM channels WHERE owner_id != ? LIMIT 1", (user_id,))
    ch = cursor.fetchone()
    conn.close()
    
    if ch:
        ch_id, owner_id, ch_username = ch
        owner_pts = get_user_points(owner_id)
        
        if owner_pts < 1:
            send_next_channel(message)
            return

        markup = types.InlineKeyboardMarkup()
        btn_link = types.InlineKeyboardButton("🔗 الانتقال للقناة", url=f"https://t.me/{ch_username[1:]}")
        btn_verify = types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data=f"check_{ch_username}_{owner_id}")
        markup.add(btn_link)
        markup.add(btn_verify)
        
        bot.send_message(message.chat.id, f"اشترك في القناة التالية للحصول على +1 نقطة:\n👉 {ch_username}", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "لا توجد قنوات متاحة للتبادل حالياً! جرب لاحقاً.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def verify_subscription(call):
    _, ch_username, owner_id = call.data.split("_")
    user_id = call.from_user.id
    
    try:
        member = bot.get_chat_member(ch_username, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            update_points(user_id, 1)
            update_points(int(owner_id), -1)
            bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح! حصلت على +1 نقطة.", show_alert=True)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_next_channel(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد!", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠️ تأكد أن البوت مرفوع مشرفاً في تلك القناة للتحقق!", show_alert=True)

print("Bot is running online 24/7...")
bot.infinity_polling()

# أمر سري للأدمن لإضافة نقاط لنفسه
# الاستخدام في تليجرام: addpoints 500/
@bot.message_handler(commands=['addpoints'])
def add_points_admin(message):
    # ضع آيدي تليجرام الخاص بك هنا ليصبح الأمر لك وحدك
    ADMIN_ID = message.from_user.id  

    if message.from_user.id == ADMIN_ID:
        try:
            amount = int(message.text.split()[1])
            conn = sqlite3.connect("bot_database.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, message.from_user.id))
            conn.commit()
            conn.close()
            bot.reply_to(message, f"تمت إضافة {amount} نقطة لحسابك بنجاح! 🎉")
        except:
            bot.reply_to(message, "اكتب الأمر هكذا: /addpoints 500")
