#! /usr/bin/env python

import sys
import threading
import Queue
import time
import requests
import errno
import copy
import os
import pdb
import termios
import tty

import m3u8

out_dir = './'
old_settings = []
log_queue = Queue.Queue(0)

def logThread():
	while True:
		m = log_queue.get()
		sys.stdout.write(m)

t = threading.Thread(target = logThread)
t.daemon = True
t.start()

def log(m):
	log_queue.put(m)


def downloadThread(v):
	#log('thread starting bps=%d\n'% v.bps)
	dirname = out_dir + '/' + str(v.bps) + '/'
	try:
		os.makedirs(dirname)
	except OSError as e:
		if (e.errno != errno.EEXIST):
			raise e

	out_playlist = m3u8.Playlist(dirname + '/index.m3u8')
	
	in_playlist = m3u8.parse(v.absolute_url)
	seq = in_playlist.media_sequence
	while True:
		e = in_playlist.getEntry(seq)
		if (not e):
			if (not in_playlist.endlist):
				time.sleep(1)
				in_playlist = m3u8.parse(v.absolute_url)
				if (in_playlist.media_sequence > seq):
					log('sequence discontinuity: %d -> %d\n' % seq, in_playlist.media_sequence)
					seq = in_playlist.media_sequence
					e = in_playlist.getEntry(seq)
					if (not e):
						log('empty playlist\n')
						continue
				else:
					continue
			else:
				break

		log(e.absolute_url + '\n')

		try:
			r = requests.get(e.absolute_url)
		except requests.exceptions.RequestException as ex:
			time.sleep(1)
			log('exception on ' + e.absolute_url + ' ' + ex)
			continue
			
		if (r.status_code/100 != 2):
			log('error %d on %s\n', r.status_code, e.absolute_url)
			continue

		tsname = str(seq) + '.ts'
		with open(dirname + '/' + tsname, 'wb') as fd:
			for chunk in r.iter_content(128 * 1024):
				fd.write(chunk)

		e.url = tsname
		out_playlist.append_entry(e)
		out_playlist.save()
		
		seq += 1		

pdb_lock = threading.Lock()

def downloadThreadWrapper(v):
	try:
		downloadThread(v)
	except Exception as e:
		 pdb_lock.acquire()
		 termios.tcsetattr(0, termios.TCSADRAIN, old_settings)
		 sys.stderr.write('Exception: ' + str(e) + '\n')
		 sys.stderr.write('entering post mortem...\n')
		 pdb.post_mortem()
		 pdb_lock.release()
		 
def main():
	variants = []
	if (len(sys.argv) < 3):
		log('usage: ' + sys.argv[0] + ' [url of the m3u8] [path to output directory]\n')
		sys.exit(1)
	
	global out_dir
	out_dir = sys.argv[2]
	try:
		os.makedirs(out_dir)
	except OSError as e:
		if (e.errno != errno.EEXIST):
			raise e

	out_playlist = m3u8.Playlist(out_dir + '/index.m3u8')
	
	in_playlist = m3u8.parse(sys.argv[1])
	for v in in_playlist.variants:
		variants.append(v)

	if (len(variants) == 0):
		v = m3u8.Variant(sys.argv[1], 0)
		variants.append(v)
		
	for v in variants:
		v2 = copy.copy(v)
		v2.url = str(v2.bps)
		log('variant: ' + v.absolute_url + '\n') 
		out_playlist.append_variant(v2)

	out_playlist.save()

	for v in variants:
		t = threading.Thread(target = downloadThreadWrapper, args = (v,))
		t.daemon = True
		t.start()


	#beurk...
	global old_settings
	old_settings = termios.tcgetattr(0)
	try:
		new_settings = copy.copy(old_settings)
		f = 3
		new_settings[f] = new_settings[f] & ~termios.ICANON
		new_settings[f] = new_settings[f] & ~termios.ECHO
		termios.tcsetattr(0, termios.TCSADRAIN, new_settings)
		termios.tcdrain(0)
		while True:
			ch = sys.stdin.read(1)
			#sys.stderr.write('got char: ' + ch)
			if (ch == 'q'):
				sys.exit(1)
	finally:
		termios.tcsetattr(0, termios.TCSADRAIN, old_settings)
		

if __name__ == '__main__':
	main()

