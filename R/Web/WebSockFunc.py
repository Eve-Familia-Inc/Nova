# 日本語RFC
# https://triple-underscore.github.io/RFC6455-ja.html


async def ws_recv(connection):
    buf = await connection.Recv()
    # print("Recv", buf)
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
        # print("Extended", Extended_Payload_len)
        Ptr = 4
    elif(Payload_len == 127):
        # Extended payload length
        Payload_len = int.from_bytes(buf[2:10], "big")
        # print("Extended", Extended_Payload_len)
        Ptr = 10
    Payload_data = buf[Ptr+4:]
    # print("opcode", opcode)
    # print("Payload_len", Payload_len)
    # print("Payload_data", Payload_data)
    if(is_Masked):
        # Resulut[ i ] ＝ buf[ i ] xor key [ i mod 4 ]
        Masking_key = buf[Ptr:Ptr+4]
        Result = b""
        for i in range(Payload_len):
            Result += (Payload_data[i] ^
                       Masking_key[i % 4]).to_bytes(1, 'big')
        Payload_data = Result
    # print("Mask", Masking_key)
    # print("unMasked_data", Payload_data)
    return(opcode, Payload_data)


async def build_frame(opcode, payload):
    try:
        payload_len = len(payload)
        R = (0x80 + opcode).to_bytes(1, "big")
        print(R, payload_len)
        if(payload_len <= 125):
            R += payload_len.to_bytes(1, 'big')
        elif(payload_len <= 65535):
            R += b"\x7e" + payload_len.to_bytes(2, 'big')
        elif(65535 < payload_len and payload_len <= 18446744073709551615):
            R += b"\x7f" + payload_len.to_bytes(8, 'big')
        R += payload
        print(R)
        return(R)
    except:
        import traceback
        traceback.print_exc()


async def Debug(self, connection, Request, ReplyHeader):
    print("WebSocketTest")
    while(connection.OnLine):
        opcode, payload = await ws_recv(connection)
        print("payload:", payload)
        if(not payload):
            # print("WebSocket Connection Closed.")
            await connection.Close()
        R = b""
        if(opcode == 0x0):
            # Continuation Frame
            pass
        elif(opcode == 0x1):
            # Text Frame
            R = await build_frame(0x1, payload)
        elif(opcode == 0x2):
            # Binary Frame
            pass
        await connection.Send(R)

WebSocketFunctions = {
    b"/Debug.ws": Debug
}
