"""Safe, offline DNS wire-format encoder and diagnostic decoder."""
from __future__ import annotations
import argparse
import json
import struct
from dataclasses import dataclass


class DNSFormatError(ValueError):
    """Malformed or unsupported DNS wire data."""


def encode_name(name: str) -> bytes:
    if name == '.':
        return b'\0'
    labels = name.rstrip('.').split('.')
    out = bytearray()
    for label in labels:
        try:
            raw = label.encode('idna')
        except UnicodeError as exc:
            raise DNSFormatError('invalid or overlong IDN label') from exc
        if not raw or len(raw) > 63:
            raise DNSFormatError('DNS labels must contain 1..63 encoded bytes')
        out.append(len(raw)); out.extend(raw)
    out.append(0)
    if len(out) > 255:
        raise DNSFormatError('encoded DNS name exceeds 255 bytes')
    return bytes(out)


def decode_name(packet: bytes, offset: int) -> tuple[str, int]:
    """Decode a possibly compressed name; return name and next original offset."""
    if offset < 0 or offset >= len(packet):
        raise DNSFormatError('name offset outside packet')
    labels, pos, end, seen = [], offset, None, set()
    expanded = 1
    while True:
        if pos >= len(packet):
            raise DNSFormatError('truncated DNS name')
        size = packet[pos]
        if size & 0xC0 == 0xC0:
            if pos + 1 >= len(packet):
                raise DNSFormatError('truncated compression pointer')
            pointer = ((size & 0x3F) << 8) | packet[pos + 1]
            if pointer >= len(packet) or pointer in seen:
                raise DNSFormatError('invalid or cyclic compression pointer')
            seen.add(pointer)
            if end is None:
                end = pos + 2
            pos = pointer
            continue
        if size & 0xC0:
            raise DNSFormatError('reserved label encoding')
        pos += 1
        if size == 0:
            return '.'.join(labels) + ('.' if labels else '.'), end if end is not None else pos
        if size > 63 or pos + size > len(packet):
            raise DNSFormatError('invalid or truncated DNS label')
        expanded += size + 1
        if expanded > 255:
            raise DNSFormatError('expanded DNS name exceeds 255 bytes')
        try:
            labels.append(packet[pos:pos + size].decode('ascii'))
        except UnicodeDecodeError as exc:
            raise DNSFormatError('non-ASCII label in wire packet') from exc
        pos += size


TYPES = {1: 'A', 2: 'NS', 5: 'CNAME', 6: 'SOA', 12: 'PTR', 15: 'MX', 16: 'TXT', 28: 'AAAA'}


def build_query(name: str, qtype: str = 'A', txid: int = 0x1234, recursion: bool = True) -> bytes:
    typ = next((k for k, v in TYPES.items() if v == qtype.upper()), None)
    if typ is None or not 0 <= txid <= 65535:
        raise DNSFormatError('unsupported query type or transaction ID')
    flags = 0x0100 if recursion else 0
    return struct.pack('!HHHHHH', txid, flags, 1, 0, 0, 0) + encode_name(name) + struct.pack('!HH', typ, 1)


def parse_packet(packet: bytes) -> dict:
    if len(packet) < 12:
        raise DNSFormatError('packet shorter than DNS header')
    txid, flags, qd, an, ns, ar = struct.unpack_from('!HHHHHH', packet)
    if sum((qd, an, ns, ar)) > 4096:
        raise DNSFormatError('record count exceeds safety limit')
    pos = 12
    questions = []
    for _ in range(qd):
        name, pos = decode_name(packet, pos)
        if pos + 4 > len(packet): raise DNSFormatError('truncated question')
        typ, cls = struct.unpack_from('!HH', packet, pos); pos += 4
        questions.append({'name': name, 'type': TYPES.get(typ, f'TYPE{typ}'), 'class': cls})
    sections = {}
    for section, count in (('answers', an), ('authority', ns), ('additional', ar)):
        records = []
        for _ in range(count):
            name, pos = decode_name(packet, pos)
            if pos + 10 > len(packet): raise DNSFormatError('truncated resource record header')
            typ, cls, ttl, length = struct.unpack_from('!HHIH', packet, pos); pos += 10
            end = pos + length
            if end > len(packet): raise DNSFormatError('truncated resource record data')
            data = packet[pos:end]
            if typ == 1 and length == 4: value = '.'.join(map(str, data))
            elif typ == 28 and length == 16: value = ':'.join(f'{int.from_bytes(data[i:i+2], "big"):x}' for i in range(0, 16, 2))
            elif typ in (2, 5, 12):
                value, consumed = decode_name(packet, pos)
                if consumed > end: raise DNSFormatError('name exceeds record data')
            elif typ == 15 and length >= 3:
                preference = struct.unpack_from('!H', packet, pos)[0]
                exchange, consumed = decode_name(packet, pos + 2)
                if consumed != end: raise DNSFormatError('malformed MX record data')
                value = {'preference': preference, 'exchange': exchange}
            elif typ == 16:
                chunks, i = [], 0
                while i < length:
                    n = data[i]; i += 1
                    if i + n > length: raise DNSFormatError('malformed TXT string')
                    chunks.append(data[i:i+n].decode('utf-8', 'replace')); i += n
                value = chunks
            else: value = data.hex()
            records.append({'name': name, 'type': TYPES.get(typ, f'TYPE{typ}'), 'class': cls, 'ttl': ttl, 'data': value})
            pos = end
        sections[section] = records
    if pos != len(packet): raise DNSFormatError('trailing bytes after DNS sections')
    return {'id': txid, 'flags': flags, 'response': bool(flags & 0x8000), 'rcode': flags & 15, 'questions': questions, **sections}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    query = sub.add_parser('query', help='encode a DNS query as hex')
    query.add_argument('name'); query.add_argument('--type', default='A', choices=sorted(set(TYPES.values())))
    query.add_argument('--id', type=lambda s: int(s, 0), default=0x1234)
    inspect = sub.add_parser('inspect', help='decode a DNS packet supplied as hex')
    inspect.add_argument('hex')
    args = parser.parse_args(argv)
    try:
        if args.command == 'query': print(build_query(args.name, args.type, args.id).hex())
        else: print(json.dumps(parse_packet(bytes.fromhex(args.hex)), indent=2))
    except (DNSFormatError, ValueError) as exc:
        parser.error(str(exc))

if __name__ == '__main__':
    main()
