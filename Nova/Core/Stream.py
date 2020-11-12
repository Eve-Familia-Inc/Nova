import asyncio
import ssl

########## DEFAULT DEFINES ##########
DEFAULT_TIMEOUT = 60.0 * 15
RECV_SIZE = 1024 * 4
TLS_READ_SIZE = 8
#####################################


class AsyncStream():
    async def __new__(cls, *a, **kw):
        instance = super().__new__(cls)
        await instance.__init__(*a, **kw)
        return instance

    async def __init__(self, reader, writer, ssl_context=None, debug=False, server_side=True):
        self.OnLine = True
        self._Reader = reader
        self._Writer = writer
        self._Recvsize = RECV_SIZE
        self._Timeout = DEFAULT_TIMEOUT
        self._SSL_Context = ssl_context
        self._tls_Readsize = TLS_READ_SIZE
        self._tls_in_buff = None
        self._tls_out_buff = None
        self._tls_obj = None
        self.PeerInfo = writer.get_extra_info("peername")
        self._Debug = debug
        self._server_side = server_side

        self._normal_send = self._non_ssl_send
        self._normal_recv = self._non_ssl_recv
        if(self._Debug):
            print("AsyncStream:__init__")
            print(
                "PeerInfo ip:", self.PeerInfo[0],
                "port:", self.PeerInfo[1]
            )
            self.Send = self._debug_send
            self.Recv = self._debug_recv
            self.Close = self._debug_close
        else:
            self.Send = self._normal_send
            self.Recv = self._normal_recv
            self.Close = self._normal_close

    ### Send ###

    async def Send():
        pass

    async def _normal_send():
        pass

    async def _debug_send(self, b):
        print("SEND...",
              "PeerInfo ip:", self.PeerInfo[0],
              "port:", self.PeerInfo[1], ">>>", b)
        await self._normal_send(b)

    async def _non_ssl_send(self, b):
        self._Writer.write(b)
        await asyncio.wait_for(self._Writer.drain(), timeout=self._Timeout)

    async def _ssl_send(self, b):
        self._tls_obj.write(b)
        self._Writer.write(self._tls_out_buff.read())
        await asyncio.wait_for(self._Writer.drain(), timeout=self._Timeout)

    ### Recv ###

    async def Recv(self):
        pass

    async def _normal_recv(self):
        pass

    async def _debug_recv(self, i=0):
        print("Receiving... PeerInfo ip:",
              self.PeerInfo[0], "port:", self.PeerInfo[1])
        R = b""
        R = await self._normal_recv(i)
        print("<<<",
              "PeerInfo ip:", self.PeerInfo[0],
              "port:", self.PeerInfo[1],
              self.PeerInfo[0], "...RECV", R)
        return(R)

    async def _non_ssl_recv(self, i=0, timeout=0):
        R = b""
        if(i == 0):
            i = self._Recvsize
        if(timeout == 0):
            timeout = self._Timeout
        R = await asyncio.wait_for(self._Reader.read(i), timeout=timeout)
        return(R)

    async def _ssl_recv(self, i=0, timeout=0):
        R = b""
        if(i == 0):
            i = self._Recvsize
        if(timeout == 0):
            timeout = self._Timeout
        self._tls_in_buff.write(await asyncio.wait_for(self._Reader.read(i), timeout=timeout))
        while(True):
            try:
                R += self._tls_obj.read(self._tls_Readsize)
            except:
                break
        return(R)

    async def StartTLS(self):
        self._normal_send = self._ssl_send
        self._normal_recv = self._ssl_recv
        if(self._Debug):
            self.Send = self._debug_send
            self.Recv = self._debug_recv
            self.Close = self._debug_close
        else:
            self.Send = self._normal_send
            self.Recv = self._normal_recv
            self.Close = self._normal_close

        self._tls_in_buff = ssl.MemoryBIO()
        self._tls_out_buff = ssl.MemoryBIO()
        self._tls_obj = self._SSL_Context.wrap_bio(
            self._tls_in_buff, self._tls_out_buff, server_side=self._server_side)
        if(self._server_side):
            # Recv Client Hello
            self._tls_in_buff.write(await asyncio.wait_for(self._Reader.read(self._Recvsize), timeout=self._Timeout))
        # || TLS Handshake
        try:
            self._tls_obj.do_handshake()
        except ssl.SSLWantReadError:
            if(self._server_side):
                self._Writer.write(self._tls_out_buff.read())
                await asyncio.wait_for(self._Writer.drain(), timeout=self._Timeout)
                self._tls_in_buff.write(await asyncio.wait_for(self._Reader.read(self._Recvsize), timeout=self._Timeout))
                self._tls_obj.do_handshake()
                self._Writer.write(self._tls_out_buff.read())
                await asyncio.wait_for(self._Writer.drain(), timeout=self._Timeout)
            else:
                # Client Hello
                self._Writer.write(self._tls_out_buff.read())
                await asyncio.wait_for(self._Writer.drain(), timeout=self._Timeout)
                # Server Hello
                self._tls_in_buff.write(await asyncio.wait_for(self._Reader.read(self._Recvsize), timeout=self._Timeout))
                try:
                    self._tls_obj.do_handshake()
                except ssl.SSLWantReadError:
                    self._Writer.write(self._tls_out_buff.read())
                    await asyncio.wait_for(self._Writer.drain(), timeout=self._Timeout)
                    self._tls_in_buff.write(await asyncio.wait_for(self._Reader.read(self._Recvsize), timeout=self._Timeout))
        # -- TLS Handshake

    async def Close():
        pass

    async def _debug_close(self):
        self._Writer.close()
        self.OnLine = False
        print(
            "[ CLOSED ] PeerInfo ip:", self.PeerInfo[0],
            "port:", self.PeerInfo[1]
        )

    async def _normal_close(self):
        self._Writer.close()
        self.OnLine = False
