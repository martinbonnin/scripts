#!/usr/bin/env python

import BaseHTTPServer
import SocketServer
import pdb
import os
import logging
import subprocess
import threading
import netifaces
import sys

PORT = 8080

class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	
	def do_GET(self):
		print("got request for " + self.path);
		#pdb.set_trace();
		path = hls_dir + self.path;
				
		try:
			fd = open(path);
		except:
			fd = None

		if (fd):
			(root, ext) = os.path.splitext(path)
			if (ext == '.ts'):
				t = 'video/mp2t'
			elif (ext == '.m3u8'):
				t = 'application/vnd.apple.mpegurl'
			else:
				t =  'application/octet-stream'

			data = fd.read();
			self.send_response(200);
			self.send_header("Content-type", t);
			self.send_header("Content-length", len(data));
			self.end_headers();
			self.wfile.write(data);
		else:
			self.send_response(404);
			self.end_headers();
			self.wfile.write("cannot find " + path + "\n");
		
class MyServer(SocketServer.TCPServer):
	allow_reuse_address = True

if (len(sys.argv) != 2):
	print('usage: %s [base directory of the HLS files]'%sys.argv[0])
	sys.exit(1)

hls_dir = sys.argv[1]

httpd = MyServer(("", PORT), MyHandler)

print "hls_dir: " + hls_dir
print ""
print('hls served at:')
interfaces = netifaces.interfaces()
for interface in interfaces:
	try:
		addr = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
		print('\thttp://%s:%d'% (addr, PORT))
	except:
		pass

httpd.serve_forever()
