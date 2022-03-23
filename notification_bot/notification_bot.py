import requests
import telegram
import os
import logging
from time import sleep


DVMN_TOKEN = os.environ['DVMN_TOKEN']
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT_ID = os.environ['TG_CHAT_ID']

LONG_POLLING_USER_REVIEWS_URL = "https://dvmn.org/api/long_polling/"
AUTH_HEADER = {'Authorization': f'Token {DVMN_TOKEN}'}

MSG_HEADER_TEMPLATE = "У вас проверили работу {}\n"
SUCCESS_MSG_BODY = "Преподавателю все понравилось, можно приступать к следующему уроку\n"
FAIL_MSG_BODY = "К сожалению, в работе нашлись ошибки\n"

SECONDS_TO_SLEEP = 5
RESPONSE_TIMEOUT = 30
MAX_RETRIES = 5

logger = logging.getLogger(__file__)


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.bot = tg_bot
        self.chat_id = chat_id

    def emit(self, record):
        log_msg = self.format(record)
        self.bot.send_message(text=log_msg, chat_id=self.chat_id)


def request_user_reviews(params, url, headers, timeout):

    logger.info(f"Sending request to url={url} with params={params}")
    response = requests.get(url,
                            headers=headers,
                            params=params,
                            timeout=timeout)
    response.raise_for_status()
    return response.json()


def main(chat_id, max_retries, tg_token, dvmn_url, headers, timeout, sleep_time, msg_header_template, success_msg_body, fail_msg_body):
    logger.setLevel(logging.DEBUG)
    retries = max_retries

    bot = telegram.Bot(token=tg_token)
    logger.addHandler(TelegramLogsHandler(bot, chat_id))
    logger.warning("Bot start")

    current_request_timestamp = None

    while True:
        try:
            user_reviews = request_user_reviews(url=dvmn_url,
                                                headers=headers,
                                                timeout=timeout,
                                                params={'timestamp': current_request_timestamp})
        except requests.exceptions.ReadTimeout as timeout_error:
            logger.error(timeout_error)
            continue

        except requests.exceptions.ConnectionError as conn_error:
            logging.error(conn_error)
            sleep(sleep_time)
            continue

        except requests.exceptions.HTTPError as http_error:
            # По KISS принципу просто выведем traceback
            retries -= 1
            logging.error(f"ERROR: {http_error}, {retries} retries left...")
            if not retries:
                break
            sleep(sleep_time)

        else:
            if 'timeout' in user_reviews.get('status', ''):
                current_request_timestamp = user_reviews.get('timestamp_to_request')
                logger.info(f"Got timestamp from response: {current_request_timestamp}")
            else:
                # Список проверок, которые отозваны
                attempts = user_reviews.get('new_attempts', [])
                logger.info(f"Got attempts from: {attempts}")

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
                    logger.info(f"Bot send message={msg} to client={chat_id}")

if __name__ == '__main__':
    main(chat_id=TG_CHAT_ID,
         max_retries=MAX_RETRIES,
         tg_token=TELEGRAM_BOT_TOKEN,
         sleep_time=SECONDS_TO_SLEEP, 
         msg_header_template=MSG_HEADER_TEMPLATE, 
         success_msg_body=SUCCESS_MSG_BODY,
         dvmn_url=LONG_POLLING_USER_REVIEWS_URL,
         headers=AUTH_HEADER,
         timeout=RESPONSE_TIMEOUT,
         fail_msg_body=FAIL_MSG_BODY)
