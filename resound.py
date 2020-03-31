import sys
import io
import struct
from enum import Enum, Flag

from contextlib import contextmanager


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

class ResMap(object):
	# __slots__ = []
	def __init__(self):
		self.flags = 0
		self.offset = 0
		self.size = 0
		self.toIndex = 0
		self.indexSize = 0
		self.indexUsed = 0
		self.freeListSize = 0
		self.freeListUsed = 0
		self.freeList = []
		self.entries = []



class ResourceWriter(object):

	def __init__(self):
		self._resources = []
		self._resource_ids = set()

	# def unique_id(self, type):
	# 	if type < 0 || type > 0x10000:
	# 		raise Exception();

	# 	used = self._id_map.get(type)
	# 	if used: 

	def add_resource(self, rtype, rid, data, attr=0):
		if type(rtype) == rTypes: rtype = rtype.value
		if rtype < 0 or rtype > 0xffff:
			raise Exception()

		if rid < 0 or rid > 0xffffffff:
			raise Exception()

		if (rid, rtype) in self._resource_ids:
			raise Exception()

		self._resources.append((rtype, rid, attr, data))
		self._resource_ids.add((rtype, rid))


	def write(self,io):
		# only need 1 free list entry (unless reserved space is supported)

		# free list always has extra blank 4-bytes at end.
		# free list available grows by 10?

		freelist_size = 10
		freelist_used = 1
		index_used = len(self._resources)
		index_size = 10 + index_used // 10 * 10

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

		index = bytearray()
		for x in self._resources:
			# type:2, id:4, offset:4, attr:2, size:4, handle:4
			index += struct.pack("<HIIHII",
				x[0], x[1], eof, 
				x[2], len(x[3]), 0
			)
			eof += len(x[3])

		index += bytes(20 * ((index_size - index_used)))

		# one free list entry at eof.
		# need to update if growth buffer allowed after resource data...
		freelist = bytearray()
		freelist += struct.pack("<II", eof, 0xffffffff-eof)
		freelist += bytes(8 * (freelist_size - freelist_used) + 4)


		io.write(rheader)
		io.write(rmap)
		io.write(freelist)
		io.write(index)

		for x in self._resources:
			io.write(x[3])

		return eof

# class ResEntry(object):
# 	__slots__ = ['type', 'id', 'offset', 'attr', 'size']
# 	def __init__(self):
# 		self.type = 0
# 		self.id = 0
# 		self.offset = 0
# 		self.attr = 0
# 		self.size = 0


# class ResFreeBlock(object):
# 	__slots__ = ['offset', 'size']



# HyperCard assumes a sample rate of 26.32 KHz
# and a pitch of 261.63 Hz (Middle C, C4)
# See HyperCard IIGs Tech Note #3: Pitching Sampled Sounds
def relative_pitch(fW, fS):
	# fW = frequency of sample
	# fS = sampling rate

	if fW == 0: return 0
	r = (261.63 * fS) / (26320 * fW)
	if r == 0: return 0

	offset = round(3072 * log2(r))
	if (offset < -32767) or (offset > 32767):
		raise Exception()
	if offset < 0: offset = 0x8000 | abs(offset)



@contextmanager
def open_res_fork(file, mode="wb"):

	parent = None
	child = None
	try:
		parent = io.open(file, "r+") # create if it doesn't exist
		child = io.open(file + "/..namedfork/rsrc", mode)
		yield child

	finally:
		if parent: parent.close()
		if child: child.close()


r = ResourceWriter()
r.add_resource(rTypes.rComment, 1, b"ORCA/C-Copyight 1997, Byte Works, Inc.\x0dUpdated 2020")
with open_res_fork("bleh.r", "wb") as f:
	r.write(f)
