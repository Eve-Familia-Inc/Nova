import asyncio
import ssl
import traceback
from Nova.Core.Stream import AsyncStream, AsyncManualSslStream


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
                            "Host": ip address or domain name ,
                            "Port": port num,
                            "SSL": {
                                "ServerName": for checking host name,
                                "Context": ssl.SSLContext using for conect to Destination or if non TLS, just set None object,
                            }
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
        self.EntranceSslContextTree = {}
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
            self.EntranceSslContextTree[gate_map] = self.GateMapping[gate_map]["EntranceSslContext"]
        print(self.GateSettingTree)
        print(self.EntranceSslContextTree)
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
            traceback.print_exc()

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
            traceback.print_exc()

    async def __gateInitHandler__(self, reader, writer):
        # Connection MUST be argment
        entrance_connection = AsyncManualSslStream(reader, writer)
        await entrance_connection.ReadClientHello()
        server_name = entrance_connection.ServerName
        if(server_name is None):
            server_name = [
                x for x in self.EntranceSslContextTree][0]

        minimum_index = self.DestinationsWeight[server_name].index(
            min(self.DestinationsWeight[server_name]))
        destination = self.GateMapping[server_name]["Destinations"][minimum_index]

        destination_connection = None
        if(entrance_connection.isTryingHandshake):
            print(destination)
            if(destination["SSL"] is not None):
                # open ssl connection
                destination_context = ssl.create_default_context()
                print(entrance_connection.ALPN)
                if(len(entrance_connection.ALPN) > 0):
                    destination_context.set_alpn_protocols(
                        entrance_connection.ALPN
                    )
                reader, writer = await asyncio.open_connection(
                    destination["Host"],
                    destination["Port"],
                    ssl=destination_context,
                    server_hostname=destination["SSL"]["ServerName"])
                destination_connection = AsyncStream(reader, writer)
                # create entrance ssl context
                selected_alpn = destination_connection._Writer.get_extra_info(
                    "ssl_object"
                ).selected_alpn_protocol()
                entrance_ssl_context = self.EntranceSslContextTree[server_name]
                if(selected_alpn is not None):
                    entrance_ssl_context.set_alpn_protocols([selected_alpn])
                entrance_connection.SslContext = entrance_ssl_context
                # handshake entrance
                await entrance_connection.Handshake()
            else:
                entrance_ssl_context = self.EntranceSslContextTree[server_name]
                entrance_connection.SslContext = entrance_ssl_context
                # handshake entrance
                await entrance_connection.Handshake()
                reader, writer = await asyncio.open_connection(
                    destination["Host"],
                    destination["Port"])
                destination_connection = AsyncStream(reader, writer)
        else:
            if(destination["SSL"] is not None):
                destination_context = ssl.create_default_context()
                reader, writer = await asyncio.open_connection(
                    destination["Host"],
                    destination["Port"],
                    ssl=destination_context,
                    server_hostname=destination["SSL"]["ServerName"])
                destination_connection = AsyncStream(reader, writer)
            else:
                reader, writer = await asyncio.open_connection(
                    destination["Host"],
                    destination["Port"])
                destination_connection = AsyncStream(reader, writer)

            await destination_connection.Send(
                await self.onEntranceToDestination(
                    entrance_connection._client_hello_buf, entrance_connection, destination_connection)
            )
            entrance_connection = AsyncStream(
                entrance_connection._Reader, entrance_connection._Writer
            )

        self.DestinationsWeight[server_name][minimum_index] += 1
        await self.__openGate__(
            entrance_connection,
            destination_connection
        )
        self.DestinationsWeight[server_name][minimum_index] -= 1

    async def __start__(self):
        server = await asyncio.start_server(self.__gateInitHandler__, self.EntranceHost, self.EntrancePort)
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
