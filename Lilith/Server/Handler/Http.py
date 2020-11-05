import asyncio

from Lilith.Server.Base import AsyncTcp


class HttpHandler(AsyncTcp):
    async def __new__(cls, *a, **kw):
        instance = await super().__new__(cls)
        await instance.__init__(*a, **kw)
        return instance

    async def __init__(self, host, port, ssl_context):
        await super().__init__(host, port, ssl_context)
        self.ServerFunctions = {
            b"GET": self.Get,
            b"POST": self.Post,
            b"WebSocket": self.WebSocket
        }
        self.ContentLengthLimit = 1024 * 1024

    # Need Override
    def NewHeader():
        pass

    # Need Override
    async def Get():
        pass

    # Need Override
    async def Post():
        pass

    # Need Override
    async def WebSocket():
        pass

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
                Request.update({b"method": request[0]})
                Request.update({b"path": request[1]})
                Request.update({b"version": request[2]})
                try:
                    for param in headers[1:]:
                        p = param.split(b": ")
                        Request.update({p[0]: p[1]})
                except:
                    pass
                if(b"Upgrade" in Request and Request[b"Upgrade"] == b"websocket"):
                    Request[b"method"] = b"WebSocket"
                elif(Request[b"method"] == b"GET"):
                    pass
                elif(Request[b"method"] == b"POST"):
                    body = buf[body_pointer+4:]
                    if(self.ContentLengthLimit < int(Request[b'Content-Length'])):
                        await connection.Close()
                        return
                    while(len(body) < int(Request[b'Content-Length'])):
                        body += await connection.Recv()
                    Request.update({b"content": body})
                else:
                    await connection.Close()
                    return
                await self.ServerFunctions[Request[b"method"]](connection, Request, h)
        except:
            import traceback
            traceback.print_exc()
            await connection.Close()
