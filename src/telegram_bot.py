import logging
import os
import requests
from telegram import Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from google.cloud import datastore
from midpass import (get_status, format_status)

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("LOGGING_LEVEL", logging.INFO))

class WebhookBot:

    def __init__(self, telegram_token, hook_path):
        self.hook_path = hook_path # + token_urlsafe(32)
        self.bot_name = os.environ["BOT_NAME"]
        self.bot = Bot(token=telegram_token)
        self.dispatcher = Dispatcher(bot=self.bot, update_queue=None, workers=0, use_context=True)
        self._set_handlers()
        self.datastore_client = datastore.Client()
        self.storage_kind = "user_registry"
        # self.__set_webhook()

    def __set_webhook(self):
        url = f"https://{os.environ['GOOGLE_CLOUD_PROJECT']}.appspot.com{self.hook_path}"
        if self.bot.set_webhook(url):
            logger.info("webhook setup ok: %s", url)
        else:
            logger.error("webhook setup failed: %s", url)
            raise RuntimeError("Couldn't setup webhook")

    def _set_handlers(self):
        self.dispatcher.add_handler(CommandHandler(["start", "help", "about"], self._help))
        self.dispatcher.add_handler(CommandHandler("register", self._register))
        self.dispatcher.add_handler(CommandHandler("unregister", self._unregister))
        self.dispatcher.add_handler(CommandHandler("check", self._check))
        self.dispatcher.add_error_handler(self._error)

    def _register(self, update, context):
        chat_id = update.message.chat_id
        try:
            key = self.datastore_client.key(self.storage_kind, chat_id)
            user_record = datastore.Entity(key=key)
            tokens = update.message.text.split()[1:]
            dept_id, uid = [int(token.strip()) for token in tokens]
            user_record["uid"] = uid
            user_record["dept_id"] = dept_id
            self.datastore_client.put(user_record)
            context.bot.send_message(chat_id=chat_id, text="saved")
        except Exception as exc:
            logger.error(exc)
            context.bot.send_message(chat_id=chat_id, text="save failed")

    def _unregister(self, update, context):
        chat_id = update.message.chat_id
        key = self.datastore_client.key(self.storage_kind, chat_id)
        self.datastore_client.delete(key)
        context.bot.send_message(chat_id=chat_id, text="unregistred")

    def _check(self, update, context):
        chat_id = update.message.chat_id
        key = self.datastore_client.key(self.storage_kind, chat_id)
        user_record = self.datastore_client.get(key)
        dept_id, uid = user_record["dept_id"], user_record["uid"]
        json_status = get_status(dept_id, uid)
        if not json_status:
            response = "No response"
        else:
            response = format_status(json_status)
        context.bot.send_message(chat_id=chat_id, text=response)

    @staticmethod
    def _help(update, context):
        help_message = "/start /help /about\n" \
            "/register dept_id uid\n" \
            "/unregister\n" \
            "/check\n" \
            f"chat_id={update.message.chat_id}"
        context.bot.send_message(chat_id=update.message.chat_id, text=help_message)

    @staticmethod
    def _error(update, context):
        logger.warn('Update "%s" caused error "%s"' % (update, context.error))
