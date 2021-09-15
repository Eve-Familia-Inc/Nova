def parse(data, bytes_format):
    R = []
    pointer = 0
    for p in bytes_format:
        R.append(data[pointer:pointer+p])
        pointer += p
    bottom = data[pointer:]
    if(len(bottom) != 0):
        R.append(bottom)
    return R


def parseq(data, size):
    return parse(data, [size for _ in int(len(data)/size)])
