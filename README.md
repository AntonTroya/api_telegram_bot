Инструкция по работе с проектом: API + Telegram bot



1. В CMD перейдите в папку проекта: Диск:\путь\api_telegram_bot, установите зависимости: requirements.txt
	командой: pip install -r requirements.txt


2. Создайте в корне проекта файл: .env с содержимым: TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН
	В Telegram (@BotFather) создать бота, получите токен и добавьте его в файл .env


3. Данные из БД лежат в: Диск:\путь\api_telegram_bot\data\raw\spb_rentals.db


4. Запуск API
	В CMD перейдите в : Диск:\путь\api_telegram_bot (команда: api_telegram_bot>python -m uvicorn api.main:app --reload --port 8000)
	Появится информация: Успешный запуск: INFO: Uvicorn running on http://127.0.0.1:8000 INFO: Application startup complete

5. Запуск telegram бота
	Откройте еще одно окно CMD, перейдите в: Диск:\путь\api_telegram_bot, запустите bot.py (команда: python -m bot.bot)



6. Завершение работы
	В CMD, команда: Ctrl + c


* В папке: screenshots - скриншоты по запуску и работе бота.