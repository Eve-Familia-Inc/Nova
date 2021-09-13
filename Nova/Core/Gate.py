import asyncio
from Nova.Core.Stream import AsyncStream


class Gate():
    def __init__(self,
                 entrance_ip, entrance_port, entrance_ssl_context,
                 destinations):
        """
        Parameters
        ----------
        entrance_ip : str
            proxy ip
        entrance_port : int
            proxy port
        entrance_ssl_context : sslContext | None
            proxy SSL context
        destinations : array [
                entrance_ip,
                entrance_port,
                entrance_ssl_context
                ]
            proxy destinations list
        """
        self.EntranceIp = entrance_ip
        self.EntrancePort = entrance_port
        self.EntranceSslContext = entrance_ssl_context
        self.Destinations = destinations
        self.DestinationsWeight = [0 for x in destinations]
        self.__print_msg__()

    async def onEntranceToDestination(self, buf, entrance_connection, destination_connection):
        return buf

    async def onDestinationToEntrance(self, buf, destination_connection, entrance_connection):
        return buf

    async def __openGate__(self, entrance_connection, destination_connection, destination_index):
        await asyncio.gather(
            self.__entranceHandler__(
                entrance_connection, destination_connection),
            self.__transportHandler__(
                destination_connection, entrance_connection)
        )

    async def __entranceHandler__(self, entrance_connection, destination_connection):
        try:
            while(entrance_connection.isOnline()):
                buf = await entrance_connection.Recv()
                event_handling_result_buf = await self.onEntranceToDestination(buf, entrance_connection, destination_connection)
                if(buf == b""):
                    await entrance_connection.Close()
                    await destination_connection.Close()
                    break
                await destination_connection.Send(event_handling_result_buf)
        except:
            await entrance_connection.Close()
            await destination_connection.Close()

    async def __transportHandler__(self, destination_connection, entrance_connection):
        try:
            while(destination_connection.isOnline()):
                buf = await destination_connection.Recv()
                event_handling_result_buf = await self.onDestinationToEntrance(buf, destination_connection, entrance_connection)
                if(buf == b""):
                    await entrance_connection.Close()
                    await destination_connection.Close()
                    break
                await entrance_connection.Send(event_handling_result_buf)
        except:
            await entrance_connection.Close()
            await destination_connection.Close()

    async def __proxyHandler__(self, entrance_connection):
        destination_connection, destination_index = await self.__openDestination__()
        await self.__openGate__(
            entrance_connection,
            destination_connection,
            destination_index
        )
        self.DestinationsWeight[destination_index] -= 1

    async def __openDestination__(self):
        minimum_index = self.DestinationsWeight.index(
            min(self.DestinationsWeight))
        reader, writer = await asyncio.open_connection(
            self.Destinations[minimum_index][0],
            self.Destinations[minimum_index][1],
            ssl=self.Destinations[minimum_index][2])
        self.DestinationsWeight[minimum_index] += 1

        return AsyncStream(reader, writer), minimum_index

    async def __proxyInitHandler__(self, reader, writer):
        # Connection MUST be argment
        connection = AsyncStream(reader, writer)
        await self.__proxyHandler__(connection)

    async def __start__(self):
        server = await asyncio.start_server(self.__proxyInitHandler__, self.EntranceIp, self.EntrancePort, ssl=self.EntranceSslContext)
        async with server:
            await server.serve_forever()

    def start(self):
        asyncio.run(self.__start__())

    def __print_msg__(self):
        print("""
        ,o888888o.          .8.    8888888 8888888888 8 8888888888   
       8888     `88.       .888.         8 8888       8 8888         
    ,8 8888       `8.     :88888.        8 8888       8 8888         
    88 8888              . `88888.       8 8888       8 8888         
    88 8888             .8. `88888.      8 8888       8 888888888888 
    88 8888            .8`8. `88888.     8 8888       8 8888         
    88 8888   8888888 .8' `8. `88888.    8 8888       8 8888         
    `8 8888       .8'.8'   `8. `88888.   8 8888       8 8888         
       8888     ,88'.888888888. `88888.  8 8888       8 8888         
        `8888888P' .8'       `8. `88888. 8 8888       8 888888888888 

                                                            © Eve.Familia, Inc. / LobeliaTechnologies™ 2021""")
