# Телеграм бот для ответов на комментарии

Этот бот помогает создавать ответы на комментарии в социальных сетях, анализируя контент по ссылке и генерируя варианты ответов на комментарии.

## Возможности

- Анализ контента по ссылке с различных платформ (YouTube, TikTok, Instagram, Twitter/X, ВКонтакте, Яндекс Дзен, Telegram)
- Распознавание текста комментариев с изображений
- Генерация стратегических целей для ответа
- Создание естественных ответов на комментарии с учетом выбранной цели

## Технологии

- Python
- Telegram Bot API (telebot)
- OpenAI API (GPT-4o, GPT-4 Turbo)
- Perplexity API (Sonar Pro)
- Обход региональных ограничений через SOCKS5 прокси

## Установка и настройка

### Требования

- Python 3.8+
- Токен бота Telegram
- Ключ API OpenAI
- Ключ API Perplexity

### Шаги по установке

1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш_логин/ваш_репозиторий.git
cd ваш_репозиторий
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе примера:
```bash
cp .env.example .env
```

4. Отредактируйте файл `.env`, добавив свои токены API:
```
TELEGRAM_TOKEN=ваш_токен_телеграм_бота
OPENAI_API_KEY=ваш_ключ_api_openai
PERPLEXITY_API_KEY=ваш_ключ_api_perplexity

# Опционально, для обхода региональных ограничений Perplexity API:
PROXY_HOST=хост_прокси
PROXY_PORT=порт_прокси
PROXY_USERNAME=имя_пользователя_прокси  # если требуется
PROXY_PASSWORD=пароль_прокси  # если требуется
```

5. Замените `@grisha123invent` в файле `telebot_version.py` на ваш Telegram-аккаунт, если вы не являетесь оригинальным создателем.

### Запуск бота

```bash
python telebot_version.py
```

## Использование

1. Найдите своего бота в Telegram по имени
2. Отправьте команду `/start` для начала работы
3. Отправьте ссылку на пост или видео
4. Отправьте комментарий, на который нужно ответить (текстом или картинкой)
5. Выберите цель для ответа из предложенных или напишите свою
6. Получите готовый ответ!

## Обработка ошибок

- Если у вас возникает ошибка при работе с Perplexity API связанная с регионом `unsupported_country_region_territory`, настройте SOCKS5 прокси в файле `.env`
- В России для работы с OpenAI API может потребоваться VPN или настройка прокси

## Лицензия

Этот проект распространяется под лицензией MIT с дополнительным требованием атрибуции.

**Важно:** Согласно лицензии, при использовании этого кода в любой форме необходимо явно указывать оригинального создателя (@grisha123invent) в пользовательском интерфейсе, документации или другом видимом пользователю компоненте. 