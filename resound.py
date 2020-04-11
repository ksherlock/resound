import sys
import io
import os
import struct
from math import log2
from enum import Enum, Flag
from itertools import groupby
import os.path
import argparse

# from contextlib import contextmanager


def _validate_mode(mode):
	# strips "t" format, adds "b" format, and checks if the 
	# base file needs to be created.
	# full validation will be handled by os.open
	r = False
	w = False
	plus = False
	rmode = "b"
	for x in mode:
		if x == "r": r = True
		elif x in ["a", "x", "w"]: w = True
		elif x in ["+"]: plus = True
		else: continue
		rmode += x

	mode = ["r", "a"][w]  # create if it does not exist.
	return (mode, rmode)

def _open2(file, rfile, mode):

	a = None
	b = None

	(mode, rmode) = _validate_mode(mode)
	try:
		a = io.open(file, mode)
		b = io.open(rfile, rmode)
	except Exception as e:
		raise
	finally:
		if a: a.close()

	a.close()
	return b

_finder_magic = {
	(0x00, 0x0000): b"BINApdos",
	(0x04, 0x0000): b"TEXTpdos",
	(0xff, 0x0000): b"PSYSpdos",
	(0xb3, 0x0000): b"PS16pdos",
	(0xd7, 0x0000): b"MIDIpdos",
	(0xd8, 0x0000): b"AIFFpdos",
	(0xd7, 0x0001): b"AIFCpdos",
	(0xe0, 0x0005): b"dImgdCpy",
}
_z24 = bytearray(24)
def _make_finder_data(filetype, auxtype):

	k = (filetype, auxtype)
	x = _finder_magic.get((filetype, auxtype))
	if not x:
		x = struct.pack(">cBH4s", b'p', filetype & 0xff, auxtype & 0xffff, b"pdos")

	return x

if sys.platform == "win32":

	def open_rfork(file, mode="r"):
		# protect against c -> c:stream
		file = os.path.realpath(file)
		rfile = file + ":AFP_Resource"
		return _open2(file, rfile, mode)

	def set_file_type(path, filetype, auxtype):
		path = os.path.realpath(path)
		path += ":AFP_AfpInfo"
		f = open(path, "wb")

		data = struct.pack("<IIII8s24xHI8x",
			0x00504641, 0x00010000, 0, 0x80000000,
			_make_finder_data(filetype, auxtype),
			filetype, auxtype
		)

		f.write(data)
		f.close()
		return True


if sys.platform == "darwin":
	def open_rfork(file, mode="r"):
		file = os.path.realpath(file)
		rfile = file + "/..namedfork/rsrc"
		return _open2(file, rfile, mode)

	# os.setxattr only availble in linux.
	import ctypes
	_libc = ctypes.CDLL(None)
	_setxattr = _libc.setxattr
	_setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p,
		ctypes.c_void_p, ctypes.c_size_t,
		ctypes.c_uint32, ctypes.c_int]
	def set_file_type(path, filetype, auxtype):

		data = struct.pack(">8s24x", _make_finder_data(filetype, auxtype))
		# os.setxattr(path, "com.apple.FinderInfo", data, 0, 0)
		# data = array.array('B', data)
		# (address, size) = data.buffer_info()
		ok = _setxattr(path.encode("utf-8"), b"com.apple.FinderInfo", data, 32, 0, 0)
		e = ctypes.get_errno()
		# print("ok: {}, errno: {}".format(ok, e))
		if ok < 0: return False
		return True



