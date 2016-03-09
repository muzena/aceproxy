'''
Simple Client Counter for VLC VLM
'''
import threading
import logging
import time
import aceclient
from aceconfig import AceConfig

class ClientCounter(object):

    def __init__(self):
        self.lock = threading.RLock()
        self.clients = dict()
        self.idleace = None
        self.total = 0
        threading.Timer(60.0, self.checkIdle).start()
    
    def getClients(self, cid):
        with self.lock:
            return self.clients.get(cid)

    def add(self, cid, client):
        with self.lock:
            clients = self.clients.get(cid)
            
            if clients:
                client.ace = clients[0].ace
                with client.ace._lock:
                    client.queue.extend(client.ace._streamReaderQueue)
                clients.append(client)
            else:
                if self.idleace:
                    client.ace = self.idleace
                    self.idleace = None
                else:
                    client.ace = self.createAce()
                
                clients = [client]
                self.clients[cid] = clients
                    
            self.total += 1
            return len(clients)

    def delete(self, cid, client):
        with self.lock:
            if not self.clients.has_key(cid):
                return
            
            clients = self.clients[cid]
            
            if len(clients) > 1:
                clients.remove(client)
            else:
                del self.clients[cid]
                clients[0].ace.closeStreamReader()
                
                if self.idleace:
                    client.ace.destroy()
                else:
                    client.ace.STOP()
                    self.idleace = client.ace
                    self.idleace._idleSince = time.time()

            client.closeConnection()
            self.total -= 1

    def deleteAll(self, cid):
        with self.lock:
            if not self.clients.has_key(cid):
                return
            
            clients = self.clients[cid]
            del self.clients[cid]
            self.total -= len(clients)
            clients[0].ace.closeStreamReader()
            
            for c in clients:
                c.closeConnection()
            
            if self.idleace:
                clients[0].ace.destroy()
            else:
                clients[0].ace.STOP()
                self.idleace = clients[0].ace
                self.idleace._idleSince = time.time()

    def createAce(self):
        logger = logging.getLogger('createAce')
        ace = aceclient.AceClient(
                AceConfig.acehost, AceConfig.aceport, connect_timeout=AceConfig.aceconntimeout,
                result_timeout=AceConfig.aceresulttimeout)
        logger.debug("AceClient created")
        ace.aceInit(
                gender=AceConfig.acesex, age=AceConfig.aceage,
                product_key=AceConfig.acekey, pause_delay=AceConfig.videopausedelay,
                seekback=AceConfig.videoseekback)
        logger.debug("AceClient inited")
        return ace
    
    def checkIdle(self):
        with self.lock:
            ace = self.idleace
            if ace and (ace._idleSince + 5.0 >= time.time()):
                self.idleace = None
                ace.destroy()
        
        threading.Timer(60.0, self.checkIdle).start()
