from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from bridges import Bridges
import threading, os
import fbbridge


class Bridge:
    chats = []
    bot = None

    def __init__(self, tgToken, fbEmail, fbPasswd):
        # TG
        updater = Updater(tgToken, use_context=True)

        self.bot = updater.bot

        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", self.startCommand))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.onMessage))

        # FB
        fbbridge.init(
            self.sendMessage, self.requestChat, self.updateChat, fbEmail, fbPasswd,
        )

        updater.start_polling()
        print("tg client starting")
        updater.idle()

    def onMessage(self, update, context):
        chatId = update.message.chat.id
        msgTex = update.message.text
        if not chatId in self.getChatIds():
            update.message.reply_text("chat not registered")
            return
        (_, typ) = self.getChatById(chatId)
        print(typ)
        if typ == Bridges.fb:
            fbbridge.sendMessage(msgTex, chatId)

    def sendMessage(self, text, chatid):
        if chatid == None:
            return
        self.getChatById(chatid)[0].send_message(text)

    def startCommand(self, update, context):
        update.message.reply_text("Registering chat...")
        chat = update.message.chat
        if chat.id in self.getChatIds():
            update.message.reply_text(
                f"Chat already registerd as a bridge to {self.getChatById(chat.id)[0]}"
            )
        else:
            self.chats.append((chat, Bridges.empty))
            update.message.reply_text(f'Chat registered with id "{chat.id}"')

    def getChatIds(self):
        ids = []
        for c in self.chats:
            ids.append(c[0].id)
        return ids

    def getChatById(self, id):
        for cht, brg in self.chats:
            if cht.id == id:
                return (cht, brg)
        raise Exception("Chat not found")

    def requestChat(self, bridgeType):
        for i in range(len(self.chats)):
            if self.chats[i][1] == Bridges.empty:
                self.chats[i] = (
                    self.chats[i][0],
                    bridgeType,
                )  # = self.chats[i][1] = bridgeType
                self.sendMessage("This chat got connected", self.chats[i][0].id)
                return self.chats[i][0].id
        return -1

    def updateChat(self, chatId, title, photo):
        chat = self.getChatById(chatId)[0]

        self.bot.setChatTitle(chatId, title)
        self.bot.setChatPhoto(chatId, open(photo, "rb"))

        os.remove(photo)


if __name__ == "__main__":
    sttf = open("settings.txt").read()
    sttf = sttf.replace(" ", "").split("\n")
    stt = {}
    for s in sttf:
        if s == "":
            continue
        [key, value] = s.split("=")
        stt[key] = value

    bridge = Bridge(stt["tg-bot-token"], stt["fb-email"], stt["fb-passwd"])