class rTypes(Enum):
	rIcon = 0x8001                    # Icon type 
	rPicture = 0x8002                 # Picture type 
	rControlList = 0x8003             # Control list type 
	rControlTemplate = 0x8004         # Control template type 
	rC1InputString = 0x8005           # GS/OS class 1 input string 
	rPString = 0x8006                 # Pascal string type 
	rStringList = 0x8007              # String list type 
	rMenuBar = 0x8008                 # MenuBar type 
	rMenu = 0x8009                    # Menu template 
	rMenuItem = 0x800A                # Menu item definition 
	rTextForLETextBox2 = 0x800B       # Data for LineEdit LETextBox2 call 
	rCtlDefProc = 0x800C              # Control definition procedure type 
	rCtlColorTbl = 0x800D             # Color table for control 
	rWindParam1 = 0x800E              # Parameters for NewWindow2 call 
	rWindParam2 = 0x800F              # Parameters for NewWindow2 call 
	rWindColor = 0x8010               # Window Manager color table 
	rTextBlock = 0x8011               # Text block 
	rStyleBlock = 0x8012              # TextEdit style information 
	rToolStartup = 0x8013             # Tool set startup record 
	rResName = 0x8014                 # Resource name 
	rAlertString = 0x8015             # AlertWindow input data 
	rText = 0x8016                    # Unformatted text 
	rCodeResource = 0x8017
	rCDEVCode = 0x8018
	rCDEVFlags = 0x8019
	rTwoRects = 0x801A                # Two rectangles 
	rFileType = 0x801B                # Filetype descriptors--see File Type Note $42 
	rListRef = 0x801C                 # List member 
	rCString = 0x801D                 # C string 
	rXCMD = 0x801E
	rXFCN = 0x801F
	rErrorString = 0x8020             # ErrorWindow input data 
	rKTransTable = 0x8021             # Keystroke translation table 
	rWString = 0x8022                 # not useful--duplicates $8005 
	rC1OutputString = 0x8023          # GS/OS class 1 output string 
	rSoundSample = 0x8024
	rTERuler = 0x8025                 # TextEdit ruler information 
	rFSequence = 0x8026
	rCursor = 0x8027                  # Cursor resource type 
	rItemStruct = 0x8028              # for 6.0 Menu Manager 
	rVersion = 0x8029
	rComment = 0x802A
	rBundle = 0x802B
	rFinderPath = 0x802C
	rPaletteWindow = 0x802D           # used by HyperCard IIgs 1.1
	rTaggedStrings = 0x802E
	rPatternList = 0x802F
	rRectList = 0xC001
	rPrintRecord = 0xC002
	rFont = 0xC003


class rAttr(Flag):

	attrPage = 0x0004   
	attrNoSpec = 0x0008 
	attrNoCross = 0x0010
	resChanged = 0x0020
	resPreLoad = 0x0040
	resProtected = 0x0080
	attrPurge1 = 0x0100
	attrPurge2 = 0x0200
	attrPurge3 = 0x0300
	resAbsLoad = 0x0400
	resConverter = 0x0800
	attrFixed = 0x4000
	attrLocked = 0x8000

	attrPurge = 0x0300

