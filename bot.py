import os
import firebase_admin
from firebase_admin import credentials, db
import logging
from datetime import datetime
import telebot
from telebot import types
import json

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8257056060:AAEJjN5nJ2deXu8KfvmeCoFfi40NqoSkPr0')
BOT_PASSWORD = os.getenv('BOT_PASSWORD', 'operkassa2020')  

#лог
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
# Словарь для хранения авторизованных пользователей
authorized_users = {}

try:
    if os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
    else:
        service_account_info = {
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID', 'oper-kassa'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL', ''),
            "client_id": os.getenv('FIREBASE_CLIENT_ID', ''),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL', '')
        }
        cred = credentials.Certificate(service_account_info)
    
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://oper-kassa-default-rtdb.europe-west1.firebasedatabase.app'
    })
    logging.info("Firebase initialized successfully")
except Exception as e:
    logging.error(f"Firebase initialization failed: {e}")

class CurrencyManager:
    def __init__(self):
        self.currencies_structure = [
            {'code': 'USD_WHITE', 'flag': 'us', 'name': 'Доллар США (белый)', 'showRates': True},
            {'code': 'USD_BLUE', 'flag': 'us', 'name': 'Доллар США (синий)', 'showRates': True},
            {'code': 'EUR', 'flag': 'eu', 'name': 'Евро', 'showRates': True},
            {'code': 'GBP', 'flag': 'gb', 'name': 'Фунт стерлингов', 'showRates': False},
            {'code': 'CNY', 'flag': 'cn', 'name': 'Китайский юань', 'showRates': False},
            {'code': 'RUB', 'flag': 'ru', 'name': 'Российский рубль', 'showRates': True}
        ]
    
    def get_current_rates(self):
        """Получить текущие курсы из Firebase"""
        try:
            ref = db.reference('/currencies')
            rates = ref.get()
            if rates is None:
                # Если в Firebase нет данных, инициализируем базовыми
                self.initialize_rates()
                return self.get_current_rates()
            return rates
        except Exception as e:
            logging.error(f"Error getting rates: {e}")
            return []
    
    def initialize_rates(self):
        """Инициализировать Firebase базовыми курсами"""
        try:
            ref = db.reference('/currencies')
            initial_rates = []
            for currency in self.currencies_structure:
                curr = currency.copy()
                if curr['showRates']:
                    if curr['code'] == 'USD_WHITE':
                        curr.update({'buy': 95.5, 'sell': 97.8})
                    elif curr['code'] == 'USD_BLUE':
                        curr.update({'buy': 94.0, 'sell': 96.5})
                    elif curr['code'] == 'EUR':
                        curr.update({'buy': 105.2, 'sell': 107.9})
                    elif curr['code'] == 'RUB':
                        curr.update({'buy': 1.0, 'sell': 1.0})
                    else:
                        curr.update({'buy': 0.0, 'sell': 0.0})
                else:
                    curr.update({'buy': 0.0, 'sell': 0.0})
                curr['updated'] = datetime.now().isoformat()
                initial_rates.append(curr)
            
            ref.set(initial_rates)
            logging.info("Initial rates set in Firebase")
        except Exception as e:
            logging.error(f"Error initializing rates: {e}")
    
    def update_currency_rate(self, currency_code, buy_rate, sell_rate):
        """Обновить курс конкретной валюты"""
        try:
            ref = db.reference('/currencies')
            current_rates = ref.get() or []
            
            updated = False
            for currency in current_rates:
                if currency['code'] == currency_code:
                    currency['buy'] = float(buy_rate)
                    currency['sell'] = float(sell_rate)
                    currency['updated'] = datetime.now().isoformat()
                    updated = True
                    break
            if not updated:
                for base_currency in self.currencies_structure:
                    if base_currency['code'] == currency_code:
                        new_currency = base_currency.copy()
                        new_currency['buy'] = float(buy_rate)
                        new_currency['sell'] = float(sell_rate)
                        new_currency['updated'] = datetime.now().isoformat()
                        current_rates.append(new_currency)
                        break
            
            ref.set(current_rates)
            logging.info(f"Updated {currency_code}: buy={buy_rate}, sell={sell_rate}")
            return True
            
        except Exception as e:
            logging.error(f"Error updating rate: {e}")
            return False

currency_manager = CurrencyManager()

def is_authorized(user_id):
    """Проверка авторизации пользователя"""
    return authorized_users.get(user_id, False)

