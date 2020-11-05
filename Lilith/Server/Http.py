import asyncio
import hashlib
import base64

from Lilith.Server.Handler.Http import HttpHandler


class HttpServer(HttpHandler):
    async def __new__(cls, *a, **kw):
        instance = await super().__new__(cls)
        await instance.__init__(*a, **kw)
        return instance

    async def __init__(self, host, port, ssl_context):
        await super().__init__(host, port, ssl_context)
        self.RootDirectory = b"./"
        self.MessageDirectory = b"./"
        self.DefaultFile = b"/index.html"
        self.PostFunctions = {}
        self.GePtFunctions = {}
        self.WebSocketFunctions = {}
        self.StatusCodes = {}
        self.MIME = {}
        self._Header = (
            b"HTTP/1.1 %b\r\n" +
            b"Server: %b\r\n" +
            b"Accept-Ranges: %b\r\n" +
            b"Content-Length: %i\r\n" +
            b"Connection: %b\r\n" +
            b"Keep-Alive: %b\r\n" +
            b"Content-Type: %b\r\n"
        )

    def NewHeader(self):
        return({
            b"Status": 0,
            b"Server": b"AmnesiA-Lilith/4.0",
            b"Accept-Ranges": b"bytes",
            b"Content-Length": 0,
            b"Connection": b"keep-alive",
            b"Keep-Alive": b"timeout=30, max=100",
            b"Content-Type": b"",
            b"Additional": [],
            b"ReplyContent": b""
        })

    async def Reply(self, connection, header):
        _ReplyBuffer = self._Header % (
            self.StatusCodes[header[b"Status"]],
            header[b"Server"],
            header[b"Accept-Ranges"],
            len(header[b"ReplyContent"]),
            header[b"Connection"],
            header[b"Keep-Alive"],
            header[b"Content-Type"])

        for a in header[b"Additional"]:
            _ReplyBuffer += a + b"\r\n"

        await connection.Send(_ReplyBuffer + b"\r\n" + header[b"ReplyContent"])

    async def Get(self, connection, Request, ReplyHeader):
        if(Request[b"path"].find(b"?") != -1):
            data = Request[b"path"].split(b"?")
            Request[b"path"] = data[0]
            Request.update({b"content": data[1]})
            try:
                await self.GePtFunctions[Request[b"path"]](self, connection, Request, ReplyHeader)
            except KeyError as error:
                try:
                    f = open(self.MessageDirectory + b"/404.html", "rb")
                    ReplyHeader[b"ReplyContent"] = f.read()
                    f.close()
                    ReplyHeader[b"Content-Type"] = b"text/plain"
                    ReplyHeader[b"Status"] = 404
                except:
                    ReplyHeader[
                        b"ReplyContent"] = b"ContentNotFound & 404 Message Not Found :("
                    ReplyHeader[b"Content-Type"] = b"text/plain"
                    ReplyHeader[b"Status"] = 404
                await self.Reply(connection, ReplyHeader)
        else:
            try:
                if(Request[b"path"] == b"/"):
                    Request[b"path"] = self.DefaultFile
                f = open(self.RootDirectory + Request[b"path"], "rb")
                ReplyHeader[b"ReplyContent"] = f.read()
                f.close()
                try:
                    ReplyHeader[b"Content-Type"] = self.MIME[
                        Request[b"path"][Request[b"path"].find(b".")+1:]
                    ]
                    ReplyHeader[b"Status"] = 200
                except:
                    f = open(self.MessageDirectory + b"/415.html", "rb")
                    ReplyHeader[b"ReplyContent"] = f.read()
                    f.close()
                    ReplyHeader[b"Content-Type"] = b"text/html"
                    ReplyHeader[b"Status"] = 415
            except:
                try:
                    f = open(self.MessageDirectory + b"/404.html", "rb")
                    ReplyHeader[b"ReplyContent"] = f.read()
                    f.close()
                    ReplyHeader[b"Content-Type"] = b"text/plain"
                    ReplyHeader[b"Status"] = 404
                except:
                    ReplyHeader[
                        b"ReplyContent"] = b"ContentNotFound & 404 Message Not Found :("
                    ReplyHeader[b"Content-Type"] = b"text/plain"
                    ReplyHeader[b"Status"] = 404
            await self.Reply(connection, ReplyHeader)

    async def Post(self, connection, Request, ReplyHeader):
        try:
            await self.PostFunctions[Request[b"path"]](self, connection, Request, ReplyHeader)
        except KeyError as error:
            try:
                f = open(self.MessageDirectory + b"/404.html", "rb")
                ReplyHeader[b"ReplyContent"] = f.read()
                f.close()
                ReplyHeader[b"Content-Type"] = b"text/plain"
                ReplyHeader[b"Status"] = 404
            except:
                ReplyHeader[b"ReplyContent"] = b"ContentNotFound & 404 Message Not Found :("
                ReplyHeader[b"Content-Type"] = b"text/plain"
                ReplyHeader[b"Status"] = 404
            await self.Reply(connection, ReplyHeader)

    async def WebSocket(self, connection, Request, ReplyHeader):
        print("Handling WebSocket.")
        print(Request[b"Sec-WebSocket-Version"])
        print(Request[b"Sec-WebSocket-Key"])
        m = hashlib.sha1()
        m.update(Request[b"Sec-WebSocket-Key"])
        m.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
        await connection.Send(
            b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
            + base64.b64encode(m.digest())
            + b"\r\n\r\n"
        )
        try:
            await self.WebSocketFunctions[Request[b"path"]](self, connection, Request, ReplyHeader)
        except:
            await connection.Close()
