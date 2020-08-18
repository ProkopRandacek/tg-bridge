import logging, threading, requests
from fbchat import log, Client, Message, ThreadType
from telegram.update import Update as tgUpdate
from telegram.message import Message as tgMessage
from bridges import Bridges
from PIL import Image

client = None


def init(tgSendMessage, tgRequestChat, tgUpdateChat, nm, pw):
    global client

    client = Bot(nm, pw, logging_level=logging.ERROR)
    client.tgSendMessage = tgSendMessage
    client.tgRequestChat = tgRequestChat
    client.tgUpdateChat = tgUpdateChat

    clientThread = threading.Thread(target=client.listen)
    print("fb client starting")
    clientThread.start()


def sendMessage(text, tgChatId):
    global client
    print(text, " to ", client.tgIdToFbId(tgChatId))
    client.sendMessage(text, client.tgIdToFbId(tgChatId))


class Chat:
    id = 0
    photo = ""
    title = ""
    tgId = 0

    def __init__(self, id, tgChat):
        self.id = id
        self.tgId = tgChat


class Bot(Client):
    tgSendMessage = None
    tgRequestChat = None
    tgUpdateChat = None
    chats = []

    def onMessage(self, author_id, message_object, thread_id, thread_type, **kwargs):
        if thread_type == ThreadType.GROUP:
            return
        if message_object.text.startswith("ERROR:"):
            return
        if message_object.text == "fetching chat info":
            return

        self.markAsDelivered(thread_id, message_object.uid)
        self.markAsRead(thread_id)

        if thread_id not in self.getChatsIds():
            self.initChat(thread_id, message_object.text)
        else:
            if author_id == self.uid:
                return

            msgText = message_object.text
            tgChatId = self.getChatById(thread_id).tgId

            self.tgSendMessage(msgText, tgChatId)

    def sendMessage(self, text, chatId):
        self.send(Message(text=text), thread_id=chatId, thread_type=ThreadType.USER)

    def getChatsIds(self):
        ids = []
        for c in self.chats:
            ids.append(c.id)
        return ids

    def getChatById(self, id):
        for c in self.chats:
            if c.id == id:
                return c

    def tgIdToFbId(self, tgId):
        for c in self.chats:
            if c.tgId == tgId:
                return c.id

    def fbIdToTgId(self, fbId):
        return self.getChatById(fbId).tgId

    def initChat(self, thread_id, message):
        self.sendMessage("fetching chat info", thread_id)

        thread = self.fetchThreadInfo(thread_id)
        thread = thread[thread_id]

        # users = client.searchForUsers(thread.first_name + " " + thread.last_name)
        # user = users[0]
        # print(user.url)
        # print(thread.url)
        # print(thread.photo)

        tgChatId = self.tgRequestChat(Bridges.fb)
        if tgChatId == -1:
            self.sendMessage(
                "ERROR: could not allocate chat in telegram.\nError was reported",
                thread_id,
            )
            self.tgSendMessage(
                f"I ran out of empty chats. {thread.name} messaged: {message}", None
            )
            return

        c = Chat(thread_id, tgChatId)
        c.title = thread.name
        c.photo = thread.photo

        self.chats.append(c)

        open("tmp.jpeg", "wb").write(requests.get(thread.photo).content)

        with Image.open("tmp.jpeg") as img:
            resz = img.resize((600, 600))
            resz.save("tmp.jpeg")

        self.tgUpdateChat(tgChatId, c.title, "tmp.jpeg")

        self.sendMessage(f"Chat registered.\ntgid {c.tgId}\nfbid {c.id}", thread_id)
