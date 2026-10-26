import tempfile
import unittest
from pathlib import Path
from quantizer import Image, median_cut, quantize, read_ppm, write_ppm

class Tests(unittest.TestCase):
    def test_palette_and_roundtrip(self):
        im=Image(2,1,((0,0,0),(255,255,255)))
        self.assertEqual(len(median_cut(im.pixels,2)),2)
        out=quantize(im,2)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.ppm'; write_ppm(out,p); self.assertEqual(read_ppm(p),out)
    def test_bad_palette(self):
        with self.assertRaises(ValueError): median_cut(((0,0,0),),0)
    def test_short_data(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.ppm'; p.write_bytes(b'P6\n1 1\n255\n\x00')
            with self.assertRaises(ValueError): read_ppm(p)
    def test_crlf_header_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'crlf.ppm'; p.write_bytes(b'P6\r\n1 1\r\n255\r\n\x01\x02\x03')
            self.assertEqual(read_ppm(p).pixels, ((1,2,3),))

if __name__=='__main__': unittest.main()
