import telebot
from telebot import types
import sqlite3
import time
import os
from datetime import datetime
import random

# ========== SETTINGS ==========
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 8763658506))
SUPPORT = "@helpGROMBET"

bot = telebot.TeleBot(TOKEN)
bot_active = True

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, join_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, account_id TEXT, photo TEXT, status TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS game_stats (user_id INTEGER PRIMARY KEY, total_win INTEGER DEFAULT 0, total_bet INTEGER DEFAULT 0, games_played INTEGER DEFAULT 0, biggest_win INTEGER DEFAULT 0)''')
    c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username, join_date) VALUES (?, ?, ?)', (user_id, username, datetime.now().strftime("%d.%m.%Y %H:%M")))
    c.execute('INSERT OR IGNORE INTO game_stats (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_user_balance(user_id):
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def update_balance(user_id, amount, operation='add'):
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    if operation == 'add':
        c.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    else:
        c.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('SELECT user_id, username, balance FROM users ORDER BY balance DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_users_list():
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_deposit(user_id, amount, account_id, photo):
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('INSERT INTO deposits (user_id, amount, account_id, photo, status, date) VALUES (?, ?, ?, ?, ?, ?)',
              (user_id, amount, account_id, photo, 'pending', datetime.now().strftime("%d.%m.%Y %H:%M")))
    dep_id = c.lastrowid
    conn.commit()
    conn.close()
    return dep_id

def update_deposit_status(dep_id, status):
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('UPDATE deposits SET status = ? WHERE id = ?', (status, dep_id))
    conn.commit()
    conn.close()

def get_pending_deposits():
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('SELECT id, user_id, amount, account_id, photo, date FROM deposits WHERE status = "pending"')
    rows = c.fetchall()
    conn.close()
    return rows

def get_admins():
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM admins')
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_admin(user_id):
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def update_game_stats(user_id, bet, win):
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('UPDATE game_stats SET total_bet = total_bet + ?, games_played = games_played + 1 WHERE user_id = ?', (bet, user_id))
    if win > 0:
        c.execute('UPDATE game_stats SET total_win = total_win + ? WHERE user_id = ?', (win, user_id))
        c.execute('UPDATE game_stats SET biggest_win = MAX(biggest_win, ?) WHERE user_id = ?', (win, user_id))
    conn.commit()
    conn.close()

def get_game_stats(user_id):
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('SELECT total_win, total_bet, games_played, biggest_win FROM game_stats WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'total_win': row[0], 'total_bet': row[1], 'games_played': row[2], 'biggest_win': row[3]}
    return {'total_win': 0, 'total_bet': 0, 'games_played': 0, 'biggest_win': 0}

def get_stats():
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM deposits WHERE status="pending"')
    pending = c.fetchone()[0]
    c.execute('SELECT SUM(amount) FROM deposits WHERE status="approved"')
    total_deposits = c.fetchone()[0] or 0
    c.execute('SELECT SUM(total_win) FROM game_stats')
    total_wins = c.fetchone()[0] or 0
    conn.close()
    return {'users': users, 'pending': pending, 'total_deposits': total_deposits, 'total_wins': total_wins}

init_db()
temp_data = {}

# ========== MENU ==========
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 CASINO", "💰 DEPOSIT")
    markup.add("💸 WITHDRAW", "👨‍💻 SUPPORT")
    if user_id in get_admins():
        markup.add("⚙️ ADMIN")
    return markup

def casino_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add("🎲 10", "🎲 50", "🎲 100")
    markup.add("🎲 500", "🎲 1000", "🎲 5000")
    markup.add("🔙 MAIN MENU")
    return markup

def admin_menu():
    global bot_active
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📋 REQUESTS", "💰 ADD BALANCE")
    markup.add("👥 USERS LIST", "📊 STATS")
    markup.add("➕ ADD ADMIN", "➖ REMOVE ADMIN")
    markup.add("📢 BROADCAST")
    status_btn = "🔴 STOP" if bot_active else "🟢 START"
    markup.add(status_btn)
    markup.add("🔙 MAIN MENU")
    return markup

def back_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 BACK")
    return markup

# ========== COMMANDS ==========
@bot.message_handler(commands=['start'])
def start(msg):
    user = msg.from_user
    add_user(msg.chat.id, user.username)
    balance = get_user_balance(msg.chat.id)
    stats = get_game_stats(msg.chat.id)
    
    bot.send_message(msg.chat.id, 
        f"⚡ WELCOME TO GROMBET ⚡\n\n"
        f"👤 {user.first_name}\n"
        f"🆔 ID: {msg.chat.id}\n"
        f"💰 BALANCE: {balance} som\n\n"
        f"🏆 TOTAL WIN: {stats['total_win']} som\n"
        f"🎮 GAMES: {stats['games_played']}\n"
        f"💎 BIGGEST WIN: {stats['biggest_win']} som\n\n"
        f"🎰 SPIN AND WIN! 🎰",
        reply_markup=main_menu(msg.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔙 MAIN MENU" or m.text == "🔙 BACK")
def back_to_main(msg):
    start(msg)

# ========== CASINO ==========
@bot.message_handler(func=lambda m: m.text == "🎰 CASINO")
def casino(msg):
    bot.send_message(msg.chat.id, "🎰 CHOOSE YOUR BET 🎰", reply_markup=casino_menu())

@bot.message_handler(func=lambda m: m.text and m.text.startswith("🎲"))
def play_game(msg):
    try:
        bet = int(msg.text.split()[1])
    except:
        bot.send_message(msg.chat.id, "❌ ERROR!")
        return
    
    balance = get_user_balance(msg.chat.id)
    if bet > balance:
        bot.send_message(msg.chat.id, f"❌ NOT ENOUGH BALANCE!\n💰 BALANCE: {balance} som\n🎲 BET: {bet} som")
        return
    
    symbols = ['🍒', '🍋', '🍊', '🍉', '🍇', '💎', '7️⃣', '🎰']
    reels = [random.choice(symbols) for _ in range(3)]
    
    win_multiplier = 0
    if reels[0] == reels[1] == reels[2]:
        if reels[0] == '🎰': win_multiplier = 50
        elif reels[0] == '💎': win_multiplier = 30
        elif reels[0] == '7️⃣': win_multiplier = 25
        elif reels[0] == '🍇': win_multiplier = 15
        elif reels[0] == '🍉': win_multiplier = 12
        elif reels[0] == '🍊': win_multiplier = 10
        elif reels[0] == '🍋': win_multiplier = 8
        elif reels[0] == '🍒': win_multiplier = 5
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        win_multiplier = 2
    
    win_amount = bet * win_multiplier
    
    if win_amount > 0:
        update_balance(msg.chat.id, win_amount, 'add')
        update_game_stats(msg.chat.id, bet, win_amount)
        result_text = f"🎉 WIN! 🎉\n\n{reels[0]} | {reels[1]} | {reels[2]}\n\n✅ WIN: {win_amount} som! (x{win_multiplier})"
    else:
        update_balance(msg.chat.id, bet, 'sub')
        update_game_stats(msg.chat.id, bet, 0)
        result_text = f"😔 LOSE! 😔\n\n{reels[0]} | {reels[1]} | {reels[2]}\n\n❌ LOST: {bet} som"
    
    new_balance = get_user_balance(msg.chat.id)
    stats = get_game_stats(msg.chat.id)
    bot.send_message(msg.chat.id, 
        f"{result_text}\n\n"
        f"💰 BALANCE: {new_balance} som\n"
        f"🏆 TOTAL WIN: {stats['total_win']} som",
        reply_markup=casino_menu())

# ========== DEPOSIT ==========
@bot.message_handler(func=lambda m: m.text == "💰 DEPOSIT")
def deposit(msg):
    bot.send_message(msg.chat.id, "🆔 ENTER ACCOUNT ID:", reply_markup=back_menu())
    bot.register_next_step_handler(msg, get_account_id)

def get_account_id(msg):
    if msg.text == "🔙 BACK":
        start(msg)
        return
    temp_data[msg.chat.id] = {"account_id": msg.text}
    bot.send_message(msg.chat.id, "💰 ENTER AMOUNT (100 - 100000 som):", reply_markup=back_menu())
    bot.register_next_step_handler(msg, get_amount)

def get_amount(msg):
    if msg.text == "🔙 BACK":
        start(msg)
        return
    if not msg.text.isdigit():
        bot.send_message(msg.chat.id, "❌ ENTER NUMBER!")
        bot.register_next_step_handler(msg, get_amount)
        return
    amount = int(msg.text)
    if amount < 100 or amount > 100000:
        bot.send_message(msg.chat.id, "❌ AMOUNT FROM 100 TO 100000 SOM!")
        bot.register_next_step_handler(msg, get_amount)
        return
    temp_data[msg.chat.id]["amount"] = amount
    bot.send_message(msg.chat.id, "📸 SEND PHOTO OF RECEIPT:", reply_markup=back_menu())
    bot.register_next_step_handler(msg, get_check_photo)

def get_check_photo(msg):
    if msg.text == "🔙 BACK":
        start(msg)
        return
    if not msg.photo:
        bot.send_message(msg.chat.id, "❌ SEND PHOTO OF RECEIPT!")
        bot.register_next_step_handler(msg, get_check_photo)
        return
    user_id = msg.chat.id
    account_id = temp_data[user_id]["account_id"]
    amount = temp_data[user_id]["amount"]
    photo_id = msg.photo[-1].file_id
    dep_id = add_deposit(user_id, amount, account_id, photo_id)
    
    admins = get_admins()
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{dep_id}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{dep_id}")
    )
    for admin in admins:
        try:
            bot.send_photo(admin, photo_id, 
                caption=f"🆕 NEW REQUEST #{dep_id}\n"
                        f"👤 USER: {user_id}\n"
                        f"💰 AMOUNT: {amount} som\n"
                        f"🆔 ACCOUNT: {account_id}\n"
                        f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                reply_markup=markup)
        except:
            pass
    bot.send_message(msg.chat.id, 
        f"✅ REQUEST SENT!\n\n"
        f"💰 AMOUNT: {amount} som\n"
        f"🆔 ACCOUNT: {account_id}\n\n"
        f"⏳ WAITING FOR APPROVAL",
        reply_markup=main_menu(user_id))
    del temp_data[user_id]

# ========== WITHDRAW ==========
@bot.message_handler(func=lambda m: m.text == "💸 WITHDRAW")
def withdraw(msg):
    bot.send_message(msg.chat.id, f"💸 FOR WITHDRAWAL CONTACT SUPPORT:\n{SUPPORT}", reply_markup=main_menu(msg.from_user.id))

# ========== SUPPORT ==========
@bot.message_handler(func=lambda m: m.text == "👨‍💻 SUPPORT")
def support(msg):
    bot.send_message(msg.chat.id, f"📞 SUPPORT: {SUPPORT}")

# ========== ADMIN PANEL ==========
@bot.message_handler(func=lambda m: m.text == "⚙️ ADMIN" and m.from_user.id in get_admins())
def admin_panel(msg):
    bot.send_message(msg.chat.id, "⚙️ ADMIN PANEL", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "💰 ADD BALANCE" and m.from_user.id in get_admins())
def admin_add_balance(msg):
    bot.send_message(msg.chat.id, "👤 ENTER USER ID:", reply_markup=back_menu())
    bot.register_next_step_handler(msg, get_user_id_for_balance)

def get_user_id_for_balance(msg):
    if msg.text == "🔙 BACK":
        admin_panel(msg)
        return
    try:
        user_id = int(msg.text)
        temp_data[msg.chat.id] = {"admin_user_id": user_id}
        bot.send_message(msg.chat.id, "💰 ENTER AMOUNT:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, get_admin_amount)
    except:
        bot.send_message(msg.chat.id, "❌ ERROR! ENTER NUMERIC ID!")

def get_admin_amount(msg):
    if msg.text == "🔙 BACK":
        admin_panel(msg)
        return
    if not msg.text.isdigit():
        bot.send_message(msg.chat.id, "❌ ENTER NUMBER!")
        bot.register_next_step_handler(msg, get_admin_amount)
        return
    amount = int(msg.text)
    user_id = temp_data[msg.chat.id]["admin_user_id"]
    update_balance(user_id, amount, 'add')
    balance = get_user_balance(user_id)
    bot.send_message(msg.chat.id, 
        f"✅ BALANCE ADDED!\n"
        f"👤 USER: {user_id}\n"
        f"💰 AMOUNT: {amount} som\n"
        f"📊 NEW BALANCE: {balance} som", 
        reply_markup=admin_menu())
    try:
        bot.send_message(user_id, f"✅ YOUR BALANCE HAS BEEN INCREASED!\n💰 {amount} som\n📊 BALANCE: {balance} som")
    except:
        pass

@bot.message_handler(func=lambda m: m.text == "👥 USERS LIST" and m.from_user.id in get_admins())
def list_users(msg):
    users = get_all_users()
    if not users:
        bot.send_message(msg.chat.id, "📭 NO USERS")
        return
    text = "👥 USERS LIST 👥\n\n"
    for user in users[:20]:
        user_id, username, balance = user
        username_display = f"@{username}" if username else str(user_id)
        text += f"🆔 {user_id} | {username_display}\n💰 {balance} som\n\n"
    bot.send_message(msg.chat.id, text, reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📊 STATS" and m.from_user.id in get_admins())
def admin_stats(msg):
    stats = get_stats()
    text = f"📊 GROMBET STATS 📊\n\n"
    text += f"👥 USERS: {stats['users']}\n"
    text += f"⏳ PENDING: {stats['pending']}\n"
    text += f"💰 TOTAL DEPOSITS: {stats['total_deposits']} som\n"
    text += f"🏆 TOTAL WINS: {stats['total_wins']} som"
    bot.send_message(msg.chat.id, text, reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📋 REQUESTS" and m.from_user.id in get_admins())
def view_requests(msg):
    deposits = get_pending_deposits()
    if not deposits:
        bot.send_message(msg.chat.id, "📭 NO REQUESTS", reply_markup=admin_menu())
        return
    for dep in deposits:
        dep_id, user_id, amount, account_id, photo_id, date = dep
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{dep_id}"),
            types.InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{dep_id}")
        )
        text = f"🆕 REQUEST #{dep_id}\n👤 USER: {user_id}\n💰 AMOUNT: {amount} som\n🆔 ACCOUNT: {account_id}\n📅 {date}"
        try:
            if photo_id:
                bot.send_photo(msg.chat.id, photo_id, caption=text, reply_markup=markup)
            else:
                bot.send_message(msg.chat.id, text, reply_markup=markup)
        except:
            bot.send_message(msg.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ ADD ADMIN" and m.from_user.id in get_admins())
def add_admin_btn(msg):
    bot.send_message(msg.chat.id, "👤 ENTER NEW ADMIN ID:")
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(msg):
    try:
        add_admin(int(msg.text))
        bot.send_message(msg.chat.id, "✅ ADMIN ADDED!", reply_markup=admin_menu())
    except:
        bot.send_message(msg.chat.id, "❌ ERROR!")

@bot.message_handler(func=lambda m: m.text == "➖ REMOVE ADMIN" and m.from_user.id in get_admins())
def remove_admin_btn(msg):
    bot.send_message(msg.chat.id, "👤 ENTER ADMIN ID TO REMOVE:")
    bot.register_next_step_handler(msg, process_remove_admin)

def process_remove_admin(msg):
    try:
        user_id = int(msg.text)
        if user_id == ADMIN_ID:
            bot.send_message(msg.chat.id, "❌ CANNOT REMOVE MAIN ADMIN!")
            return
        remove_admin(user_id)
        bot.send_message(msg.chat.id, "✅ ADMIN REMOVED!", reply_markup=admin_menu())
    except:
        bot.send_message(msg.chat.id, "❌ ERROR!")

@bot.message_handler(func=lambda m: m.text in ["🔴 STOP", "🟢 START"] and m.from_user.id in get_admins())
def toggle_bot(msg):
    global bot_active
    bot_active = (msg.text == "🟢 START")
    bot.send_message(msg.chat.id, f"{'🟢 BOT STARTED' if bot_active else '🔴 BOT STOPPED'}", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📢 BROADCAST" and m.from_user.id in get_admins())
def broadcast_start(msg):
    bot.send_message(msg.chat.id, "📝 SEND MESSAGE FOR BROADCAST:")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(msg):
    users = get_all_users_list()
    success = 0
    for user_id in users:
        try:
            bot.copy_message(user_id, msg.chat.id, msg.message_id)
            success += 1
        except:
            pass
        time.sleep(0.05)
    bot.send_message(msg.chat.id, f"✅ BROADCAST DONE!\n📨 DELIVERED: {success}/{len(users)}", reply_markup=admin_menu())

# ========== CALLBACKS ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_call(call):
    admin_id = call.from_user.id
    if admin_id not in get_admins():
        bot.answer_callback_query(call.id, "❌ NO PERMISSION!")
        return
    action, dep_id = call.data.split('_')
    dep_id = int(dep_id)
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('SELECT user_id, amount FROM deposits WHERE id = ?', (dep_id,))
    result = c.fetchone()
    conn.close()
    if not result:
        bot.answer_callback_query(call.id, "❌ REQUEST NOT FOUND!")
        return
    user_id, amount = result
    if action == "approve":
        update_deposit_status(dep_id, "approved")
        update_balance(user_id, amount, 'add')
        bot.answer_callback_query(call.id, "✅ APPROVED!")
        try:
            bot.send_message(user_id, f"✅ YOUR REQUEST FOR {amount} som HAS BEEN APPROVED!\n💰 BALANCE UPDATED!")
        except:
            pass
        bot.edit_message_text(f"✅ REQUEST #{dep_id} APPROVED", call.message.chat.id, call.message.message_id)
    else:
        update_deposit_status(dep_id, "rejected")
        bot.answer_callback_query(call.id, "❌ REJECTED!")
        try:
            bot.send_message(user_id, f"❌ YOUR REQUEST FOR {amount} som HAS BEEN REJECTED!\n📞 CONTACT SUPPORT: {SUPPORT}")
        except:
            pass
        bot.edit_message_text(f"❌ REQUEST #{dep_id} REJECTED", call.message.chat.id, call.message.message_id)

# ========== START ==========
if __
