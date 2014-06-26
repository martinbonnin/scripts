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

def patch_ts(fd):
	streams = {}
	output = bytearray(0)
	print('patch!')
	def log(m):
		if (False):
			print(m)

	while(True):
		packet = bytearray(fd.read(188))
		if (len(packet) != 188):
			break
		if (packet[0] != 0x47):
			print('bad sync byte: %x'%packet[0])
		pid = (packet[1] & 0x1f) << 8
		pid |= packet[2]
		cc_counter = packet[3] & 0xf
		
		if (not pid in streams):
			log('new pid = 0x%04X' % pid)
			# I substract 1 from cc_counter so that we do not have a warning for the first packet
			streams[pid] = {'cc_counter': (cc_counter - 1) & 0xf, 'packet_count': 0}
		stream = streams[pid]

		adaptation_field_exists = packet[3] & 0x20
		prefix_size = 4
		if (adaptation_field_exists):
			if (packet[prefix_size + 1] & 0x80):
				log('discontinuity bit is set on pid %04x, packet %d, clear' % (pid, stream['packet_count']))
				packet[prefix_size + 1] &= ~0x80
		
		expected_cc_counter = (stream['cc_counter'] + 1) & 0xf
		#print('%04x: %2d' % (pid, cc_counter))
		if (cc_counter != expected_cc_counter):
			print('cc error: %2d -> %2d' % (stream['cc_counter'], cc_counter))
		stream['cc_counter'] = cc_counter
		stream['packet_count'] += 1
		output.extend(packet)

	for pid in streams:
		stream = streams[pid]
		log('pid 0x%04x last_cc_counter: %2d' % (pid, stream['cc_counter']))
		# do not patch PAT, SDT or PMT
		if (pid == 0 or pid == 0x11 or pid == 0x100):
			continue
		cc_counter = stream['cc_counter']
		while (cc_counter != 0xf):
			cc_counter += 1
			packet = bytearray(188)
			packet[0] = 0x47
			packet[1] = pid >> 8
			packet[2] = pid & 0xff
			packet[3] = 0x20 | cc_counter #adaptation field exists, no payload
			packet[prefix_size] = 183
			packet[prefix_size + 1] = 0
			log('stuff...')
			output.extend(packet)
			#stuffing
			

	return output
	
		
class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	
	def do_GET(self):
		print("got request for " + self.path)
		#pdb.set_trace()
		path = hls_dir + self.path
				
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

			if (ext == '.ts'):
				data = patch_ts(fd)
			else:
				data = fd.read()
			self.send_response(200)
			self.send_header("Content-type", t)
			self.send_header("Content-length", len(data))
			self.end_headers()
			self.wfile.write(data)
		else:
			self.send_response(404)
			self.end_headers()
			self.wfile.write("cannot find " + path + "\n")
		
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
		print('\thttp://%s:%d/index.m3u8'% (addr, PORT))
	except:
		pass

httpd.serve_forever()
