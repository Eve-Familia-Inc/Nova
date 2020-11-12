import asyncio

from Nova.Core.Stream import AsyncStream


class AsyncTcp():
    def __init__(self, host, port):
        self._Host = host
        self._Port = port
        self._SSL_Context = None

    # Need Override
    async def Handler():
        pass

    async def __InitHandler__(self, reader, writer):
        # Connection MUST be argment
        connection = await AsyncStream(reader, writer, ssl_context=self._SSL_Context)
        await self.Handler(connection)

    async def __InitHandlerSSL__(self, reader, writer):
        # Connection MUST be argment
        connection = await AsyncStream(reader, writer)
        await self.Handler(connection)

    async def __Start__(self):
        if(self._SSL_Context is None):
            server = await asyncio.start_server(self.__InitHandler__, self._Host, self._Port)
            async with server:
                await server.serve_forever()
        else:
            server = await asyncio.start_server(self.__InitHandlerSSL__, self._Host, self._Port, ssl=self._SSL_Context)
            async with server:
                await server.serve_forever()
