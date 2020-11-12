import asyncio
import ssl
import glob

from Nova.Server.Http import Server
from Nova.Server.Defines import status_codes, mime


class Service(Server):
    def __init__(self, host, port, root_path):
        super().__init__(host=host, port=port)
        self.__print_msg__()
        self.RootPath = root_path
        self.StatusCodes = status_codes
        self.MIME = mime
        self.OnMemoryFiles = {}
        self.SetFilesOnMemory(root_path)

    def __print_msg__(self):
        print("""                                                      
    b.             8     ,o888888o.  `8.`888b           ,8' .8.          
    888o.          8  . 8888     `88. `8.`888b         ,8' .888.         
    Y88888o.       8 ,8 8888       `8b `8.`888b       ,8' :88888.        
    .`Y888888o.    8 88 8888        `8b `8.`888b     ,8' . `88888.       
    8o. `Y888888o. 8 88 8888         88  `8.`888b   ,8' .8. `88888.      
    8`Y8o. `Y88888o8 88 8888         88   `8.`888b ,8' .8`8. `88888.     
    8   `Y8o. `Y8888 88 8888        ,8P    `8.`888b8' .8' `8. `88888.    
    8      `Y8o. `Y8 `8 8888       ,8P      `8.`888' .8'   `8. `88888.   
    8         `Y8o.`  ` 8888     ,88'        `8.`8' .888888888. `88888.  
    8            `Yo     `8888888P'           `8.` .8'       `8. `88888. 

                                                        © Eve.Familia, Inc. 2020""")

    def SetFilesOnMemory(self, path):
        path = (path + "/**").replace("//", "/")
        l = glob.glob(path, recursive=True)
        root_dir = l[0]
        print("Root Directory:", root_dir)
        tmp = [a.replace(root_dir, '/') for a in l]
        for p in tmp:
            if("." in p):
                extension = p.split(".")[-1]
                if(extension in self.MIME):
                    f = open(root_dir + p[1:], "rb")
                    data = f.read()
                    f.close()
                    self.OnMemoryFiles[p] = {
                        "MIME": self.MIME[extension],
                        "DATA": data
                    }
                    print("Stored File:", root_dir + p[1:])

    def EnableSSL(self, domain_cert, private_key):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ctx.load_cert_chain(domain_cert, private_key)
        ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        self._SSL_Context = ctx

    def Start(self):
        asyncio.run(self.__Start__())
