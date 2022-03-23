import requests
import telegram
import os
import logging
from time import sleep


DVMN_TOKEN = os.environ['DVMN_TOKEN']
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_TG_CHAT_ID = os.environ['ADMIN_TG_CHAT_ID']
TG_CHAT_ID = os.environ['TG_CHAT_ID']

LONG_POLLING_USER_REVIEWS_URL = "https://dvmn.org/api/long_polling/"
AUTH_HEADER = {'Authorization': f'Token {DVMN_TOKEN}'}

MSG_HEADER_TEMPLATE = "У вас проверили работу {}\n"
SUCCESS_MSG_BODY = "Преподавателю все понравилось, можно приступать к следующему уроку\n"
FAIL_MSG_BODY = "К сожалению, в работе нашлись ошибки\n"

SECONDS_TO_SLEEP = 5
RESPONSE_TIMEOUT = 30
MAX_RETRIES = 5

app_logger = logging.getLogger(__file__)
admin_logger = logging.getLogger('admin')


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, admin_chat_id):
        super().__init__()
        self.bot = tg_bot
        self.admin_chat_id = admin_chat_id

    def emit(self, record):
        log_msg = self.format(record)
        self.bot.send_message(text=log_msg, chat_id=self.admin_chat_id)


def request_user_reviews(params, url, headers, timeout):

    app_logger.info(f"Sending request to url={url} with params={params}")
    response = requests.get(url,
                            headers=headers,
                            params=params,
                            timeout=timeout)
    response.raise_for_status()
    return response.json()


def main(chat_id, admin_chat_id, n_retries, tg_token, dvmn_url, headers, timeout,
         sleep_time, msg_header_template, success_msg_body, fail_msg_body):

    bot = telegram.Bot(token=tg_token)

    # Присылаем в телеграм админу
    admin_logger.setLevel(logging.DEBUG)
    admin_logger.addHandler(TelegramLogsHandler(bot, admin_chat_id))
    admin_logger.warning("Bot start")

    # Логи приложения, не требуют отправки в телеграм
    app_logger.setLevel(logging.DEBUG)
    
    current_request_timestamp = None

    while True:
        try:
            user_reviews = request_user_reviews(url=dvmn_url,
                                                headers=headers,
                                                timeout=timeout,
                                                params={'timestamp': current_request_timestamp})
        except requests.exceptions.ReadTimeout as timeout_error:
            app_logger.error(timeout_error)
            continue

        except requests.exceptions.ConnectionError as conn_error:
            app_logger.error(conn_error)
            sleep(sleep_time)
            continue

        except requests.exceptions.HTTPError as http_error:
            # По KISS принципу просто выведем traceback
            n_retries -= 1
            app_logger.error(f"ERROR: {http_error}, {n_retries} retries left...")
            if not n_retries:
                break
            sleep(sleep_time)

        else:
            if 'timeout' in user_reviews.get('status', ''):
                current_request_timestamp = user_reviews.get('timestamp_to_request')
                app_logger.info(f"Got timestamp from response: {current_request_timestamp}")
            else:
                # Список проверок, которые отозваны
                attempts = user_reviews.get('new_attempts', [])
                admin_logger.info(f"Got attempts from: {attempts}")

                for attempt in attempts:
                    lesson_title = attempt.get('lesson_title')
                    task_success = not attempt.get('is_negative')
                    msg_header = msg_header_template.format(lesson_title)
                    lesson_url = attempt.get('lesson_url')

                    if task_success:
                        msg = f"{msg_header}{success_msg_body}"
                    else:
                        msg = f"{msg_header}{fail_msg_body}"
                    msg += lesson_url
                    bot.send_message(text=msg, chat_id=chat_id)
                    app_logger.info(f"Bot send message={msg} to client={chat_id}")

if __name__ == '__main__':
    main(chat_id=TG_CHAT_ID,
         admin_chat_id=ADMIN_TG_CHAT_ID,
         n_retries=MAX_RETRIES,
         tg_token=TELEGRAM_BOT_TOKEN,
         sleep_time=SECONDS_TO_SLEEP, 
         msg_header_template=MSG_HEADER_TEMPLATE, 
         success_msg_body=SUCCESS_MSG_BODY,
         dvmn_url=LONG_POLLING_USER_REVIEWS_URL,
         headers=AUTH_HEADER,
         timeout=RESPONSE_TIMEOUT,
         fail_msg_body=FAIL_MSG_BODY)
