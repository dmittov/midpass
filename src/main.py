from midpass import (get_status, format_status)
from telegram_bot import WebhookBot
import telegram
from google.cloud import secretmanager
import os
import logging
from flask import Flask, request
import json
from google.cloud import datastore


app = Flask(__name__)

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("LOGGING_LEVEL", logging.INFO))

client = secretmanager.SecretManagerServiceClient()
project_id = os.environ["PROJECT_ID"]
telegram_token_secret_id = os.environ["TELEGRAM_TOKEN_SECRET_ID"]
name = client.secret_version_path(project_id, telegram_token_secret_id, 1)
telegram_token = client.access_secret_version(name).payload.data.decode('UTF-8')

logger.info("Telegram token read: *******")
hook_path = "/bot"
bot = WebhookBot(telegram_token, hook_path)

# FIXME: unsafe, use randomized hook path
@app.route(bot.hook_path, methods=["POST", "GET"])
def bot_handler():
    update = telegram.Update.de_json(request.get_json(force=True), bot.bot)
    bot.dispatcher.process_update(update)
    return json.dumps({"status": "ok"})


@app.route("/daily")
def daily_handler():
    if "X-AppEngine-Cron" not in request.headers:
        return json.dumps({"status": "ok"})
    query = bot.datastore_client.query(kind=bot.storage_kind)
    for user_record in query.fetch():
        chat_id = user_record.key.id
        dept_id, uid = user_record["dept_id"], user_record["uid"]
        json_status = get_status(dept_id, uid)
        if not json_status:
            response = "No response"
        else:
            response = format_status(json_status)
        bot.bot.send_message(chat_id=chat_id, text=response)
    return json.dumps({"status": "ok"})


if __name__ == '__main__':
    app.run(threaded=True, host='127.0.0.1', port=8080, debug=True)
