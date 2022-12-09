import asyncio
import ssl
import glob

from Nova.Server.Http import Server
from Nova.Server.Defines import status_codes, mime
from Nova.Core.Gate import Gate, StableGate


class Service(Server):
    def __init__(self, host, port, root_path):
        super().__init__(host=host, port=port)
        self.RootPath = root_path
        self.StatusCodes = status_codes
        self.MIME = mime
        self.OnMemoryFiles = {}
        self.SetFilesOnMemory(root_path)

    def SetFilesOnMemory(self, path):
        path = (path + "/**").replace("//", "/")
        l = glob.glob(path, recursive=True)
        root_dir = l[0]
        print("Root Directory:", root_dir)
        tmp = [a.replace(root_dir, '/') for a in l]
        for p in tmp:
            if("." in p):
                p = p.replace("\\", "/")
                extension = p.split(".")[-1]
                if(extension in self.MIME):
                    f = open(root_dir + p[1:], "rb")
                    data = f.read()
                    f.close()
                    self.OnMemoryFiles[p] = {
                        "MIME": self.MIME[extension],
                        "DATA": data
                    }
                    print("Stored File:", p)

    def EnableSSL(self, domain_cert, private_key):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ctx.load_cert_chain(domain_cert, private_key)
        ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        self._SSL_Context = ctx

    def Start(self):
        asyncio.run(self.__Start__())
