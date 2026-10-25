import struct
import unittest
from dns_wirelab import DNSFormatError, build_query, decode_name, encode_name, parse_packet

class DNSWireTests(unittest.TestCase):
    def test_name_roundtrip(self):
        packet = encode_name('example.com')
        self.assertEqual(decode_name(packet, 0), ('example.com.', len(packet)))
    def test_root_name(self): self.assertEqual(encode_name('.'), b'\0')
    def test_query_header_and_question(self):
        q = build_query('example.com', 'AAAA', 7)
        self.assertEqual(struct.unpack('!HHHHHH', q[:12]), (7, 0x100, 1, 0, 0, 0))
        self.assertEqual(parse_packet(q)['questions'][0]['type'], 'AAAA')
    def test_compressed_pointer(self):
        packet = encode_name('example.com') + b'\x03www\xc0\x00'
        self.assertEqual(decode_name(packet, len(encode_name('example.com'))), ('www.example.com.', len(packet)))
    def test_reject_pointer_cycle(self):
        with self.assertRaises(DNSFormatError): decode_name(b'\xc0\x00', 0)
    def test_reject_truncation(self):
        with self.assertRaises(DNSFormatError): parse_packet(b'\0' * 11)
    def test_reject_oversized_label(self):
        with self.assertRaises(DNSFormatError): encode_name('x' * 64)
    def test_decode_a_record(self):
        question = encode_name('x.test') + struct.pack('!HH', 1, 1)
        rr = b'\xc0\x0c' + struct.pack('!HHIH', 1, 1, 60, 4) + bytes((192, 0, 2, 1))
        packet = struct.pack('!HHHHHH', 2, 0x8180, 1, 1, 0, 0) + question + rr
        self.assertEqual(parse_packet(packet)['answers'][0]['data'], '192.0.2.1')
    def test_trailing_data_rejected(self):
        with self.assertRaises(DNSFormatError): parse_packet(build_query('x.test') + b'junk')
    def test_unsupported_qtype(self):
        with self.assertRaises(DNSFormatError): build_query('x.test', 'BOGUS')

if __name__ == '__main__': unittest.main()
