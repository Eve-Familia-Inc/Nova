from Nova.Core.ServerBase import AsyncTcp
import asyncio
import hashlib
import base64

from Nova.Server.Defines import status_codes


class Server(AsyncTcp):
    def __init__(self, host, port):
        super().__init__(host=host, port=port)
        self.DefaultFile = "/index.html"
        self.PostFunctions = {}
        self.GetFunctions = {}
        self.WebSocketFunctions = {}
        self.StatusCodes = {}
        self.MIME = {}
        self.OnMemoryFiles = {}
        self._Header = (
            b"HTTP/1.1 %b\r\n" +
            b"Server: %b\r\n" +
            b"Accept-Ranges: %b\r\n" +
            b"Content-Length: %i\r\n" +
            b"Connection: %b\r\n" +
            b"Keep-Alive: %b\r\n" +
            b"Content-Type: %b\r\n"
        )
        self.ServerFunctions = {
            b"GET": self.Get,
            b"POST": self.Post,
            b"WebSocket": self.WebSocket
        }
        self.ContentLengthLimit = 1024 * 1024 * 3

    def NewHeader(self):
        return({
            "Status": 0,
            "Server": b"Nova/1.0",
            "Accept-Ranges": b"bytes",
            "Content-Length": 0,
            "Connection": b"keep-alive",
            "Keep-Alive": b"timeout=30, max=100",
            "Content-Type": b"",
            "Additional": [],
            "ReplyContent": b""
        })

    async def Reply(self, connection, header):
        _ReplyBuffer = self._Header % (
            self.StatusCodes[header["Status"]],
            header["Server"],
            header["Accept-Ranges"],
            len(header["ReplyContent"]),
            header["Connection"],
            header["Keep-Alive"],
            header["Content-Type"])

        for a in header["Additional"]:
            _ReplyBuffer += a + b"\r\n"

        await connection.Send(_ReplyBuffer + b"\r\n" + header["ReplyContent"])

    async def ReplyJustCode(self, code, connection, Request, ReplyHeader):
        ReplyHeader["ReplyContent"] = status_codes[code]
        ReplyHeader["Content-Type"] = b"text/html"
        ReplyHeader["Status"] = code
        await self.Reply(connection, ReplyHeader)

    async def WebSockRecv(self, connection):
        buf = await connection.Recv()
        if(len(buf) == 0 or buf[0] == 0x88):
            return(False)
        opcode = (buf[0] & 0x0f)
        is_Masked = (buf[1] >> 7)
        Payload_len = (buf[1] & 0x7f)
        Ptr = 2
        Masking_key = b""
        Payload_data = b""
        if(Payload_len == 126):
            # Extended payload length
            Payload_len = int.from_bytes(buf[2:4], "big")
            Ptr = 4
        elif(Payload_len == 127):
            # Extended payload length
            Payload_len = int.from_bytes(buf[2:10], "big")
            Ptr = 10
        Payload_data = buf[Ptr+4:]
        if(is_Masked):
            # Resulut[ i ] ＝ buf[ i ] xor key [ i mod 4 ]
            Masking_key = buf[Ptr:Ptr+4]
            Result = b""
            for i in range(Payload_len):
                Result += (Payload_data[i] ^
                           Masking_key[i % 4]).to_bytes(1, 'big')
            Payload_data = Result
        return(opcode, Payload_data)

    async def BuildWebSockFrame(self, opcode, payload):
        payload_len = len(payload)
        R = (0x80 + opcode).to_bytes(1, "big")
        if(payload_len <= 125):
            R += payload_len.to_bytes(1, 'big')
        elif(payload_len <= 65535):
            R += b"\x7e" + payload_len.to_bytes(2, 'big')
        elif(65535 < payload_len and payload_len <= 18446744073709551615):
            R += b"\x7f" + payload_len.to_bytes(8, 'big')
        R += payload
        return(R)

    async def GetFunctionHandler(self, connection, Request, ReplyHeader):
        try:
            await self.GetFunctions[Request["path"].decode("utf-8")](self, connection, Request, ReplyHeader)
        except:
            await self.ReplyJustCode(500, connection, Request, ReplyHeader)

    async def PostFunctionHandler(self, connection, Request, ReplyHeader):
        try:
            await self.PostFunctions[Request["path"].decode("utf-8")](self, connection, Request, ReplyHeader)
        except:
            await self.ReplyJustCode(500, connection, Request, ReplyHeader)

    async def WebSocketFunctionHandler(self, connection, Request, ReplyHeader):
        try:
            await self.WebSocketFunctions[Request["path"]](self, connection, Request, ReplyHeader)
        except:
            await connection.Close()

    async def Get(self, connection, Request, ReplyHeader):
        ReqPath = Request["path"].decode("utf-8")
        if(ReqPath == "/"):
            ReqPath = self.DefaultFile
        if(ReqPath in self.OnMemoryFiles):
            ReplyHeader["ReplyContent"] = self.OnMemoryFiles[ReqPath]["DATA"]
            ReplyHeader["Content-Type"] = self.OnMemoryFiles[ReqPath]["MIME"]
            ReplyHeader["Status"] = 200
            await self.Reply(connection, ReplyHeader)
        elif(ReqPath in self.GetFunctions):
            Request.update({"content": b""})
            await self.GetFunctionHandler(connection, Request, ReplyHeader)
        elif("?" in ReqPath):
            data = Request["path"].split(b"?")
            Request["path"] = data[0]
            Request.update({"content": data[1]})
            if(Request["path"].decode("utf-8") in self.GetFunctions):
                await self.GetFunctionHandler(connection, Request, ReplyHeader)
            else:
                await self.ReplyJustCode(404, connection, Request, ReplyHeader)
        else:
            await self.ReplyJustCode(404, connection, Request, ReplyHeader)

    async def Post(self, connection, Request, ReplyHeader):
        ReqPath = Request["path"].decode("utf-8")
        if(ReqPath in self.PostFunctions):
            await self.PostFunctionHandler(connection, Request, ReplyHeader)
        else:
            await self.ReplyJustCode(404, connection, Request, ReplyHeader)

    async def WebSocket(self, connection, Request, ReplyHeader):
        m = hashlib.sha1()
        m.update(Request["Sec-WebSocket-Key"])
        m.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
        await connection.Send(
            b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
            + base64.b64encode(m.digest())
            + b"\r\n\r\n"
        )
        await self.WebSocketFunctionHandler[Request["path"]](connection, Request, ReplyHeader)

    async def Handler(self, connection):
        try:
            h = self.NewHeader()
            Request = {}
            while(connection.OnLine):
                buf = await connection.Recv()
                if(len(buf) == 0):
                    await connection.Close()
                    return
                while(buf.find(b"\r\n\r\n") == -1):
                    buf += await connection.Recv()
                Request = {}
                body_pointer = buf.find(b"\r\n\r\n")
                headers = buf[:body_pointer].split(b"\r\n")
                request = headers[0].split(b" ")
                Request.update({"method": request[0]})
                Request.update({"path": request[1]})
                Request.update({"version": request[2]})
                try:
                    for param in headers[1:]:
                        p = param.split(b": ")
                        Request.update({p[0].decode("utf-8"): p[1]})
                except:
                    pass
                if("Upgrade" in Request and Request["Upgrade"] == b"websocket"):
                    Request["method"] = b"WebSocket"
                elif(Request["method"] == b"GET"):
                    pass
                elif(Request["method"] == b"POST"):
                    body = buf[body_pointer+4:]
                    if(self.ContentLengthLimit < int(Request["Content-Length"])):
                        await connection.Close()
                        return
                    while(len(body) < int(Request["Content-Length"])):
                        body += await connection.Recv()
                    Request.update({"content": body})
                else:
                    await connection.Close()
                    return
                await self.ServerFunctions[Request["method"]](connection, Request, h)
        except:
            await connection.Close()
