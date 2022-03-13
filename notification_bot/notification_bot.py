import requests
import telegram
from dotenv import dotenv_values
import os


# .env переменные, токены бота и девмана
ENV_CONFIG = dotenv_values(".env")
DVMN_TOKEN = ENV_CONFIG["DVMN_TOKEN"]
BOT_TOKEN = ENV_CONFIG["BOT_TOKEN"]

# В environ добавил через export
MY_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

# API переменные, url, заголовки
POLLING_USER_REVIEWS_URL = "https://dvmn.org/api/user_reviews/"
LONG_POLLING_USER_REVIEWS_URL = "https://dvmn.org/api/long_polling/"
AUTH_HEADER = {'Authorization': f'Token {DVMN_TOKEN}'}

MSG_HEADER_TEMPLATE = "У вас проверили работу {}\n"
SUCCESS_MSG_BODY = "Преподавателю все понравилось, можно приступать к следующему уроку\n"
FAIL_MSG_BODY = "К сожалению, в работе нашлись ошибки\n"

bot = telegram.Bot(token=BOT_TOKEN)


"""Такой подход, когда раз в n секунд опрашивается сторонний сервис, называется polling.
Чтобы сэкономить на ресурсах, можно использовать long polling. Устроен он так же, как и polling, 
с одним отличием: сервер дольше отвечает. Вообще, при лонг-поллинге сервер отвечает в двух случаях: или потому, что пришло новое сообщение, или потому, что соединение пора разрывать.

У каждого запроса есть timeout — время, в течении которого нужно ответить. Если на запрос не ответили за это время, считается, что сервер не ответит вообще. Поэтому сервер смотрит на timeout и решает так:

Если за это время у меня не появится обновлений для клиента, я отвечу ему, что их нет.
Если появятся, я отправлю ему обновления сразу, не дожидаясь таймаута.
Чтобы реализовать long polling на стороне клиента, нужно выставить большой timeout: 30 или 60 секунд."""


current_request_timestamp = None
# Чтобы всегда быть в курсе событий, он должен слать запросы постоянно, один за другим.
while True:
    try:
        # Если мы уже получили current_request_timestamp, то в параметрах timestamp передаем его
        if current_request_timestamp:
            response = requests.get(LONG_POLLING_USER_REVIEWS_URL,
                                    headers=AUTH_HEADER,
                                    timestamp=current_request_timestamp,
                                    timeout=5)
        else:
            # Иначе шлем запрос без него
            response = requests.get(LONG_POLLING_USER_REVIEWS_URL,
                                    headers=AUTH_HEADER,
                                    timeout=5)
    # Если нет соединения или сервер не успел ответить за таймаут, просто повторяем отправку запроса
    except requests.exceptions.ReadTimeout:
        # print("ReadTimeout")
        continue
    except requests.exceptions.ConnectionError:
        # print("Connection Error")
        continue
    else:
        # Если смогли получить ответ на GET запрос, парсим ответ.
        response_json = response.json()

        # При таймаут статусе нам понадобится timestamp_to_request
        if response_json.get('status', '') == 'timeout':
            current_request_timestamp = response_json.get('timestamp_to_request')
        else:
            # Иначе получаем список проверок, которые отозваны
            attempts_list = response_json.get('new_attempts', [])
            for attempt_dct in attempts_list:
                lesson_title = attempt_dct.get('lesson_title')
                task_success = not attempt_dct.get('is_negative')
                msg_header = MSG_HEADER_TEMPLATE.format(lesson_title)
                lesson_url = attempt_dct.get('lesson_url')
            
                if task_success:
                    msg = f"{msg_header}{SUCCESS_MSG_BODY}"
                else:
                    msg = f"{msg_header}{FAIL_MSG_BODY}"
                msg += lesson_url
                bot.send_message(text=msg, chat_id=MY_CHAT_ID)
