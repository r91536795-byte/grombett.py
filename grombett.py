import telebot
from telebot import types
import sqlite3
import time
import os
from datetime import datetime
import random

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 8763658506))
SUPPORT = "@helpGGkassabot"

bot = telebot.TeleBot(TOKEN)
bot_active = True

# ========== БАЗА ДАННЫХ ==========
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

# ========== МЕНЮ ==========
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 КАЗИНО", "💰 ПОПОЛНИТЬ")
    markup.add("💸 ВЫВЕСТИ", "👨‍💻 ПОДДЕРЖКА")
    if user_id in get_admins():
        markup.add("⚙️ АДМИН")
    return markup

def casino_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add("🎲 10", "🎲 50", "🎲 100")
    markup.add("🎲 500", "🎲 1000", "🎲 5000")
    markup.add("🔙 ГЛАВНОЕ МЕНЮ")
    return markup

def admin_menu():
    global bot_active
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📋 ЗАЯВКИ", "💰 ПОПОЛНИТЬ ПОЛЬЗОВАТЕЛЯ")
    markup.add("👥 СПИСОК ИГРОКОВ", "📊 СТАТИСТИКА")
    markup.add("➕ ДОБАВИТЬ АДМИНА", "➖ УДАЛИТЬ АДМИНА")
    markup.add("📢 РАССЫЛКА")
    status_btn = "🔴 ВЫКЛЮЧИТЬ" if bot_active else "🟢 ВКЛЮЧИТЬ"
    markup.add(status_btn)
    markup.add("🔙 ГЛАВНОЕ МЕНЮ")
    return markup

