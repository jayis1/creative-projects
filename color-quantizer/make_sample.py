from quantizer import Image, write_ppm
write_ppm(Image(2, 2, ((0,0,0),(255,0,0),(0,255,0),(0,0,255))), 'examples/sample.ppm')