def require_auth(func):
    """Декоратор для проверки авторизации"""
    def wrapper(message):
        if not is_authorized(message.from_user.id):
            bot.send_message(
                message.chat.id, 
                "🔒 *Доступ запрещен!*\n\n"
                "Для работы с ботом необходимо авторизоваться.\n"
                "Используйте команду /auth для ввода пароля.",
                parse_mode='Markdown'
            )
            return
        return func(message)
    return wrapper

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Приветственное сообщение"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('📊 Текущие курсы')
    btn2 = types.KeyboardButton('✏️ Изменить курс')
    btn3 = types.KeyboardButton('🔄 Обновить все')
    btn4 = types.KeyboardButton('❓ Помощь')
    
    if is_authorized(message.from_user.id):
        btn5 = types.KeyboardButton('🚪 Выйти')
        markup.add(btn1, btn2, btn3, btn4, btn5)
    else:
        btn5 = types.KeyboardButton('🔐 Авторизация')
        markup.add(btn1, btn2, btn3, btn4, btn5)
    
    status = "✅ Авторизован" if is_authorized(message.from_user.id) else "❌ Не авторизован"
    
    bot.send_message(
        message.chat.id,
        f"💱 *Бот управления курсами валют*\n\n"
        f"Статус: {status}\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.message_handler(commands=['auth'])
@bot.message_handler(func=lambda message: message.text == '🔐 Авторизация')
def handle_auth(message):
    """Обработка авторизации"""
    if is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "✅ Вы уже авторизованы!")
        return
    
    msg = bot.send_message(
        message.chat.id,
        "🔒 *Авторизация*\n\n"
        "Введите пароль для доступа к управлению курсами:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_password)

def process_password(message):
    """Обработка ввода пароля"""
    if message.text == BOT_PASSWORD:
        authorized_users[message.from_user.id] = True
        bot.send_message(
            message.chat.id,
            "✅ *Авторизация успешна!*\n\n"
            "Теперь вы можете изменять курсы валют.",
            parse_mode='Markdown'
        )
        send_welcome(message)
    else:
        bot.send_message(
            message.chat.id,
            "❌ *Неверный пароль!*\n\n"
            "Попробуйте снова или обратитесь к администратору.",
            parse_mode='Markdown'
        )

@bot.message_handler(func=lambda message: message.text == '🚪 Выйти')
def handle_logout(message):
    """Выход из системы"""
    if message.from_user.id in authorized_users:
        del authorized_users[message.from_user.id]
    bot.send_message(message.chat.id, "🚪 Вы вышли из системы.")
    send_welcome(message)

@bot.message_handler(commands=['rates'])
@bot.message_handler(func=lambda message: message.text == '📊 Текущие курсы')
def show_current_rates(message):
    """Показать текущие курсы"""
    rates = currency_manager.get_current_rates()
    
    if not rates:
        bot.send_message(message.chat.id, "❌ Курсы еще не установлены")
        return
    
    response = "💱 *Текущие курсы:*\n\n"
    for currency in rates:
        status = "✅" if currency.get('showRates', False) else "❌"
        if currency.get('showRates', False):
            response += f"{status} *{currency['name']}*\n"
            response += f"   Покупка: `{currency.get('buy', 0):.2f} ₽`\n"
            response += f"   Продажа: `{currency.get('sell', 0):.2f} ₽`\n"
        else:
            response += f"{status} *{currency['name']}* — уточняйте по телефону\n"
        
        if currency.get('updated'):
            try:
                updated_time = datetime.fromisoformat(currency['updated']).strftime('%H:%M')
                response += f"   _Обновлено: {updated_time}_\n"
            except:
                pass
        
        response += "\n"
    
    bot.send_message(message.chat.id, response, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '✏️ Изменить курс')
@require_auth
def handle_change_rate(message):
    """Выбор валюты для изменения курса"""
    rates = currency_manager.get_current_rates()
    
    if not rates:
        bot.send_message(message.chat.id, "❌ Нет доступных валют для редактирования")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for currency in rates:
        btn = types.InlineKeyboardButton(
            text=currency['name'],
            callback_data=f"edit_{currency['code']}"
        )
        markup.add(btn)
    
    cancel_btn = types.InlineKeyboardButton("❌ Отмена", callback_data="cancel")
    markup.add(cancel_btn)
    
    bot.send_message(
        message.chat.id,
        "💰 *Выберите валюту для изменения курса:*",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_'))
def handle_edit_currency(call):
    """Обработка выбора валюты для редактирования"""
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Не авторизован!", show_alert=True)
        return
    
    currency_code = call.data.replace('edit_', '')
    
    # Получаем информацию о валюте
    rates = currency_manager.get_current_rates()
    currency_info = next((c for c in rates if c['code'] == currency_code), None)
    
    if not currency_info:
        bot.answer_callback_query(call.id, "❌ Валюта не найдена")
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        f"✏️ *Редактирование {currency_info['name']}*\n\n"
        f"Введите курс *покупки* (только число, например: 95.5):",
        parse_mode='Markdown'
    )
    
    bot.register_next_step_handler(msg, process_buy_rate, currency_code)

def process_buy_rate(message, currency_code):
    """Обработка ввода курса покупки"""
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Сессия истекла. Авторизуйтесь снова.")
        return
        
    try:
        buy_rate = float(message.text.replace(',', '.'))
        
        if buy_rate <= 0:
            bot.send_message(message.chat.id, "❌ Курс должен быть больше 0. Попробуйте снова:")
            bot.register_next_step_handler(message, process_buy_rate, currency_code)
            return
        
        # Запрашиваем курс продажи
        msg = bot.send_message(
            message.chat.id,
            f"Теперь введите курс *продажи* (только число, например: 97.8):",
            parse_mode='Markdown'
        )
        
        bot.register_next_step_handler(msg, process_sell_rate, currency_code, buy_rate)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат числа. Введите число (например: 95.5):")
        bot.register_next_step_handler(message, process_buy_rate, currency_code)

def process_sell_rate(message, currency_code, buy_rate):
    """Обработка ввода курса продажи и сохранение"""
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Сессия истекла. Авторизуйтесь снова.")
        return
        
    try:
        sell_rate = float(message.text.replace(',', '.'))
        
        if sell_rate <= 0:
            bot.send_message(message.chat.id, "❌ Курс должен быть больше 0. Попробуйте снова:")
            bot.register_next_step_handler(message, process_sell_rate, currency_code, buy_rate)
            return
        
        if sell_rate <= buy_rate:
            bot.send_message(message.chat.id, "❌ Курс продажи должен быть выше курса покупки. Попробуйте снова:")
            bot.register_next_step_handler(message, process_sell_rate, currency_code, buy_rate)
            return
        
        # Сохраняем курсы в Firebase
        success = currency_manager.update_currency_rate(currency_code, buy_rate, sell_rate)
        
        if success:
            # Получаем обновленную информацию о валюте
            rates = currency_manager.get_current_rates()
            currency_info = next((c for c in rates if c['code'] == currency_code), None)
            
            response = f"✅ *Курсы обновлены!*\n\n"
            response += f"*{currency_info['name'] if currency_info else currency_code}*\n"
            response += f"🏦 Покупка: `{buy_rate:.2f} ₽`\n"
            response += f"💸 Продажа: `{sell_rate:.2f} ₽`\n"
            response += f"🕐 Обновлено: {datetime.now().strftime('%H:%M')}"
            
            bot.send_message(message.chat.id, response, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ Ошибка при сохранении курсов в базу данных")
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат числа. Введите число (например: 97.8):")
        bot.register_next_step_handler(message, process_sell_rate, currency_code, buy_rate)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def handle_cancel(call):
    """Обработка отмены"""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "Действие отменено")

@bot.message_handler(func=lambda message: message.text == '🔄 Обновить все')
@require_auth
def handle_update_all(message):
    """Обновить все курсы"""
    # Здесь можно добавить логику массового обновления
    # Например, увеличение всех курсов на определенный процент
    bot.send_message(message.chat.id, "🔄 Функция массового обновления в разработке")

@bot.message_handler(func=lambda message: message.text == '❓ Помощь')
@bot.message_handler(commands=['help'])
def send_help(message):
    """Справка по командам"""
    help_text = """
💱 *Доступные команды:*

*/start* - Главное меню
*/rates* - Текущие курсы
*/auth* - Авторизация
*/help* - Эта справка

*Быстрые кнопки:*
📊 Текущие курсы - Показать все курсы
✏️ Изменить курс - Изменить курс валюты (требует авторизации)
🔄 Обновить все - Массовое обновление (в разработке)
🔐 Авторизация - Войти в систему
🚪 Выйти - Выйти из системы
❓ Помощь - Эта справка

*Инструкция по изменению курса:*
1. Нажмите *"🔐 Авторизация"* и введите пароль
2. Нажмите *"✏️ Изменить курс"*
3. Выберите валюту из списка
4. Введите курс покупки
5. Введите курс продажи
6. Курсы автоматически обновятся на сайте

*Примечание:* Курс продажи должен быть выше курса покупки.

*Пароль:* `oper2025`
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def handle_other_messages(message):
    """Обработка других сообщений"""
    if message.text not in ['📊 Текущие курсы', '✏️ Изменить курс', '🔄 Обновить все', '❓ Помощь', '🔐 Авторизация', '🚪 Выйти']:
        bot.send_message(
            message.chat.id, 
            "🤔 Не понимаю команду. Используйте кнопки меню или /help для справки."
        )

if __name__ == "__main__":
    logging.info("Currency bot started...")
    logging.info(f"Bot password: {BOT_PASSWORD}")
    
    try:
        rates = currency_manager.get_current_rates()
        logging.info(f"Loaded {len(rates)} currencies from Firebase")
    except Exception as e:
        logging.error(f"Failed to load currencies: {e}")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        logging.error(f"Bot stopped with error: {e}")