__map__ = {
    "b": "big",
    "l": "little",
    "B": "big",
    "L": "little"
}


def parse(data, bytes_format):
    R = []
    pointer = 0
    for i in range(len(bytes_format)):
        p = bytes_format[i]
        if(type(p) is str):
            byteorder = __map__[p[0]]
            format_index = int(p[1:])
            length = int.from_bytes(R[format_index], byteorder)
            p = length
            if(p == 0):
                R.append(data[-1:0])
            else:
                R.append(data[pointer:pointer+p])
            pointer += p
        else:
            R.append(data[pointer:pointer+p])
            pointer += p
    bottom = data[pointer:]
    if(len(data) < pointer+1):
        R.append(None)
    else:
        R.append(bottom)
    return R


def parseq(data, size):
    return parse(data, [size for _ in range(int(len(data)/size))])
