import requests
import telegram
from dotenv import dotenv_values
import os
from time import sleep


ENV_CONFIG = dotenv_values(".env")
DVMN_TOKEN = ENV_CONFIG["DVMN_TOKEN"]
TELEGRAM_BOT_TOKEN = ENV_CONFIG["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

LONG_POLLING_USER_REVIEWS_URL = "https://dvmn.org/api/long_polling/"
AUTH_HEADER = {'Authorization': f'Token {DVMN_TOKEN}'}

MSG_HEADER_TEMPLATE = "У вас проверили работу {}\n"
SUCCESS_MSG_BODY = "Преподавателю все понравилось, можно приступать к следующему уроку\n"
FAIL_MSG_BODY = "К сожалению, в работе нашлись ошибки\n"

SECONDS_TO_SLEEP = 120


def main():
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

    current_request_timestamp = None

    while True:

        try:
            params = {'timestamp': current_request_timestamp}
            response = requests.get(LONG_POLLING_USER_REVIEWS_URL,
                                    headers=AUTH_HEADER,
                                    params=params,
                                    timeout=5)
        except requests.exceptions.ReadTimeout:
            continue
        except requests.exceptions.ConnectionError:
            sleep(SECONDS_TO_SLEEP)
            continue
        else:
            # Если смогли получить ответ на GET запрос, парсим ответ.
            decoded_response = response.json()

            if decoded_response.get('status', '') == 'timeout':
                current_request_timestamp = decoded_response.get('timestamp_to_request')
            else:
                # Список проверок, которые отозваны
                attempts = decoded_response.get('new_attempts', [])

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
                    bot.send_message(text=msg, chat_id=TELEGRAM_CHAT_ID)

if __name__ == '__main__':
    main()