def back_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Назад")
    return markup

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(msg):
    user = msg.from_user
    add_user(msg.chat.id, user.username)
    balance = get_user_balance(msg.chat.id)
    stats = get_game_stats(msg.chat.id)
    bot.send_message(msg.chat.id, 
        f"⚡ ДОБРО ПОЖАЛОВАТЬ В GROMBET ⚡\n\n👤 {user.first_name}\n🆔 ID: {msg.chat.id}\n💰 БАЛАНС: {balance} сом\n\n🏆 ВЫИГРАНО: {stats['total_win']} сом\n🎮 ИГР: {stats['games_played']}\n\n🎰 КРУТИ И ВЫИГРЫВАЙ! 🎰",
        reply_markup=main_menu(msg.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔙 ГЛАВНОЕ МЕНЮ" or m.text == "🔙 Назад")
def back_to_main(msg):
    start(msg)

# ========== КАЗИНО ==========
@bot.message_handler(func=lambda m: m.text == "🎰 КАЗИНО")
def casino(msg):
    bot.send_message(msg.chat.id, "🎰 ВЫБЕРИ СТАВКУ 🎰", reply_markup=casino_menu())

@bot.message_handler(func=lambda m: m.text and m.text.startswith("🎲"))
def play_game(msg):
    try:
        bet = int(msg.text.split()[1])
    except:
        bot.send_message(msg.chat.id, "❌ ОШИБКА!")
        return
    
    balance = get_user_balance(msg.chat.id)
    if bet > balance:
        bot.send_message(msg.chat.id, f"❌ НЕДОСТАТОЧНО СРЕДСТВ!\n💰 БАЛАНС: {balance} сом\n🎲 СТАВКА: {bet} сом")
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
        result_text = f"🎉 ПОБЕДА! 🎉\n\n{reels[0]} | {reels[1]} | {reels[2]}\n\n✅ ВЫИГРЫШ: {win_amount} сом! (x{win_multiplier})"
    else:
        update_balance(msg.chat.id, bet, 'sub')
        update_game_stats(msg.chat.id, bet, 0)
        result_text = f"😔 ПРОИГРЫШ! 😔\n\n{reels[0]} | {reels[1]} | {reels[2]}\n\n❌ ПРОИГРАНО: {bet} сом"
    
    new_balance = get_user_balance(msg.chat.id)
    stats = get_game_stats(msg.chat.id)
    bot.send_message(msg.chat.id, f"{result_text}\n\n💰 БАЛАНС: {new_balance} сом\n🏆 ВСЕГО ВЫИГРАНО: {stats['total_win']} сом", reply_markup=casino_menu())

# ========== ПОПОЛНЕНИЕ ==========
@bot.message_handler(func=lambda m: m.text == "💰 ПОПОЛНИТЬ")
def deposit(msg):
    bot.send_message(msg.chat.id, "🆔 ВВЕДИТЕ ID СЧЕТА:", reply_markup=back_menu())
    bot.register_next_step_handler(msg, get_account_id)

def get_account_id(msg):
    if msg.text == "🔙 Назад":
        start(msg)
        return
    temp_data[msg.chat.id] = {"account_id": msg.text}
    bot.send_message(msg.chat.id, "💰 ВВЕДИТЕ СУММУ (от 100 до 100 000 сом):", reply_markup=back_menu())
    bot.register_next_step_handler(msg, get_amount)

def get_amount(msg):
    if msg.text == "🔙 Назад":
        start(msg)
        return
    if not msg.text.isdigit():
        bot.send_message(msg.chat.id, "❌ ВВЕДИТЕ ЧИСЛО!")
        bot.register_next_step_handler(msg, get_amount)
        return
    amount = int(msg.text)
    if amount < 100 or amount > 100000:
        bot.send_message(msg.chat.id, "❌ СУММА ОТ 100 ДО 100 000 СОМ!")
        bot.register_next_step_handler(msg, get_amount)
        return
    temp_data[msg.chat.id]["amount"] = amount
    bot.send_message(msg.chat.id, "📸 ОТПРАВЬТЕ ФОТО ЧЕКА:", reply_markup=back_menu())
    bot.register_next_step_handler(msg, get_check_photo)

def get_check_photo(msg):
    if msg.text == "🔙 Назад":
        start(msg)
        return
    if not msg.photo:
        bot.send_message(msg.chat.id, "❌ ОТПРАВЬТЕ ФОТО ЧЕКА!")
        bot.register_next_step_handler(msg, get_check_photo)
        return
    user_id = msg.chat.id
    account_id = temp_data[user_id]["account_id"]
    amount = temp_data[user_id]["amount"]
    photo_id = msg.photo[-1].file_id
    dep_id = add_deposit(user_id, amount, account_id, photo_id)
    
    admins = get_admins()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ ОДОБРИТЬ", callback_data=f"approve_{dep_id}"), types.InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_{dep_id}"))
    for admin in admins:
        try:
            bot.send_photo(admin, photo_id, caption=f"🆕 ЗАЯВКА #{dep_id}\n👤 {user_id}\n💰 {amount} сом\n🆔 {account_id}", reply_markup=markup)
        except:
            pass
    bot.send_message(msg.chat.id, f"✅ ЗАЯВКА ОТПРАВЛЕНА!\n💰 {amount} сом\n🆔 {account_id}\n\n⏳ ОЖИДАЙТЕ ПОДТВЕРЖДЕНИЯ", reply_markup=main_menu(user_id))
    del temp_data[user_id]

# ========== ВЫВОД ==========
@bot.message_handler(func=lambda m: m.text == "💸 ВЫВЕСТИ")
def withdraw(msg):
    bot.send_message(msg.chat.id, f"💸 ДЛЯ ВЫВОДА ОБРАТИТЕСЬ В ПОДДЕРЖКУ:\n{SUPPORT}", reply_markup=main_menu(msg.from_user.id))

# ========== ПОДДЕРЖКА ==========
@bot.message_handler(func=lambda m: m.text == "👨‍💻 ПОДДЕРЖКА")
def support(msg):
    bot.send_message(msg.chat.id, f"📞 ПОДДЕРЖКА: {SUPPORT}")

