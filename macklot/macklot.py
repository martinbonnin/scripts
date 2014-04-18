#!/usr/bin/python
# -*- coding: koi8-r -*-
import sys
import xmpp
import twitter
import json
import random
import time
import re
import shlex
import excuse
from Queue import Queue
from threading import Thread, Lock
import signal
import pdb
import socket
import traceback
import collections
import errno
import HTMLParser
import thread

htmlparser = HTMLParser.HTMLParser()

class Manhole(object):

    def __init__(self):
        self.port = 2323
    
    def __manholeThread(self):
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                skt.bind(("127.0.0.1", self.port))
                break
            except Exception as e:
                if (e.errno == errno.EADDRINUSE):
                    #print("%d already in use"%self.port)
                    self.port += 1
                else:
                    raise e
        print("connect with telnet 127.0.0.1 %d to debug"% self.port)
        skt.listen(1)
        
        while (True):
            (clientsocket, address) = skt.accept()
            print("debugger connected")
            handle = clientsocket.makefile('rw')
            try:
                debugger = pdb.Pdb(stdin=handle, stdout=handle)
                debugger.set_trace()
            except:
                pass
            print("debugger disconnected");
        

    def start(self):
        t=Thread(target=self.__manholeThread)
        t.daemon=True;
        t.start()

class PersistentObject(collections.MutableMapping):
    '''an object that is backed by a json file
       it can be accessed either as a pure object or a dict'''
    #~ privateAttributes = ("store", "fileName")
    def __init__(self, fileName, default={}):
        self.fileName = fileName;
        try:
            fd = open(fileName, "rb");
            self.store = json.loads(fd.read());
        except:
            self.store = default
            self.save()

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value
    
    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def save(self):
        fd = open(self.fileName, "w");
        json.dump(self.store, fd);
        
class Twitter(object):
    OK = "ok"
    USER_UNKNOWN = "unknown"
    ALREADY_FOLLOWING = "following"
    NOT_FOLLOWING = "not_following"
    
    def __init__(self):
        credentials = PersistentObject("twitter.json")
        self.following = PersistentObject("following.json", self.getDefaultFollowing())
        
        self.threadId=0;
        self.lock=Lock();

        for a in ("api_key", "api_secret", "access_token", "access_token_secret"):
            if (not a in credentials):
                raise Exception("cannot find twitter api credentials")

        api = twitter.Api(credentials["api_key"], credentials["api_secret"],
                    credentials["access_token"], credentials["access_token_secret"], debugHTTP=True);
        self.api = api
        print("credentials:" + str(api.VerifyCredentials()));
        self.__startThread()
        
    def __checkThread(self, threadId):
        self.lock.acquire()
        if (self.threadId != threadId):
            # we have created a new thread, stop listening to this one...
            self.lock.release()
            print("thread #%d exit" % threadId)
            thread.exit()
        else:
            self.lock.release()
        

    def __thread(self, threadId):
        print("thread #%d enter" % threadId)
        while True:
            try:
                f=[self.following[key] for key in self.following]
                stream = self.api.GetStreamFilter(follow=f);
                while True:
                    m = stream.next();
                    print("thread #%d: %s"%(threadId, str(m)[:64]));
                    self.__checkThread(threadId)                   
                    #print("got message" + str(m));
                    self.onMessage(m)
            except SystemExit as e:
                # forward this exception
                print("Got SystemException")
                raise e
            except Exception as e:
                print("Got exception " + str(type(e)) + ": " + str(e));
                traceback.print_tb(sys.exc_info()[2])
                self.__checkThread(threadId)
                print("restart the stream filter")
                time.sleep(2)
            
    def __startThread(self):
        self.lock.acquire()
        self.threadId += 1
        self.lock.release()
        thread=Thread(target=self.__thread, args=[self.threadId,])
        thread.daemon=True;
        thread.start()
    
    def getDefaultFollowing(self):
        return {
                "SebastienChemin": "308982108", 
                "martinbonnin": "36179713",
                "Netgem": "51029845",
                "Videofutur": "171895044",
                "zelfir": "73072691",
                "gui17aume": "44731563",
                "macklot": "2337009242"
                }

    def getUserId(self, screen_name):
        '''cached version of __getUserId'''
        if (not screen_name in self.following):
            return None
        else:
            return self.following[screen_name]
    
    def __getUserId(self, screen_name):
        user = self.api.GetUser(screen_name=screen_name)
        if (not user):
            return None
        return str(user.GetId())
        
    def __action(self, screen_name, follow):
        uid = self.__getUserId(screen_name)
        if (uid == None):
            return Twitter.USER_UNKNOWN;

        if (follow):
            if (screen_name in self.following):
                return (Twitter.ALREADY_FOLLOWING, uid)
            self.following[screen_name] = uid            
        else:
            if (not screen_name in self.following):
                return (Twitter.NOT_FOLLOWING, uid)
            del self.following[screen_name]

        self.following.save();
        self.__startThread();
        return (Twitter.OK, uid)
    
    def follow(self, screen_name):
        return self.__action(screen_name, True)

    def unfollow(self, screen_name):
        return self.__action(screen_name, False)
    
    def getFollowing(self):
        return self.following
    
