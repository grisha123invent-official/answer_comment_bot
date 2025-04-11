import os
import logging
import telebot
from telebot import types
import requests
import json
import re
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI
import socks
import socket

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токены API
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = os.getenv("PROXY_PORT")
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)   

# Состояния пользователя
WAITING_FOR_LINK = 1
WAITING_FOR_COMMENT = 2
WAITING_FOR_GOAL = 3

# Словарь для хранения состояний пользователей
user_states = {}

# Функция для определения типа платформы по ссылке
def identify_platform(url):
    if re.search(r'(youtube\.com|youtu\.be)', url):
        return "YouTube"
    elif "tiktok.com" in url:
        return "TikTok"
    elif "instagram.com" in url:
        return "Instagram"
    elif re.search(r'(twitter\.com|x\.com)', url):
        return "Twitter/X"
    elif "vk.com" in url:
        if "/clip" in url or "/clips" in url or "/video" in url:
            return "ВКонтакте-видео"
        return "ВКонтакте"
    elif "dzen.ru" in url:
        if "/video" in url:
            return "Яндекс Дзен-видео"
        return "Яндекс Дзен"
    elif "t.me" in url:
        return "Telegram"
    else:
        return "Неизвестная платформа"

# Функция для настройки прокси
def setup_proxy():
    if all([PROXY_HOST, PROXY_PORT]):
        try:
            port = int(PROXY_PORT)
            proxy_dict = {
                "http": f"socks5://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{port}" if PROXY_USERNAME else f"socks5://{PROXY_HOST}:{port}",
                "https": f"socks5://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{port}" if PROXY_USERNAME else f"socks5://{PROXY_HOST}:{port}"
            }
            
            # Настройка для requests
            return proxy_dict
        except Exception as e:
            logger.error(f"Ошибка настройки прокси: {e}")
    
    return None

# Функция для анализа контента с помощью Perplexity API
def analyze_content(url):
    try:
        platform = identify_platform(url)
        proxy = setup_proxy()
        
        try:
            # Пробуем сначала без прокси
            client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
            
            messages = [
                {
                    "role": "system",
                    "content": "Ты аналитик контента. Твоя задача - проанализировать контент по ссылке и описать основные тезисы, тему и тональность."
                },
                {
                    "role": "user",
                    "content": f"Проанализируй контент по этой ссылке: {url}. Опиши основные тезисы, тему и тональность контента. Информация будет использована для генерации ответов на комментарии."
                }
            ]
            
            response = client.chat.completions.create(
                model="sonar-pro",
                messages=messages
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            # Если получаем ошибку про регион, пробуем через прокси
            error_str = str(e)
            if "unsupported_country_region_territory" in error_str and proxy:
                logger.info("Используем прокси для Perplexity API из-за ограничения региона")
                
                # Используем обычный requests запрос через прокси
                headers = {
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "sonar-pro",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты аналитик контента. Твоя задача - проанализировать контент по ссылке и описать основные тезисы, тему и тональность."
                        },
                        {
                            "role": "user",
                            "content": f"Проанализируй контент по этой ссылке: {url}. Опиши основные тезисы, тему и тональность контента. Информация будет использована для генерации ответов на комментарии."
                        }
                    ]
                }
                
                response = requests.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=data,
                    proxies=proxy,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"Ошибка Perplexity API с прокси: {response.status_code}, {response.text}")
            else:
                # Если ошибка не связана с регионом или нет прокси, пробрасываем ошибку дальше
                raise e
            
    except Exception as e:
        logger.error(f"Ошибка при анализе контента: {e}")
        return f"Ошибка при анализе контента: {str(e)}. Продолжаем работу."

# Функция для распознавания текста с изображения
def recognize_text_from_image(photo_file_id):
    try:
        # Получаем файл из Telegram
        file_info = bot.get_file(photo_file_id)
        file = requests.get(f'https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}')
        
        # Кодируем в base64
        import base64
        photo_bytes = BytesIO(file.content).read()
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Инициализируем клиент OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Прочитай текст с этого изображения. Если на изображении комментарий из социальной сети, верни только текст комментария. Если это скриншот, найди основной комментарий и верни его."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Ошибка при распознавании текста: {e}")
        return None

