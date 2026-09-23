HELPERS = {
"bytes": r'''
def __boa_bytes(value):
    return value if isinstance(value, bytes) else str(value).encode("utf-8")
''',
"digest": r'''
def __boa_digest(mode, source, algorithm, value, expected=""):
    data = pathlib.Path(value).read_bytes() if source == "file" else __boa_bytes(value)
    digest = format(zlib.crc32(data) & 0xffffffff, "08x") if algorithm == "crc32" else hashlib.new(algorithm, data).hexdigest()
    return (hmac.compare_digest(digest.casefold(), str(expected).strip().casefold()), digest) if mode == "verify" else digest
''',
}

