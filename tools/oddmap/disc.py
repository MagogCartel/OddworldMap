"""Raw PS1 disc images and the LVL archives inside them: 2352-byte sector
reads, the ISO9660 directory, and the chunk container both games use."""
import struct

SECTOR_RAW = 2352
USER_OFF = 24

class Disc:
    def __init__(self, path):
        self.f = open(path, "rb")
        pvd = self.sector(16)
        assert pvd[1:6] == b"CD001", "not an ISO9660 raw image"
        root = pvd[156:156+34]
        lba = struct.unpack_from("<I", root, 2)[0]
        size = struct.unpack_from("<I", root, 10)[0]
        self.files = {}
        self._read_dir(lba, size, "")

    def sector(self, lba):
        self.f.seek(lba * SECTOR_RAW)
        return self.f.read(SECTOR_RAW)[USER_OFF:USER_OFF + 2048]

    def read(self, lba, size):
        out = bytearray()
        while len(out) < size:
            sec = self.sector(lba)
            if not sec:
                raise EOFError(f"read past end of image at LBA {lba}")
            out += sec
            lba += 1
        return bytes(out[:size])

    def _read_dir(self, lba, size, prefix):
        data = self.read(lba, size)
        pos = 0
        while pos < len(data):
            ln = data[pos]
            if ln == 0:
                pos = (pos // 2048 + 1) * 2048
                if pos >= len(data):
                    break
                continue
            e_lba = struct.unpack_from("<I", data, pos + 2)[0]
            e_size = struct.unpack_from("<I", data, pos + 10)[0]
            flags = data[pos + 25]
            name_len = data[pos + 32]
            name = data[pos + 33:pos + 33 + name_len].decode("ascii", "replace")
            if name not in ("\x00", "\x01"):
                if flags & 2:
                    self._read_dir(e_lba, e_size, prefix + name + "/")
                else:
                    self.files[name.split(";")[0].upper()] = (e_lba, e_size)
            pos += ln

class Lvl:
    def __init__(self, disc, name):
        self.disc = disc
        self.lba, self.size = disc.files[name.upper()]
        hdr = disc.sector(self.lba)
        num_files = struct.unpack_from("<I", hdr, 16)[0]
        if 32 + num_files * 24 > self.size:
            raise ValueError(f"{name}: directory does not fit the file, not a LVL archive")
        dir_bytes = disc.read(self.lba, 32 + num_files * 24)
        self.files = {}
        for i in range(num_files):
            off = 32 + i * 24
            nm = dir_bytes[off:off+12].split(b"\0")[0].decode("ascii", "replace")
            start_sec, num_sec, fsize = struct.unpack_from("<iii", dir_bytes, off + 12)
            self.files[nm] = (start_sec, fsize)

    def read(self, name):
        start_sec, fsize = self.files[name]
        return self.disc.read(self.lba + start_sec, fsize)

def parse_chunks(data):
    chunks = {}
    pos = 0
    while pos + 16 <= len(data):
        size, ref, flags, typ, rid = struct.unpack_from("<IHHII", data, pos)
        tag = struct.pack("<I", typ).decode("latin1")
        if tag == "End!" or size < 16 or pos + size > len(data):
            break
        chunks.setdefault((tag, rid), data[pos+16:pos+size])
        pos += size
    return chunks
