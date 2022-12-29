import asyncio
import ssl
import nova.util.parser


class AsyncStream():
    def __init__(self, reader, writer):
        self._Reader = reader
        self._Writer = writer
        self._Recvsize = 1024 * 4
        self._Timeout = 60.0 * 15
    ### Send ###

    async def Send(self, b):
        self._Writer.write(b)
        await asyncio.wait_for(self._Writer.drain(), timeout=self._Timeout)

    async def Recv(self, i=0, timeout=0):
        R = b""
        if(i == 0):
            i = self._Recvsize
        if(timeout == 0):
            timeout = self._Timeout
        R = await asyncio.wait_for(self._Reader.read(i), timeout=timeout)
        return(R)

    async def Close(self):
        self._Writer.close()

    def isOnline(self):
        return(not self._Writer.is_closing())


class AsyncManualSslStream(AsyncStream):
    def __init__(self, reader, writer):
        super().__init__(reader, writer)
        self.serverSide = True
        self.serverName = None
        self.ALPN = None
        self.SslContext = None

        self.isTryingHandshake = False

        self._tls_in_buff = ssl.MemoryBIO()
        self._tls_out_buff = ssl.MemoryBIO()
        self._tls_Readsize = 8
        self._client_hello_buf = None

    async def Send(self, b):
        self._tls_obj.write(b)
        self._Writer.write(self._tls_out_buff.read())
        await asyncio.wait_for(self._Writer.drain(), timeout=self._Timeout)

    async def Recv(self, i=0, timeout=0):
        R = b""
        if(i == 0):
            i = self._Recvsize
        if(timeout == 0):
            timeout = self._Timeout
        BUF = await asyncio.wait_for(self._Reader.read(i), timeout=timeout)
        self._tls_in_buff.write(BUF)
        while(True):
            try:
                R += self._tls_obj.read(self._tls_Readsize)
            except:
                break
        return(R)

    def ReadserverName(self, ex):
        R = None
        exTypes = ex[0::3]
        exLength = ex[1::3]
        exBuf = ex[2::3]
        for i in range(len(exTypes)):
            if(exTypes[i] == b"\x00\x00"):
                return nova.util.parser.parse(
                    exBuf[i],
                    (2, 1, 2, "b-1")
                )[-2].decode("utf-8")
        return R

    def ReadALPN(self, ex):
        R = []
        exTypes = ex[0::3]
        exLength = ex[1::3]
        exBuf = ex[2::3]
        for i in range(len(exTypes)):
            if(exTypes[i] == b"\x00\x10"):
                tmp = nova.util.parser.parse(
                    exBuf[i][2:],
                    (1, "b-1")
                )
                R.append(
                    tmp[1].decode("utf-8")
                )
                while(tmp[-1] != None):
                    tmp = nova.util.parser.parse(
                        tmp[-1],
                        (1, "b-1")
                    )
                    R.append(
                        tmp[1].decode("utf-8")
                    )
        return R

    async def ParseClientHello(self):
        R = {}
        self._client_hello_buf = await super().Recv()
        if(self._client_hello_buf[0] != 22):
            self.isTryingHandshake = False
            return None
        self.isTryingHandshake = True
        R["Parsed"] = nova.util.parser.parse(
            self._client_hello_buf,
            (
                1, 2, 2,
                1, 3, 2, 32, 1, "b-1", 2, "b-1", 1, "b-1",
                2)
        )
        extensions = [R["Parsed"][-1]]
        while(extensions[-1] != None):
            extensions = extensions[:-1] + nova.util.parser.parse(
                extensions[-1],
                (2, 2, "b-1")
            )
        R["Parsed"][-1] = extensions[:-1]
        return(R)

    async def ReadClientHello(self):
        R = await self.ParseClientHello()
        if(self.isTryingHandshake):
            self.serverName = self.ReadserverName(R["Parsed"][-1])
            self.ALPN = self.ReadALPN(R["Parsed"][-1])

    async def Handshake(self):
        self._tls_obj = self.SslContext.wrap_bio(
            self._tls_in_buff, self._tls_out_buff, server_side=self.serverSide)
        if(self.serverSide):
            # Recv Client Hello
            self._tls_in_buff.write(self._client_hello_buf)
        # || TLS Handshake
        try:
            self._tls_obj.do_handshake()
        except ssl.SSLWantReadError:
            if(self.serverSide):
                server_hello = self._tls_out_buff.read()
                # serverHello
                await super().Send(server_hello)
                # Client Certificate
                client_cert = await super().Recv()
                self._tls_in_buff.write(client_cert)
                self._tls_obj.do_handshake()
                # Change Cipher
                change_cipher_finished = self._tls_out_buff.read()
                await super().Send(change_cipher_finished)
            else:
                # Client Hello
                await super().Send(self._tls_out_buff.read())
                # server Hello
                self._tls_in_buff.write(await super().Recv())
                try:
                    self._tls_obj.do_handshake()
                except ssl.SSLWantReadError:
                    await super().Send(self._tls_out_buff.read())
                    self._tls_in_buff.write(await super().Recv())
        # -- TLS Handshake