class ResourceWriter(object):

	def __init__(self):
		self._resources = []
		self._resource_ids = set()
		self._resource_names = {}


	def unique_resource_id(self, rtype, range):
		if type(rtype) == rTypes: rtype = rtype.value
		if rtype < 0 or rtype > 0xffff:
			raise ValueError("Invalid resource type ${:04x}".format(rtype))

		if range > 0xffff:
			raise ValueError("Invalid range ${:04x}".format(range))
		if range > 0x7ff and range < 0xffff:
			raise ValueError("Invalid range ${:04x}".format(range))

		min = range << 16
		max = min + 0xffff
		if range == 0:
			min = 1
		elif range == 0xffff:
			min = 1
			max = 0x07feffff

		used = [x[1] for x in self._resource_ids if x[0] == rtype and x[1] >= min and x[1] <= max]
		if len(used) == 0: return min

		used.sort()
		# if used[0] > min: return min

		id = min
		for x in used:
			if x > id: return id
			id = x + 1
		if id >= max:
			raise OverflowError("No Resource ID available in range")
		raise id

	def add_resource(self, rtype, rid, data, *, attr=0, reserved=0, name=None):
		if type(rtype) == rTypes: rtype = rtype.value
		if rtype < 0 or rtype > 0xffff:
			raise ValueError("Invalid resource type ${:04x}".format(rtype))

		if rid < 0 or rid > 0x07ffffff:
			raise ValueError("Invalid resource id ${:08x}".format(rid))

		if (rid, rtype) in self._resource_ids:
			raise ValueError("Duplicate resource ${:04x}:${:08x}".format(rtype, rid))

		# don't allow standard res names since they're handled elsewhere.
		if rtype == rTypes.rResName.value and rid > 0x00010000 and rid < 0x00020000:
			raise ValueError("Invalid resource ${:04x}:${:08x}".format(rtype, rid))


		if name:
			if type(name) == str: name = name.encode('ascii')
			if len(name) > 255: name = name[0:255]
			self._resource_names[(rtype, name)]=rid

		self._resources.append((rtype, rid, attr, data, reserved))
		self._resource_ids.add((rtype, rid))



	def set_resource_name(rtype, rid, name):
		if type(rtype) == rTypes: rtype = rtype.value
		if rtype < 0 or rtype > 0xffff:
			raise ValueError("Invalid resource type ${:04x}".format(rtype))

		if rid < 0 or rid > 0x07ffffff:
			raise ValueError("Invalid resource id ${:08x}".format(rid))

		key = (rtype, name)
		if not name:
			self._resource_names.pop(key, None)
		else:
			if type(name) == str: name = str.encode('ascii')
			if len(name) > 255: name = name[0:255]
			self._resource_names[key] = rid



	@staticmethod
	def _merge_free_list(fl):
		rv = []
		eof = None
		for (offset, size) in fl:
			if offset == eof:
				tt = rv.pop()
				tt[1] += size
				rv.append(tt)
			else:
				rv.append((offset, size))
			eof = offset + size
		return rv

	def _build_res_names(self):
		# format:
		# type $8014, id $0001xxxx (where xxxx = resource type)
		# version:2 [1]
		# name count:4
		# [id:4, name:pstring]+
		#

		rv = []
		tmp = []

		if not len(self._resource_names): return rv
		for (rtype, rname), rid in self._resource_names.items():
			tmp.append( (rtype, rid, rname) )


		keyfunc_type = lambda x: x[0]
		keyfunc_name = lambda x: x[2]
		tmp.sort(key = keyfunc_type)
		for rtype, iter in groupby(tmp, keyfunc_type):
			tmp = list(iter)
			tmp.sort(key=keyfunc_name)
			data = bytearray()
			data += struct.pack("<HI", 1, len(tmp))
			for (_, rid, rname) in tmp:
				data += struct.pack("<IB", rid, len(rname))
				data += rname

			rv.append( (rTypes.rResName.value, 0x00010000 | rtype, 0, data, 0) )

		return rv

	def write(self,io):
		# only need 1 free list entry (until reserved space is supported)

		# free list always has extra blank 4-bytes at end.
		# free list available grows by 10?

		resources = self._build_res_names()

		resources.extend(self._resources)

		index_used = len(resources)
		index_size = 10 + index_used // 10 * 10

		# remove reserved space from the last entry
		ix = len(resources)
		if ix and resources[ix-1][4]:
			(rid, rtype, attr, data, _) = resources[ix-1]
			resources[ix-1] = (rid, rtype, attr, data, 0)


		freelist_used = 1
		for x in resources:
			if x[4]: freelist_used += 1
		freelist_size = 10 + freelist_used // 10 * 10

		extra = freelist_size * 8 + 4 + index_size * 20

		map_size = 32 + extra
		map_offset = 0x8c

		# version, offset to map, sizeof map, 128 bytes (reserved) 
		rheader = struct.pack("<III128s", 0, map_offset, map_size, b"\x00")

		# handle:4, flags:2, offset:4, size:4, toindex:2, filenum:2, id:2,
		# indexSize:4, indexUsed:4, flSize:2,flUsed:2,
		rmap = struct.pack("<IHIIHHHIIHH",
			0, 0, map_offset, map_size,
			32 + freelist_size * 8 + 4, 
			0, 0,
			index_size, index_used,
			freelist_size, freelist_used
		)

		eof = 0x8c + map_size
		fl = []

		index = bytearray()
		for (rtype, rid, attr, data, reserved) in resources:
			# type:2, id:4, offset:4, attr:2, size:4, handle:4
			index += struct.pack("<HIIHII",
				rtype, rid, eof, 
				attr, len(data), 0
			)
			eof += len(data)
			if reserved:
				fl.append((eof, reserved))
				eof += reserved

		index += bytes(20 * ((index_size - index_used)))

		fl.append((eof, 0xffffffff-eof))

		fl = self._merge_free_list(fl)

		freelist = bytearray()
		for (offset, size) in fl:
			freelist += struct.pack("<II", offset, size)
		freelist += bytes(8 * (freelist_size - freelist_used) + 4)


		io.write(rheader)
		io.write(rmap)
		io.write(freelist)
		io.write(index)

		for (_, _, attr, data, reserved) in resources:
			io.write(data)
			if reserved: io.write(bytes(reserved))

		return eof