# Функция для генерации целей ответа
def generate_goals(content_analysis, comment):
    try:
        # Инициализируем клиент OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        messages = [
            {
                "role": "system",
                "content": "Ты стратег, который помогает создавать эффективные ответы на комментарии."
            },
            {
                "role": "user",
                "content": f"""
                Контекст: {content_analysis}

                Комментарий пользователя: {comment}

                Предложи 3 разные стратегические цели для ответа на этот комментарий. Цели могут быть:
                - Согласиться и развить мысль
                - Вежливо не согласиться
                - Задать уточняющий вопрос
                - Поднять шумиху/вовлеченность
                - Перевести разговор на свой продукт/услугу
                - Пошутить
                - Другое, что подходит по контексту

                Формат ответа: только список из 3 целей, пронумерованных от 1 до 3, каждая цель одним предложением.
                """
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip().split("\n")
    
    except Exception as e:
        logger.error(f"Ошибка при генерации целей: {e}")
        return ["1. Согласиться и поддержать", "2. Вежливо не согласиться", "3. Задать уточняющий вопрос"]

# Функция для генерации ответа
def generate_response(content_analysis, comment, goal):
    try:
        # Инициализируем клиент OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        messages = [
            {
                "role": "system",
                "content": "Ты копирайтер, который создает естественные и грамотные ответы на комментарии."
            },
            {
                "role": "user",
                "content": f"""
                Контекст: {content_analysis}

                Комментарий пользователя: {comment}

                Цель ответа: {goal}

                Сгенерируй естественный и грамотный ответ на комментарий от лица автора контента. 
                Ответ должен быть естественным, без формальностей, как будто его пишет реальный человек в социальной сети.
                Тон и стиль ответа должны соответствовать цели и контексту.

                Ответ должен быть достаточно коротким (до 2-3 предложений), но информативным.
                """
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        return f"Ошибка при генерации ответа: {str(e)}. Пожалуйста, попробуйте еще раз."

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    user_states[user_id] = {
        "state": WAITING_FOR_LINK,
        "content_analysis": None,
        "comment": None
    }
    
    bot.send_message(message.chat.id, 
                    f"Привет, {message.from_user.first_name}! Я бот для создания ответов на комментарии.\n\n"
                    "🧠 Разработан @grisha123invent\n\n"
                    "Как со мной работать:\n"
                    "1. Отправь мне ссылку на пост или видео\n"
                    "2. Затем отправь текст комментария или скриншот с комментарием\n"
                    "3. Я предложу варианты целей для ответа\n"
                    "4. Выбери цель, и я сгенерирую ответ\n\n"
                    "Отправь /help для получения дополнительной информации.")

# Обработчик команды /help
@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.send_message(message.chat.id, 
                    "📱 Бот для ответов на комментарии\n"
                    "🧠 Разработан @grisha123invent\n\n"
                    "Команды:\n"
                    "/start - начать работу с ботом\n"
                    "/help - показать эту справку\n"
                    "/test - протестировать все API\n\n"
                    "Поддерживаемые платформы:\n"
                    "• YouTube\n"
                    "• TikTok\n"
                    "• Instagram\n"
                    "• Twitter/X\n"
                    "• ВКонтакте\n"
                    "• Яндекс Дзен\n"
                    "• Telegram\n\n"
                    "Если у вас возникают проблемы, обратитесь к разработчику.")

# Обработчик команды /test для проверки работоспособности бота
@bot.message_handler(commands=['test'])
def test_command(message):
    bot.reply_to(message, "Бот работает! 👍")
    logger.info(f"Получена тестовая команда от пользователя {message.from_user.id}")

# Обработчик фотографий
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    
    # Если пользователь отправил фото, но мы не ожидали комментарий
    if user_id not in user_states or user_states[user_id]["state"] != WAITING_FOR_COMMENT:
        bot.reply_to(message, "Сначала отправьте ссылку на контент, а затем фото с комментарием.")
        return
    
    bot.send_message(message.chat.id, "Получил картинку. Распознаю текст комментария...")
    
    # Берем последнее (самое большое) фото
    photo_file_id = message.photo[-1].file_id
    
    # Распознаем текст с фото
    recognized_text = recognize_text_from_image(photo_file_id)
    
    if recognized_text:
        # Показываем распознанный текст
        bot.send_message(
            message.chat.id,
            f"Распознанный комментарий: \n\n{recognized_text}\n\nГенерирую варианты ответа..."
        )
        
        # Сохраняем комментарий и переходим к генерации целей
        user_states[user_id]["comment"] = recognized_text
        user_states[user_id]["state"] = WAITING_FOR_GOAL
        
        # Генерируем цели для ответа
        goals = generate_goals(user_states[user_id]["content_analysis"], recognized_text)
        
        # Создаем клавиатуру с кнопками
        markup = types.InlineKeyboardMarkup()
        
        # Добавляем кнопки для целей
        for i, goal in enumerate(goals, 1):
            # Убираем номер в начале строки, если он есть
            goal_text = re.sub(r'^\d+\.\s*', '', goal)
            markup.add(types.InlineKeyboardButton(goal_text, callback_data=f"goal_{i}"))
        
        # Добавляем кнопку для своей цели
        markup.add(types.InlineKeyboardButton("✍️ Своя цель", callback_data="goal_custom"))
        
        bot.send_message(
            message.chat.id,
            "Выберите цель для ответа:",
            reply_markup=markup
        )
    else:
        bot.send_message(
            message.chat.id,
            "Не удалось распознать текст с изображения. Пожалуйста, отправьте комментарий текстом."
        )

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    
    # Если пользователь новый, инициализируем его состояние
    if user_id not in user_states:
        user_states[user_id] = {
            "state": WAITING_FOR_LINK,
            "content_analysis": None,
            "comment": None
        }
    
    current_state = user_states[user_id]["state"]
    
    # Ожидаем ссылку на контент
    if current_state == WAITING_FOR_LINK:
        # Проверка, является ли сообщение ссылкой
        if re.match(r'https?://\S+', message.text):
            url = message.text
            platform = identify_platform(url)
            
            bot.send_message(
                message.chat.id,
                f"Анализирую контент с платформы {platform}... Это может занять некоторое время."
            )
            
            # Анализируем контент
            content_analysis = analyze_content(url)
            
            user_states[user_id]["content_analysis"] = content_analysis
            user_states[user_id]["state"] = WAITING_FOR_COMMENT
            
            bot.send_message(
                message.chat.id,
                "✅ Контент проанализирован!\n\n"
                "Теперь отправь мне комментарий, на который нужно ответить."
            )
        else:
            bot.send_message(
                message.chat.id,
                "Пожалуйста, отправьте корректную ссылку на пост или видео."
            )
    
    # Ожидаем комментарий
    elif current_state == WAITING_FOR_COMMENT:
        user_states[user_id]["comment"] = message.text
        user_states[user_id]["state"] = WAITING_FOR_GOAL
        
        # Генерируем цели для ответа
        goals = generate_goals(user_states[user_id]["content_analysis"], message.text)
        
        # Создаем клавиатуру с кнопками
        markup = types.InlineKeyboardMarkup()
        
        # Добавляем кнопки для целей
        for i, goal in enumerate(goals, 1):
            # Убираем номер в начале строки, если он есть
            goal_text = re.sub(r'^\d+\.\s*', '', goal)
            markup.add(types.InlineKeyboardButton(goal_text, callback_data=f"goal_{i}"))
        
        # Добавляем кнопку для своей цели
        markup.add(types.InlineKeyboardButton("✍️ Своя цель", callback_data="goal_custom"))
        
        bot.send_message(
            message.chat.id,
            "Выберите цель для ответа:",
            reply_markup=markup
        )
    
    # Если пользователь выбрал свою цель и отправил её текстом
    elif current_state == WAITING_FOR_GOAL and user_states[user_id].get("custom_goal_requested"):
        goal = message.text
        user_states[user_id]["custom_goal_requested"] = False
        
        bot.send_message(
            message.chat.id,
            "Генерирую ответ... Это может занять несколько секунд."
        )
        
        # Генерируем ответ
        response = generate_response(
            user_states[user_id]["content_analysis"],
            user_states[user_id]["comment"],
            goal
        )
        
        bot.send_message(
            message.chat.id,
            f"🎯 *Цель:* {goal}\n\n"
            f"💬 *Ответ:*\n{response}\n\n"
            "Отправьте новую ссылку, чтобы начать сначала.",
            parse_mode="Markdown"
        )
        
        # Сбрасываем состояние пользователя
        user_states[user_id]["state"] = WAITING_FOR_LINK
        user_states[user_id]["content_analysis"] = None
        user_states[user_id]["comment"] = None

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    callback_data = call.data
    
    if callback_data.startswith("goal_") and user_id in user_states:
        if callback_data == "goal_custom":
            user_states[user_id]["custom_goal_requested"] = True
            bot.edit_message_text(
                "Опишите свою цель для ответа:",
                call.message.chat.id,
                call.message.message_id
            )
            return
        
        # Получаем индекс цели
        goal_index = int(callback_data.split("_")[1]) - 1
        
        # Получаем список целей
        goals = generate_goals(user_states[user_id]["content_analysis"], user_states[user_id]["comment"])
        goal = re.sub(r'^\d+\.\s*', '', goals[goal_index])
        
        bot.edit_message_text(
            "Генерирую ответ... Это может занять несколько секунд.",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Генерируем ответ
        response = generate_response(
            user_states[user_id]["content_analysis"],
            user_states[user_id]["comment"],
            goal
        )
        
        bot.send_message(
            call.message.chat.id,
            f"🎯 *Цель:* {goal}\n\n"
            f"💬 *Ответ:*\n{response}\n\n"
            "Отправьте новую ссылку, чтобы начать сначала.",
            parse_mode="Markdown"
        )
        
        # Сбрасываем состояние пользователя
        user_states[user_id]["state"] = WAITING_FOR_LINK
        user_states[user_id]["content_analysis"] = None
        user_states[user_id]["comment"] = None

# Проверка токенов API перед запуском
def check_api_tokens():
    if not TELEGRAM_TOKEN:
        logger.error("Ошибка: TELEGRAM_TOKEN не найден в .env файле")
        return False
    
    if not OPENAI_API_KEY:
        logger.error("Ошибка: OPENAI_API_KEY не найден в .env файле")
        return False
    
    if not PERPLEXITY_API_KEY:
        logger.error("Ошибка: PERPLEXITY_API_KEY не найден в .env файле")
        return False
    
    # Проверка настроек прокси
    if not all([PROXY_HOST, PROXY_PORT]) and any([PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD]):
        logger.warning("Внимание: настройки прокси указаны не полностью. Для работы прокси нужны как минимум PROXY_HOST и PROXY_PORT")
    
    return True

# Запуск бота
if __name__ == "__main__":
    print("Инициализация бота...")
    
    # Проверяем токены API
    if check_api_tokens():
        print("Все токены API найдены")
        
        try:
            # Сбрасываем вебхуки, которые могли остаться от предыдущих запусков
            bot.remove_webhook()
            print("Вебхуки успешно сброшены")
            
            # Запускаем бота
            print("Бот запущен и готов к работе!")
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Ошибка при запуске бота: {e}")
            logger.error(f"Ошибка при запуске бота: {e}")
    else:
        print("Ошибка: один или несколько токенов API отсутствуют в .env файле") 