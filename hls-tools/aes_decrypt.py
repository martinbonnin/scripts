#!/usr/bin/env python
import m3u8
import sys
import requests

from Crypto.Cipher import AES


if __name__ == '__main__':
	if (len(sys.argv) < 4):
		print('%s [name of the file] [url to key] [iv hex-encoded]'%(sys.argv[0]))
		sys.exit(1)
	fd = open(sys.argv[1], "rb")

	keyUrl = sys.argv[2];
	if (keyUrl.startswith("http")):
		try:
			kr = requests.get(sys.argv[2]).content
		except requests.exceptions.RequestException as ex:
			time.sleep(1)
			Logger.log('exception on key ' + sys.argv[2] + ' ' + ex)
			raise ex
	else:
		kfd = open(keyUrl, "rb")
		kr = kfd.read()
		
	iv = sys.argv[3].decode('hex')
	data = fd.read();
	padding = 16 - (len(data) % 16)
	data += chr(padding)*padding
	aes = AES.new(kr, AES.MODE_CBC, iv)	
	data = aes.decrypt(data)
	data = data[:-padding]

	fd = open(sys.argv[1] + "_clear", "wb")
	fd.write(data)
