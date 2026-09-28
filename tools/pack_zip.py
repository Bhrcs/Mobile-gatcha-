"""
Writes a standard .zip using zopfli deflate streams (smaller than zlib -9) when
the zopfli binary is available, falling back to zlib otherwise. Keeps the
Windows package under the upload size limit.

    python3 tools/pack_zip.py out.zip file1[=arcname] file2[=arcname] ...
    ZOPFLI=/path/to/zopfli  (default /tmp/zopfli/zopfli)   ZOPFLI_ITER=1
"""
import os
import struct
import subprocess
import sys
import time
import zlib

ZOPFLI = os.environ.get("ZOPFLI", "/tmp/zopfli/zopfli")
ITER = os.environ.get("ZOPFLI_ITER", "1")


def dos_time(ts):
    t = time.localtime(ts)
    return ((t.tm_hour << 11) | (t.tm_min << 5) | (t.tm_sec // 2),
            ((max(t.tm_year, 1980) - 1980) << 9) | (t.tm_mon << 5) | t.tm_mday)


def deflate(path, data):
    best = zlib.compressobj(9, zlib.DEFLATED, -15, 9).compress(data)
    best += b""
    co = zlib.compressobj(9, zlib.DEFLATED, -15, 9)
    best = co.compress(data) + co.flush()
    if os.path.exists(ZOPFLI):
        try:
            z = subprocess.run([ZOPFLI, "--deflate", "--i" + ITER, "-c", path], check=True,
                               stdout=subprocess.PIPE).stdout
            # verify the stream before trusting it
            if zlib.decompress(z, -15) == data and len(z) < len(best):
                best = z
        except (subprocess.CalledProcessError, zlib.error) as e:
            print("zopfli failed for %s (%s); using zlib" % (path, e))
    return best


def main():
    out = sys.argv[1]
    entries = []
    for arg in sys.argv[2:]:
        src, _, arc = arg.partition("=")
        entries.append((src, arc or os.path.basename(src)))
    central = b""
    offset = 0
    with open(out, "wb") as f:
        for src, arc in entries:
            with open(src, "rb") as fh:
                data = fh.read()
            crc = zlib.crc32(data) & 0xFFFFFFFF
            comp = deflate(src, data)
            method = 8
            if len(comp) >= len(data):
                comp, method = data, 0
            tm, dt = dos_time(os.path.getmtime(src))
            name = arc.encode("utf-8")
            local = struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0x0800, method, tm, dt, crc, len(comp), len(data),
                                len(name), 0) + name
            f.write(local)
            f.write(comp)
            central += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 0x0314, 20, 0x0800, method, tm, dt, crc,
                                   len(comp), len(data), len(name), 0, 0, 0, 0,
                                   (0o100644 << 16), offset) + name
            offset += len(local) + len(comp)
            print("%-28s %10d -> %10d" % (arc, len(data), len(comp)))
        f.write(central)
        f.write(struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(entries), len(entries), len(central), offset, 0))
    print("wrote %s: %d bytes" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    main()
