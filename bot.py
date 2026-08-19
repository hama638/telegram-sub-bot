import sqlite3
import telebot
from telebot import types

TOKEN = "8659968699:AAHA0Wmsjp6Cf-qtlV8P4D57-Fm0iHX2VbM"
MUST_JOIN_CHANNEL="@ExchangesubscriptionsZ"  # غيّر هذا بيوزر قناتك الأساسية (مع الـ @)

bot = telebot.TeleBot(TOKEN)

# تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        points INTEGER DEFAULT 0,
                        referred_by INTEGER
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id INTEGER,
                        channel_username TEXT UNIQUE
                    )''')
    conn.commit()
    conn.close()

init_db()

# فحص الاشتراك الإجباري
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(MUST_JOIN_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return True  # في حال كان هناك خطأ في الوصول للقناة يتيح للمستخدم المرور

# القائمة الرئيسية
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🚀 تجميع النقاط")
    btn2 = types.KeyboardButton("🎁 رابط الدعوة")
    btn3 = types.KeyboardButton("➕ إضافة قناتي")
    btn4 = types.KeyboardButton("💰 رصيد النقاط")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# /start مع نظام الاشتراك الإجباري والإحالة
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.clear_step_handler(message)
    user_id = message.from_user.id
    
    # فحص الاشتراك الإجباري أولاً
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        btn_channel = types.InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{MUST_JOIN_CHANNEL.replace('@', '')}")
        btn_check = types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_must_join")
        markup.add(btn_channel)
        markup.add(btn_check)
        bot.send_message(message.chat.id, f"⚠️ عذراً عزيزي، عليك الاشتراك بقناة البوت الرسمية لتتمكن من استخدامه:\n{MUST_JOIN_CHANNEL}", reply_markup=markup)
        return

    # معالجة رابط الدعوة
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        # تسجيل مستخدم جديد
        cursor.execute("INSERT INTO users (user_id, points, referred_by) VALUES (?, 10, ?)", (user_id, referrer_id))
        
        # مكافأة الشخص الذي دعاه بـ 20 نقطة
        if referrer_id and referrer_id != user_id:
            cursor.execute("UPDATE users SET points = points + 20 WHERE user_id = ?", (referrer_id,))
            try:
                bot.send_message(referrer_id, "🎉 قام شخص بالدخول عبر رابطك وحصلت على +20 نقطة!")
            except Exception:
                pass
        conn.commit()
        msg = f"أهلاً بك {message.from_user.first_name}! 🚀\nتم منحك 10 نقاط هدية للبدء."
    else:
        msg = f"مرحباً بك مجدداً {message.from_user.first_name}! 👋"

    conn.close()
    bot.send_message(message.chat.id, msg, reply_markup=main_keyboard())

# زر رابط الدعوة
@bot.message_handler(func=lambda message: message.text == "🎁 رابط الدعوة")
def referral_link(message):
    bot.clear_step_handler(message)
    user_id = message.from_user.id
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    text = (f"🎁 **رابط الدعوة الخاص بك:**\n\n`{link}`\n\n"
            "انسخ الرابط وشاركه مع أصدقائك! ستحصل على **20 نقطة** فورية عن كل شخص يدخل البوت من خلالك. 🔥")
    bot.reply_to(message, text, parse_mode="Markdown")

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
    bot.reply_to(message, f"💎 رصيدك الحالي: {points} نقطة.")

# زر إضافة قناتي (مع شرط الـ 20 نقطة)
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
    if points < 20:
        bot.reply_to(message, f"❌ عليك تجميع أكثر من 20 نقطة لتتمكن من إضافة قناتك!\n\n💎 رصيدك الحالي: {points} نقطة.\nاجمع النقاط عبر **🚀 تجميع النقاط** أو **🎁 رابط الدعوة**.")
        return

    msg = bot.reply_to(message, "أرسل يوزر قناتك العامة الآن مع الـ @ (مثال: @my_channel):\n\n⚠️ تنبيه: يجب رفع البوت مشرفاً في القناة أولاً ليتمكن من التأكد من الاشتراكات.")
    bot.register_next_step_handler(msg, process_channel_username)

def process_channel_username(message):
    if message.text in ["🚀 تجميع النقاط", "🎁 رابط الدعوة", "➕ إضافة قناتي", "💰 رصيد النقاط"]:
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
        bot.reply_to(message, f"✅ تم إضافة القناة {username} بنجاح!\nسيتم خصم نقطة واحدة مع كل مشترك جديد يأتيك.")
    except sqlite3.IntegrityError:
        bot.reply_to(message, "⚠️ هذه القناة مضافة بالفعل في النظام!")
    finally:
        conn.close()

# زر تجميع النقاط
@bot.message_handler(func=lambda message: message.text == "🚀 تجميع النقاط")
def exchange_subs(message):
    bot.clear_step_handler(message)
    user_id = message.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, channel_username, owner_id FROM channels WHERE owner_id != ? LIMIT 1", (user_id,))
    channel = cursor.fetchone()
    conn.close()

    if not channel:
        bot.reply_to(message, "📑 لا توجد قنوات متاحة حالياً!\n\n💡 يمكنك جمع النقاط عبر مشاركة **🎁 رابط الدعوة** مع أصدقائك.")
        return

    ch_id, ch_username, ch_owner = channel
    markup = types.InlineKeyboardMarkup()
    btn_link = types.InlineKeyboardButton("📢 فتح القناة والانضمام", url=f"https://t.me/{ch_username.replace('@', '')}")
    btn_check = types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data=f"check_{ch_id}_{ch_username}_{ch_owner}")
    markup.add(btn_link)
    markup.add(btn_check)

    bot.send_message(message.chat.id, f"اشترك في القناة التالية للحصول على +1 نقطة:\n👉 {ch_username}", reply_markup=markup)

# زر التحقق للتبادل والاشتراك الإجباري
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_must_join":
        if is_subscribed(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ شكرًا لاشتراكك!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_message(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد!", show_alert=True)
            
    elif call.data.startswith("check_"):
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

                bot.answer_callback_query(call.id, "✅ تم التحقق! حصلت على +1 نقطة.")
                bot.edit_message_text("✅ تم الاشتراك وحصلت على 1 نقطة!", chat_id=call.message.chat.id, message_id=call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد!", show_alert=True)
        except Exception:
            bot.answer_callback_query(call.id, "⚠️ تأكد من رفع البوت مشرفاً في القناة أولاً!", show_alert=True)

# أمر سري للأدمن لشحن النقاط (/addpoints 500)
@bot.message_handler(commands=['addpoints'])
def add_points_admin(message):
    try:
        amount = int(message.text.split()[1])
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, points) VALUES (?, 0)", (message.from_user.id,))
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, message.from_user.id))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🎉 تمت إضافة {amount} نقطة لحسابك بنجاح!")
    except Exception:
        bot.reply_to(message, "اكتب الأمر هكذا: /addpoints 500")

bot.infinity_polling()
