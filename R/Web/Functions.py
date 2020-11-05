async def PostTest(self, connection, Request, ReplyHeader):
    print(Request[b"content"])
    ReplyHeader[b"ReplyContent"] = Request[b"content"]
    ReplyHeader[b"Content-Type"] = b"text/html"
    ReplyHeader[b"Status"] = 200
    await self.Reply(connection, ReplyHeader)


async def GePtTest(self, connection, Request, ReplyHeader):
    print(Request[b"content"])
    ReplyHeader[b"ReplyContent"] = Request[b"content"]
    ReplyHeader[b"Content-Type"] = b"text/html"
    ReplyHeader[b"Status"] = 200
    await self.Reply(connection, ReplyHeader)

PostFunctions = {
    b"/PostTest.post": PostTest
}
GePtFunctions = {
    b"/GePtTest.gept": GePtTest
}