class Bot(object):
    def __init__(self):
        self.config = PersistentObject("bot.json", self.getDefaultConfig())
        for a in ("nick", "pass", "server", "domain", "room", "port"):
            if (not a in self.config):
                raise Exception("bad config, please check bot.json")
                print("param %s is missing, using default config" % a)
        self.queue=Queue(0)
        
    def sendGroupChat(self, text):
        self.conn.send(xmpp.Message(self.room, text, typ='groupchat'))
        
    def sendText(self, text):
        '''sends the given text to the room
           this uses a queue so that it can be called from a thread'''
        self.queue.put(text);     

    def handleCommand(self):
        print("this is the default handleCommand. Please override");

    def __messageCB(self, conn, mess):
        text=mess.getBody()
        user=mess.getFrom()
        if (not text):
            return
        match = re.match(self.config["nick"] + " *:", text)
        if (match and match.start() == 0):
            self.handleCommand(text[match.end():]);

    def run(self):
        config = self.config
        jid=xmpp.JID(config["nick"] + "@" + config["server"])
        user=jid.getNode()
        password=config["pass"]

        conn=xmpp.Client(config["domain"], debug=[])
        self.conn = conn;
        conres=conn.connect((config["server"], config["port"]))
        if not conres:
            print "Unable to connect to server %s!"%server
            sys.exit(1)
        #if conres != 'tls':
        #    print "Warning: unable to establish secure connection - TLS failed!"
        authres=conn.auth(user,password)
        if not authres:
            print "Unable to authorize on %s - check login/password."%server
            sys.exit(1)
        if authres != 'sasl':
            print "Warning: unable to perform SASL auth os %s. Old authentication method used!"%server

        p=xmpp.Presence(to=self.room + "/" + config["nick"])
        p.setTag('x',namespace=xmpp.NS_MUC)
        p.getTag('x').addChild('history',{'maxchars':'0','maxstanzas':'0'})
        conn.send(p)

        conn.RegisterHandler('message', self.__messageCB)
        conn.sendInitPresence()

        while (True):
            try:
                text = self.queue.get(False)
            except:
                text = None;

            if (text):
                self.sendGroupChat(text);

            conn.Process(1)

class Macklot(Bot):
    def __init__(self, debug):
        Bot.__init__(self)
        self.debug = debug

        if (self.debug):
            self.room = "test@conference.ahe1"
        else:
            self.room = self.config["room"]
        
        self.twitter = Twitter()
        self.twitter.onMessage = self.__onTwitterMessage

        manhole = Manhole()
        manhole.start()        

    def getDefaultConfig(self):
        config = {
            "nick": "macklot",
            "pass": "ssss",
            "server": "ahe2",
            "domain": "ahe1",
            "room": "enabledecoding@conference.ahe1",
            "port": 5222,
        }
        return config;

    def __serpentify(self, string):
        string = string.replace("s", "s".ljust(random.randint(0,3), "s"));
        string = string.replace("S", "S".ljust(random.randint(0,3), "s"));
        return string;

    def handleCommand(self, command):
        arg = shlex.split(command.encode("utf8"));
        if (len(arg) == 0):
            self.sendGroupChat(self.__serpentify("there is nothing there but emptiness"))
        elif (arg[0] == "excuse"):
            self.sendGroupChat(excuse.get())
        elif (arg[0] == "follow" or arg[0] == "unfollow"):
            if (len(arg) == 1):
                following = self.twitter.getFollowing()
                self.sendGroupChat("currently following: " + ", ".join(following.keys()))
                return
            
            if (arg[0] == "follow"):
                (ret, uid) = self.twitter.follow(arg[1])
            else:
                (ret, uid) = self.twitter.unfollow(arg[1])

            if (ret == Twitter.ALREADY_FOLLOWING):
                self.sendGroupChat("already following " + arg[1])
            elif (ret == Twitter.NOT_FOLLOWING):
                self.sendGroupChat("not following " + arg[1])
            elif (ret == Twitter.USER_UNKNOWN):
                self.sendGroupChat("don't know " + arg[1])
            elif (ret == Twitter.OK):
                self.sendGroupChat(arg[0] + "ing " + arg[1] + " (user_id = " + uid + ")");
        else:
            self.sendGroupChat("".ljust(random.randint(3,42), "s"))

    def __onTwitterMessage(self, m):
        if (not m):
            return;
        if (not "id" in m):
            return;
        if (not "text" in m):
            return;
        
        #print("sending tweet " + str(t));
        try:
            sender = m["user"]["screen_name"]
        except:
            print("ignore tweet without sender")
            return

        following = self.twitter.getFollowing()
        if (not sender in following):
            print("ignore tweet from someone we do not follow")
            return

        if (m["text"][0] == "@"):
            recipient = m["text"].split(" ")[0][1:]
            if (not recipient in following):
                print("ignore tweet to someone we do not follow")
                return

        retweet ="";
        text = ""

        status = m;
        if ("retweeted_status" in m):
            status = m["retweeted_status"];
            retweet = " (retweeted from "
            try:
                retweet += status["user"]["screen_name"]
            except:
                retweet += "????"
            retweet += ")"
        
        
        #display user
        if ("user" in m):
            text += "from " + sender + retweet + ": "
        
        #expand urls
        try:
            urls = status["entities"]["urls"]
        except:
            urls = []
        index = 0;
        for u in urls:
            text += htmlparser.unescape(status["text"][index:u["indices"][0]])
            text += u["expanded_url"]
            index = u["indices"][1]
        text += htmlparser.unescape(status["text"][index:])
        
        self.sendText(text)
        
if __name__ == '__main__':
    debug = False;
    if (len(sys.argv) > 1):
        if (sys.argv[1] == "--test"):
            debug = True;
        else:
            print("available options are:")
            print("   --test")
            sys.exit(2);

    macklot = Macklot(debug);
    macklot.run()
    