# HyperCard assumes a sample rate of 26.32 KHz
# and a pitch of 261.63 Hz (Middle C, C4)
# See HyperCard IIgs Tech Note #3: Pitching Sampled Sounds
def relative_pitch(fS, fW = None):
	# fW = frequency of sample
	# fS = sampling rate


	if fW: r = (261.63 * fS) / (26320 * fW)
	else: r = fS / 26320


	offset = round(3072 * log2(r))
	if (offset < -32767) or (offset > 32767):
		raise Exception("Offset too big")
	if offset < 0: offset = 0x8000 | abs(offset)
	return offset

import wave
import audioop
def read_wav(infile, resample = None, freq=None):

	# rSound Sample format:
	# format:2 (0)
	# wave size:2 (sample size, in pages)
	# relative pitch:2
	# stereo: 2
	# sample rate:2
	# sound data....


	rv = bytearray()
	tr = b"\x01" + bytes(range(1,256)) # remap 0 -> 1


	rv += struct.pack("<10x") # header filled in later

	w = wave.open(infile, "rb")

	# info = w.getparams()
	width = w.getsampwidth() # info.sampwidth

	channels = w.getnchannels()
	rate = w.getframerate()

	if channels > 2:
		raise Exception("{}: Too many channels ({})".format(infile, channels))


	cookie = None
	while True:
		frames = w.readframes(32)
		if not frames: break

		if channels > 1:
			frames = audioop.tomono(frames, width, 0.5, 0.5)

		if resample:
			frames, cookie = audioop.ratecv(frames, width, 1, rate, resample, cookie)

		if width != 1:
			frames = audioop.lin2lin(frames, width, 1)
			frames = audioop.bias(frames, 1, 128)

		frames = frames.translate(tr)
		rv += frames
	w.close()

	# based on system 6 samples, pages rounds down....
	pages = (len(rv)-10) >> 8
	hz = resample or rate

	struct.pack_into("<HHHHH", rv, 0,
		0, # format
		pages, # wave size in pages
		relative_pitch(hz, freq),
		0, # stereo ???
		hz # hz
	)


	return rv


def path2name(p):
	a, b = os.path.splitext(os.path.basename(p))
	return a	 



def freq_func(x):

	freq0 = {
		'c': 16.35160,
		'c#': 17.32391,
		'db': 17.32391,
		'd': 18.35405,
		'd#': 19.44544,
		'eb': 19.44544,
		'e': 20.60172,
		'f': 21.82676,
		'f#': 23.12465,
		'gb': 23.12465,
		'g': 24.49971,
		'g#': 25.95654,
		'ab': 25.95654,
		'a': 27.5,
		'a#': 29.13524,
		'bb': 29.13524,
		'b': 30.86771,
	}

	# allow C4, C#1, Bb2, etc
	# -or- a float
	m = re.match("([A-Ga-g][#b]?)([0-8])", x)
	if m:
		a = m[1].lower()
		n = int(m[2])

		base = freq0[a]
		return base * (2 ** n)

	return float(x)

if __name__ == '__main__':
	p = argparse.ArgumentParser(prog='resound')
	p.add_argument('files', metavar='file', type=str, nargs='+')
	p.add_argument('-c', '--comment', metavar='text', type=str)
	p.add_argument('-n', '--name', metavar='name', type=str)
	p.add_argument('-s', '--sample', metavar='rate', type=int)
	p.add_argument('-o', metavar='file', type=str)
	p.add_argument('-f', '--freq', metavar='freq', type=freq_func)
	p.add_argument('--version', action='version', version='resound 1.0')
	opts = p.parse_args()

	outfile = opts.o or 'sound.r'


	if len(opts.files) > 1:
		opts.name = None


	r = ResourceWriter()
	if opts.comment:
		s = opts.comment.encode('mac_roman')
		r.add_resource(rTypes.rComment, 1, s)

	n = 1
	for f in opts.files:
		name = opts.name or path2name(f)
		data = read_wav(f, opts.sample, opts.freq)
		r.add_resource(rTypes.rSoundSample, n, data, name=name)
		n = n + 1

	fp = open_rfork(outfile, "wb")
	r.write(fp)
	fp.close()
	set_file_type(outfile, 0xd8, 0x0003)
	sys.exit(0)