# ========== АДМИН ПАНЕЛЬ ==========
@bot.message_handler(func=lambda m: m.text == "⚙️ АДМИН" and m.from_user.id in get_admins())
def admin_panel(msg):
    bot.send_message(msg.chat.id, "⚙️ АДМИН ПАНЕЛЬ", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "💰 ПОПОЛНИТЬ ПОЛЬЗОВАТЕЛЯ" and m.from_user.id in get_admins())
def admin_add_balance(msg):
    bot.send_message(msg.chat.id, "👤 ВВЕДИТЕ ID ПОЛЬЗОВАТЕЛЯ:", reply_markup=back_menu())
    bot.register_next_step_handler(msg, get_user_id_for_balance)

def get_user_id_for_balance(msg):
    if msg.text == "🔙 Назад":
        admin_panel(msg)
        return
    try:
        user_id = int(msg.text)
        temp_data[msg.chat.id] = {"admin_user_id": user_id}
        bot.send_message(msg.chat.id, "💰 ВВЕДИТЕ СУММУ:", reply_markup=back_menu())
        bot.register_next_step_handler(msg, get_admin_amount)
    except:
        bot.send_message(msg.chat.id, "❌ ОШИБКА!")

def get_admin_amount(msg):
    if msg.text == "🔙 Назад":
        admin_panel(msg)
        return
    if not msg.text.isdigit():
        bot.send_message(msg.chat.id, "❌ ВВЕДИТЕ ЧИСЛО!")
        bot.register_next_step_handler(msg, get_admin_amount)
        return
    amount = int(msg.text)
    user_id = temp_data[msg.chat.id]["admin_user_id"]
    update_balance(user_id, amount, 'add')
    balance = get_user_balance(user_id)
    bot.send_message(msg.chat.id, f"✅ ПОПОЛНЕНО!\n👤 {user_id}\n💰 {amount} сом\n📊 НОВЫЙ БАЛАНС: {balance} сом", reply_markup=admin_menu())
    try:
        bot.send_message(user_id, f"✅ ВАШ БАЛАНС ПОПОЛНЕН!\n💰 {amount} сом\n📊 БАЛАНС: {balance} сом")
    except:
        pass

