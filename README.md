# Introduction and Goals
This repository is for telegram bots from [this site](https://dvmn.org/modules/chat-bots/)

# 1. NotificationBot
Can be found at [telegram](t.me/DvmnFirstBot).
Notifies when submtitted task is checked by a teacher.

**Example:**
<img width="343" alt="Screenshot 2022-03-20 at 15 41 21" src="https://user-images.githubusercontent.com/50524041/159160518-0e32c756-0191-411f-8353-7a07f2a03e4c.png">

Linux launch:

```bash

$ pip3 install -r requirements.txt & python3 notification_bot/notification_bot.py

starts infinite loop. Bot sends messages.

```

## Environment variables
It's essential to fill in your own env variables. You need to specify:
 ```- TG_CHAT_ID # which chat to be sent messages
    - DVMN_TOKEN # devman token to achieve api
 ```


# Other bots are coming soon....
