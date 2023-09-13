import struct
from typing import BinaryIO

from utils.leb128 import Uleb128


class osuString:

    def __new__(cls, file_handle):
        string_header = file_handle.read(1)
        string = b""
        if string_header == b'\x0b':
            string_length = Uleb128(0).decode_from_stream(file_handle, 'read', 1)
            string = file_handle.read(string_length)

        return string.decode()

    @staticmethod
    def write_string(data: str, file_handle: BinaryIO):
        if len(data) > 0:
            file_handle.write(struct.pack("<B", 0x0b))
            strlen = b""
            value = len(data)
            while value != 0:
                byte = (value & 0x7F)
                value >>= 7
                if (value != 0):
                    byte |= 0x80
                strlen += struct.pack("<B", byte)
            write_data = b''
            write_data += strlen
            write_data += struct.pack("<" + str(len(data)) +
                                      "s", data.encode("utf-8"))
            file_handle.write(write_data)
        else:
            file_handle.write(struct.pack("<B", 0x00))


class ByteInt:
    def __new__(cls, value):
        return int.from_bytes(value, byteorder="little")


class ByteFloat:
    def __new__(cls, value):
        return struct.unpack('f', value)


class ByteDouble:

    def __new__(cls, value):
        return struct.unpack('d', value)


class IntDoublePairs:
    def __new__(cls, file_handle):
        num_pairs = ByteInt(file_handle.read(4))
        for _ in range(num_pairs):
            _ = file_handle.read(14)
