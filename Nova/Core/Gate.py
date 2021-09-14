import asyncio
import ssl
from Nova.Core.Stream import AsyncStream


class Gate():
    def __init__(self, gate_setting_tree):
        """
        Parameters
        ----------
        {
            "EntranceHost": ip address or domain name,
            "EntrancePort": port num,
            "GateMapping": {
                mapping hostname, this is used for SNI callback. key of "EntranceSslContext": {
                    "EntranceSslContext": ssl.SSLContext of mapping hostname this cant be None object(must TLS),
                    "Destinations": [ this parameter is array because Gate has load balancing
                        {
                            "DestinationHost": ip address or domain name ,
                            "DestinationPort": port num,
                            "DestinationSslContext": ssl.SSLContext using for Destination or if non TLS, just set None object
                        }
                    ]
                }
            }
        }
        """
        self.GateSettingTree = gate_setting_tree
        self.EntranceHost = self.GateSettingTree["EntranceHost"]
        self.EntrancePort = self.GateSettingTree["EntrancePort"]
        self.GateMapping = self.GateSettingTree["GateMapping"]
        self.DestinationsWeight = {}
        for gate_map in self.GateMapping:
            """
                self.DestinationsWeight = {
                    GateMapping, mapping hostname: [0, ... Destinations[n]]
                }
            """
            self.DestinationsWeight[gate_map] = [
                0 for x in self.GateMapping[gate_map]['Destinations']
            ]
            setattr(
                self.GateMapping[gate_map]["EntranceSslContext"],
                "DomainName",
                gate_map
            )
        self.__print_msg__()

    async def onEntranceToDestination(self, B, entrance_connection, destination_connection):
        return B

    async def onDestinationToEntrance(self, B, destination_connection, entrance_connection):
        return B

    def __gateSniCallback__(self, ssl_sock, domain, ssl_ctx, as_callback=True):
        try:
            ssl_sock.context = self.GateMapping[domain]["EntranceSslContext"]
        except:
            raise ssl.ALERT_DESCRIPTION_HANDSHAKE_FAILURE
        return None

    async def __getDestinationName__(self, entrance_connection):
        return entrance_connection._Writer.get_extra_info("ssl_object").context.DomainName

    async def __openGate__(self, entrance_connection, destination_connection):
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
                if(event_handling_result_buf is not None):
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
                if(event_handling_result_buf is not None):
                    await entrance_connection.Send(event_handling_result_buf)
        except:
            await entrance_connection.Close()
            await destination_connection.Close()

    async def __proxyHandler__(self, entrance_connection):
        destination_name = await self.__getDestinationName__(entrance_connection)
        destination_connection, destination_index = await self.__openDestination__(
            destination_name
        )
        await self.__openGate__(
            entrance_connection,
            destination_connection
        )
        self.DestinationsWeight[destination_name][destination_index] -= 1

    async def __openDestination__(self, destination_name):
        minimum_index = self.DestinationsWeight[destination_name].index(
            min(self.DestinationsWeight[destination_name]))
        destination = self.GateMapping[destination_name]["Destinations"][minimum_index]
        reader = None
        writer = None
        if(destination["DestinationSslContext"] is None):
            reader, writer = await asyncio.open_connection(
                destination["DestinationHost"],
                destination["DestinationPort"])
        else:
            reader, writer = await asyncio.open_connection(
                destination["DestinationHost"],
                destination["DestinationPort"],
                ssl=destination["DestinationSslContext"],
                server_hostname=destination_name)
        self.DestinationsWeight[destination_name][minimum_index] += 1

        return AsyncStream(reader, writer), minimum_index

    async def __proxyInitHandler__(self, reader, writer):
        # Connection MUST be argment
        connection = AsyncStream(reader, writer)
        await self.__proxyHandler__(connection)

    async def __start__(self):
        entrance_ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH
        )
        entrance_ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        entrance_ssl_context.sni_callback = self.__gateSniCallback__
        server = await asyncio.start_server(self.__proxyInitHandler__, self.EntranceHost, self.EntrancePort, ssl=entrance_ssl_context)
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
