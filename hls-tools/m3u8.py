import requests
import re
import urlparse

class M3U8Exception(Exception):
	def __init__(self, m):
		Exception.__init__(self, m)
		self.m = m

class Entry:
	pass
	
class Variant:
	pass
	
	
class Playlist:
	def __init__(self, filename):
		self.filename = filename
		self.entries = []
		self.variants = []
		self.endlist = False

	def save(self):
		if (self.filename == None):
			raise M3U8Exception('cannot save playlist')
		
		fd = open(self.filename, 'wb')
		
		fd.write('#EXTM3U\n')
		if (len(self.variants) > 0):
			for v in self.variants:
				fd.write('#EXT-X-STREAM-INF:BANDWIDTH=%d\n'%v.bps)
				fd.write(v.url + '\n')
		else:
			for e in self.entries:
				fd.write('#EXTINF:%f\n'%e.extinf)
				fd.write(e.url + '\n')
				
	def append_entry(self, e):
		if (len(self.variants) > 0):
			raise M3U8Exception('cannot append entry to a main playlist')
		self.entries.append(e)

	def append_variant(self, e):
		if (len(self.entries) > 0):
			raise M3U8Exception('cannot append variant to a variant playlist')
		self.variants.append(e)

	def parseAttributeList(self, l):
		name = ''
		value = ''
		in_name = True;
		quoted = False;

		attr = {}
		for c in l:
			if (in_name):
				if (c == '='):
					in_name = False;
				else:
					name += c
			else:
				if(c == '"'):
					if (not quoted):
						quoted = True
					else:
						quoted = False
				elif (quoted or c != ','):
					value += c
				else:
					attr[name] = value
					name = ''
					value = ''
					in_name = True
					quoted = False
		return attr
			
	def parse(self, url):
		self.entries = []
		self.variants = []

		r = requests.get(url)
			
		if (r.status_code/100 != 2):
			raise M3U8Exception('HTTP error %d on %s'% (r.status_code, url))
		
		lines = r.text.split('\n')
		self.media_sequence = 0
		if len(lines) == 0:
			raise M3U8Exception('empty playlist')
		
		if (lines[0].find('#EXTM3U') != 0):
			raise M3U8Exception('playlist does not start with #EXTM3U')

		lines.pop(0)
		
		e = None
		v = None
		for line in lines:
			m = re.match(r'#EXTINF:([^,]*),?(.*)', line)
			if (m):
				e = Entry()
				e.extinf = float(m.group(1))
				continue
			if (line.find('#EXT-X-STREAM-INF:') == 0):
				attr = self.parseAttributeList(line[len('#EXT-X-STREAM-INF:'):])
				v = Variant()
				v.bps = int(attr['BANDWIDTH'])
				continue
			if (line.find('#EXT-X-ENDLIST') == 0):
				self.endlist = True
				continue
			m = re.match(r'#EXT-X-MEDIA-SEQUENCE:(.*)', line)
			if (m):
				self.media_sequence = int(m.group(1))
				continue
						
			if (not line.find('#') == 0):
				absolute_url = urlparse.urljoin(url, line)
				if (e):
					e.url = line
					e.absolute_url = absolute_url
					self.append_entry(e)
					e = None
				elif (v):
					v.url = line
					v.absolute_url = absolute_url
					self.append_variant(v)
					v = None
				continue
					
	def getEntry(self, seq):
		seq -= self.media_sequence
		
		if (seq < 0 or seq >= len(self.entries)):
			return None
		return self.entries[seq]

def parse(url):
	playlist = Playlist(None)
	playlist.parse(url)
	return playlist
