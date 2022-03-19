import requests
import telegram
import os
import logging
from time import sleep


DVMN_TOKEN = os.environ['DVMN_TOKEN']
TELEGRAM_BOT_TOKEN = os.envirion["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

LONG_POLLING_USER_REVIEWS_URL = "https://dvmn.org/api/long_polling/"
AUTH_HEADER = {'Authorization': f'Token {DVMN_TOKEN}'}

MSG_HEADER_TEMPLATE = "У вас проверили работу {}\n"
SUCCESS_MSG_BODY = "Преподавателю все понравилось, можно приступать к следующему уроку\n"
FAIL_MSG_BODY = "К сожалению, в работе нашлись ошибки\n"

SECONDS_TO_SLEEP = 5
RESPONSE_TIMEOUT = 30
MAX_RETRIES = 5

logger = logging.getLogger(__file__)

def request_user_reviews(params, url=LONG_POLLING_USER_REVIEWS_URL, headers=AUTH_HEADER, timeout=RESPONSE_TIMEOUT):

    logging.info(f"Sending request to url={LONG_POLLING_USER_REVIEWS_URL} with params={params}")
    response = requests.get(LONG_POLLING_USER_REVIEWS_URL,
                            headers=AUTH_HEADER,
                            params=params,
                            timeout=RESPONSE_TIMEOUT)
    response.raise_for_status()
    return response.json()


def main():
    logging.warning("Bot start")
    retries = MAX_RETRIES
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

    current_request_timestamp = None

    while True:
        try:
            user_reviews = request_user_reviews(params={'timestamp': current_request_timestamp})
        except requests.exceptions.ReadTimeout as timeout_error:
            logging.error(timeout_error)
            continue

        except requests.exceptions.ConnectionError as conn_error:
            logging.error(conn_error)
            sleep(SECONDS_TO_SLEEP)
            continue

        except requests.exceptions.HTTPError as http_error:
            # По KISS принципу просто выведем traceback
            retries -= 1
            msg = f"ERROR: {http_error}, {retries} retries left..."
            logging.error(msg)
            bot.send_message(text=msg, chat_id=TELEGRAM_CHAT_ID)
            if not retries:
                break
            sleep(SECONDS_TO_SLEEP)

        else:
            if 'timeout' in user_reviews.get('status', ''):
                current_request_timestamp = user_reviews.get('timestamp_to_request')
                logging.info(f"Got timestamp from response: {current_request_timestamp}")
            else:
                # Список проверок, которые отозваны
                attempts = user_reviews.get('new_attempts', [])
                logging.info(f"Got attempts from: {attempts}")

                for attempt in attempts:
                    lesson_title = attempt.get('lesson_title')
                    task_success = not attempt.get('is_negative')
                    msg_header = MSG_HEADER_TEMPLATE.format(lesson_title)
                    lesson_url = attempt.get('lesson_url')
                
                    if task_success:
                        msg = f"{msg_header}{SUCCESS_MSG_BODY}"
                    else:
                        msg = f"{msg_header}{FAIL_MSG_BODY}"
                    msg += lesson_url
                    logging.info(f"Bot send message={msg} to client={TELEGRAM_CHAT_ID}")
                    bot.send_message(text=msg, chat_id=TELEGRAM_CHAT_ID)

if __name__ == '__main__':
    logging.basicConfig(filename='logs/bot.log', level=logging.DEBUG)
    main()
