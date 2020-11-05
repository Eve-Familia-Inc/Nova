import asyncio
import sys
import ssl

from Lilith.Server.Http import HttpServer
from R.Web.defines import status_codes, mime
from R.Web.Functions import *
from R.Web.WebSockFunc import *

##### DEFAULTS #####
HOST = "localhost"
PORT = 80
SSL_CONTEXT = None
####################


class HttpInitialize(HttpServer):
    async def __new__(cls, *a, **kw):
        instance = await super().__new__(cls)
        await instance.__init__(*a, **kw)
        return instance

    async def __init__(self, host=HOST, port=PORT, ssl_context=SSL_CONTEXT):
        await super().__init__(host, port, ssl_context)
        self.StatusCodes = status_codes
        self.MIME = mime
        self.RootDirectory = (sys.argv[1]).encode("utf-8")
        self.MessageDirectory = (sys.argv[1]).encode("utf-8")
        self.PostFunctions = PostFunctions
        self.GePtFunctions = GePtFunctions
        self.WebSocketFunctions = WebSocketFunctions

    async def Get(self, connection, Request, ReplyHeader):
        print("GET", Request[b"path"])
        await super().Get(connection, Request, ReplyHeader)

    async def Post(self, connection, Request, ReplyHeader):
        print("POST", Request[b"path"], Request[b"content"])
        await super().Post(connection, Request, ReplyHeader)


async def start():
    print(sys.argv)
    HOST = sys.argv[2]
    PORT = int(sys.argv[3])
    CTX = None
    if(len(sys.argv) == 6):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ctx.load_cert_chain(sys.argv[4], sys.argv[5])
        ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        CTX = ctx
    print(HOST, PORT, CTX)
    http_server = await HttpInitialize(host=HOST, port=PORT, ssl_context=CTX)
    http_server.RootDirectory = (sys.argv[1]).encode("utf-8")
    http_server.MessageDirectory = (sys.argv[1]).encode("utf-8")
    await http_server.Start()

if(len(sys.argv) < 4):
    print("[usage] python3 StartHttp.py ./PathToRootDir <bind ip address> <bind port> <SSL:cert.pem> <SSL:key.pem>")
    exit()

asyncio.run(start())
