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

import m3u8

class DebuggableThread(threading.Thread):
	lock = threading.Lock()

	def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
		super(DebuggableThread, self).__init__(group, target, name, args, kwargs)
			
	def run(self):
		try:
			super(DebuggableThread, self).run()
		except Exception as e:
			 self.lock.acquire()
			 sys.stderr.write('Exception: ' + str(e) + '\n')
			 sys.stderr.write('entering post mortem...\n')
			 pdb.post_mortem()
			 self.lock.release()
		
class Logger():
	queue = Queue.Queue(0)
	thread = None
	state = 0
	
	@staticmethod
	def logThread():
		while (Logger.state == 0):
			m = Logger.queue.get()
			sys.stdout.write(m)
		Logger.state = 2
	
	@staticmethod
	def log(m):
		if (not Logger.thread):
			thread = DebuggableThread(target = Logger.logThread)
			thread.daemon = True
			thread.start()
		Logger.queue.put(m)
	
	@staticmethod
	def done():
		Logger.state = 1
		Logger.log('logerThread finished\n')
		while (Logger.state == 1):
			time.sleep(1)

class Extractor():
	MESSAGE_QUIT = 1
	MESSAGE_THREAD_DONE = 2

	def __init__(self, argv):
		if (len(argv) < 3):
			Logger.log('usage: ' + argv[0] + ' [url of the m3u8] [path to output directory]\n')
			sys.exit(1)
		
		self.out_dir = sys.argv[2]
		self.queue = Queue.Queue(0)
		
	def downloadThread(self, v):
		#Logger.log('thread starting bps=%d\n'% v.bps)
		dirname = self.out_dir + '/' + str(v.bps) + '/'
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
						Logger.log('sequence discontinuity: %d -> %d\n' % seq, in_playlist.media_sequence)
						seq = in_playlist.media_sequence
						e = in_playlist.getEntry(seq)
						if (not e):
							Logger.log('empty playlist\n')
							continue
					else:
						continue
				else:
					#Logger.log('reached endlist\n')
					break

			Logger.log(e.absolute_url + '\n')

			try:
				r = requests.get(e.absolute_url)
			except requests.exceptions.RequestException as ex:
				time.sleep(1)
				Logger.log('exception on ' + e.absolute_url + ' ' + ex)
				continue
				
			if (r.status_code/100 != 2):
				Logger.log('error %d on %s\n', r.status_code, e.absolute_url)
				continue

			tsname = str(seq) + '.ts'
			with open(dirname + '/' + tsname, 'wb') as fd:
				for chunk in r.iter_content(128 * 1024):
					fd.write(chunk)

			e.url = tsname
			out_playlist.append_entry(e)
			out_playlist.save()
			
			seq += 1	
		#Logger.log('download endlist\n')
		out_playlist.endlist = True
		out_playlist.save()
		self.queue.put(Extractor.MESSAGE_THREAD_DONE)
			 
	def run(self):
		variants = []
		try:
			os.makedirs(self.out_dir)
		except OSError as e:
			if (e.errno != errno.EEXIST):
				raise e

		out_playlist = m3u8.Playlist(self.out_dir + '/index.m3u8')

		in_playlist = m3u8.parse(sys.argv[1])
		for v in in_playlist.variants:
			variants.append(v)

		if (len(variants) == 0):
			v = m3u8.Variant(sys.argv[1], 0)
			variants.append(v)
			
		Logger.log('type \'q[enter]\' to terminate\n')

		for v in variants:
			v2 = copy.copy(v)
			v2.url = str(v2.bps) + '/index.m3u8'
			Logger.log('variant: ' + v.absolute_url + '\n') 
			out_playlist.append_variant(v2)

		out_playlist.save()

		thread_count = 0
		for v in variants:
			t = DebuggableThread(target = self.downloadThread, args = (v,))
			t.daemon = True
			t.start()
			thread_count += 1

		t  = DebuggableThread(target = self.keyboardThread)	
		t.daemon = True
		t.start()
		
		while (True):
			try:
				#we need a timeout so that Ctrl-C is caught
				m = self.queue.get(timeout=0.1)
			except Queue.Empty:
				continue
				
			if (m == Extractor.MESSAGE_QUIT):
				self.done()
			elif (m == Extractor.MESSAGE_THREAD_DONE):
				thread_count -= 1
				#Logger.log('%d threads remaining\n'%thread_count)
				if (thread_count == 0):
					self.done()
		
	def done(self):
		Logger.done()
		sys.exit(1)

	def keyboardThread(self):
		while True:
			ch = sys.stdin.read(1)
			#sys.stderr.write('got char: ' + ch)
			if (ch == 'q'):
				self.queue.put(Extractor.MESSAGE_QUIT)
			

if __name__ == '__main__':
	extractor = Extractor(sys.argv)
	extractor.run()