@bot.message_handler(func=lambda m: m.text == "👥 СПИСОК ИГРОКОВ" and m.from_user.id in get_admins())
def list_users(msg):
    users = get_all_users()
    if not users:
        bot.send_message(msg.chat.id, "📭 НЕТ ПОЛЬЗОВАТЕЛЕЙ")
        return
    text = "👥 СПИСОК ИГРОКОВ 👥\n\n"
    for user in users[:20]:
        user_id, username, balance = user
        username_display = f"@{username}" if username else str(user_id)
        text += f"🆔 {user_id} | {username_display}\n💰 {balance} сом\n\n"
    bot.send_message(msg.chat.id, text, reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📊 СТАТИСТИКА" and m.from_user.id in get_admins())
def admin_stats(msg):
    stats = get_stats()
    bot.send_message(msg.chat.id, f"📊 СТАТИСТИКА 📊\n\n👥 ПОЛЬЗОВАТЕЛЕЙ: {stats['users']}\n⏳ ЗАЯВОК: {stats['pending']}\n💰 ПОПОЛНЕНИЙ: {stats['total_deposits']} сом\n🏆 ВЫИГРАНО: {stats['total_wins']} сом", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📋 ЗАЯВКИ" and m.from_user.id in get_admins())
def view_requests(msg):
    deposits = get_pending_deposits()
    if not deposits:
        bot.send_message(msg.chat.id, "📭 НЕТ ЗАЯВОК", reply_markup=admin_menu())
        return
    for dep in deposits:
        dep_id, user_id, amount, account_id, photo_id, date = dep
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ ОДОБРИТЬ", callback_data=f"approve_{dep_id}"), types.InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_{dep_id}"))
        bot.send_message(msg.chat.id, f"🆕 ЗАЯВКА #{dep_id}\n👤 {user_id}\n💰 {amount} сом\n🆔 {account_id}", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ ДОБАВИТЬ АДМИНА" and m.from_user.id in get_admins())
def add_admin_btn(msg):
    bot.send_message(msg.chat.id, "👤 ВВЕДИТЕ ID:")
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(msg):
    try:
        add_admin(int(msg.text))
        bot.send_message(msg.chat.id, "✅ АДМИН ДОБАВЛЕН!", reply_markup=admin_menu())
    except:
        bot.send_message(msg.chat.id, "❌ ОШИБКА!")

@bot.message_handler(func=lambda m: m.text == "➖ УДАЛИТЬ АДМИНА" and m.from_user.id in get_admins())
def remove_admin_btn(msg):
    bot.send_message(msg.chat.id, "👤 ВВЕДИТЕ ID:")
    bot.register_next_step_handler(msg, process_remove_admin)

def process_remove_admin(msg):
    try:
        user_id = int(msg.text)
        if user_id == ADMIN_ID:
            bot.send_message(msg.chat.id, "❌ НЕЛЬЗЯ УДАЛИТЬ ГЛАВНОГО АДМИНА!")
            return
        remove_admin(user_id)
        bot.send_message(msg.chat.id, "✅ АДМИН УДАЛЕН!", reply_markup=admin_menu())
    except:
        bot.send_message(msg.chat.id, "❌ ОШИБКА!")

@bot.message_handler(func=lambda m: m.text in ["🔴 ВЫКЛЮЧИТЬ", "🟢 ВКЛЮЧИТЬ"] and m.from_user.id in get_admins())
def toggle_bot(msg):
    global bot_active
    bot_active = (msg.text == "🟢 ВКЛЮЧИТЬ")
    bot.send_message(msg.chat.id, f"{'🟢 БОТ ВКЛЮЧЕН' if bot_active else '🔴 БОТ ВЫКЛЮЧЕН'}", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📢 РАССЫЛКА" and m.from_user.id in get_admins())
def broadcast_start(msg):
    bot.send_message(msg.chat.id, "📝 ОТПРАВЬТЕ СООБЩЕНИЕ:")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(msg):
    users = get_all_users()
    success = 0
    for user_id, _, _ in users:
        try:
            bot.copy_message(user_id, msg.chat.id, msg.message_id)
            success += 1
        except:
            pass
        time.sleep(0.05)
    bot.send_message(msg.chat.id, f"✅ РАССЫЛКА: {success}/{len(users)}", reply_markup=admin_menu())

# ========== КНОПКИ ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_call(call):
    admin_id = call.from_user.id
    if admin_id not in get_admins():
        bot.answer_callback_query(call.id, "❌ НЕТ ПРАВ!")
        return
    action, dep_id = call.data.split('_')
    dep_id = int(dep_id)
    conn = sqlite3.connect('grombett.db')
    c = conn.cursor()
    c.execute('SELECT user_id, amount FROM deposits WHERE id = ?', (dep_id,))
    result = c.fetchone()
    conn.close()
    if not result:
        bot.answer_callback_query(call.id, "❌ ЗАЯВКА НЕ НАЙДЕНА!")
        return
    user_id, amount = result
    if action == "approve":
        update_deposit_status(dep_id, "approved")
        update_balance(user_id, amount, 'add')
        bot.answer_callback_query(call.id, "✅ ОДОБРЕНО!")
        try:
            bot.send_message(user_id, f"✅ ЗАЯВКА НА {amount} сом ОДОБРЕНА!")
        except:
            pass
        bot.edit_message_text(f"✅ ЗАЯВКА #{dep_id} ОДОБРЕНА", call.message.chat.id, call.message.message_id)
    else:
        update_deposit_status(dep_id, "rejected")
        bot.answer_callback_query(call.id, "❌ ОТКЛОНЕНО!")
        try:
            bot.send_message(user_id, f"❌ ЗАЯВКА НА {amount} сом ОТКЛОНЕНА!\n📞 {SUPPORT}")
        except:
            pass
        bot.edit_message_text(f"❌ ЗАЯВКА #{dep_id} ОТКЛОНЕНА", call.message.chat.id, call.message.message_id)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🚀 GROMBET ЗАПУЩЕН!")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)
