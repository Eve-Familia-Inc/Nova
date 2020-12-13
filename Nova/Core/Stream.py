import asyncio
import ssl

########## DEFAULT DEFINES ##########
DEFAULT_TIMEOUT = 60.0 * 15
RECV_SIZE = 1024 * 4
#####################################


class AsyncStream():
    def __init__(self, reader, writer, debug=False, server_side=True):
        self._Reader = reader
        self._Writer = writer
        self._Recvsize = RECV_SIZE
        self._Timeout = DEFAULT_TIMEOUT
        self._Debug = debug
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

    async def _normal_send(self, b):
        self._Writer.write(b)
        await asyncio.wait_for(self._Writer.drain(), timeout=self._Timeout)

    async def _debug_send(self, b):
        print("SEND...",
              "PeerInfo ip:", self.PeerInfo[0],
              "port:", self.PeerInfo[1], ">>>", b)
        await self._normal_send(b)

    ### Recv ###

    async def Recv(self):
        pass

    async def _normal_recv(self, i=0, timeout=0):
        R = b""
        if(i == 0):
            i = self._Recvsize
        if(timeout == 0):
            timeout = self._Timeout
        R = await asyncio.wait_for(self._Reader.read(i), timeout=timeout)
        return(R)

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

    async def Close():
        pass

    async def _debug_close(self):
        self._Writer.close()
        print(
            "[ CLOSED ] PeerInfo ip:", self.PeerInfo[0],
            "port:", self.PeerInfo[1]
        )

    async def _normal_close(self):
        self._Writer.close()
