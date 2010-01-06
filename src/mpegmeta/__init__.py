"""
mpegmeta

Python package which is intended to gather all kinds of MPEG related meta 
information from file. Such as duration of MPEG file, average bitrate for 
variable bitrate (VBR) MPEG files, etc.

Most of the information about MPEG Headers is from excellent article 
U{MPEG Audio Frame Header By Konrad Windszus, in Code Project
<http://www.codeproject.com/KB/audio-video/mpegaudioinfo.aspx#MPEGAudioFrame>}.
If you are solely interested on details of MPEG headers that is a good place to 
start. I have taken some paragraphs to documentation from that article.

Usage examples
==============
 
Simple example:
---------------

    >>> import mpegmeta
    >>> try:
    ...     mpeg = mpegmeta.MPEG(open('data/song.mp3', 'rb'))
    ... except mpegmeta.MpegHeaderException:
    ...    pass
    ... else:
    ...     print mpeg.duration
    0:03:12

Lazy parsing
============

Notable feature of mpegmeta is the fact that it L{tries to parse information
lazily <mpegmeta.MPEG>}. It doesn't parse all frames, or ending unless really
needed.

@author: Jari Pennanen
@copyright: Jari Pennanen, 2009.
@contact: jari.pennanen@gmail.com
@license: GNU Lesser General Public License (LGPL). 
@version: 0.5 Non-published.

"""
# Pylint disable settings:
# ------------------------
# ToDos, DocStrings:
# pylint: disable-msg=W0511,W0105
 
# Unused variable, argument:
# pylint: disable-msg=W0612,W0613

# Re-define built-in:
# pylint: disable-msg=W0622

# Protected member access: 
# pylint: disable-msg=W0212

# Line too long C0301, too many lines per module:
# pylint: disable-msg=C0302

# Too many instance attributes, Too few public methods:
# pylint: disable-msg=R0902,R0903

# TODO: LOW: I don't like the verboseness of EpyDoc syntax, maybe change to
# reStructuredText?

from datetime import timedelta
import math
import struct

PARSE_ALL_CHUNK_SIZE = 153600
"""Chunk size of parsing all frames.
@type: int"""

DEFAULT_CHUNK_SIZE = 8192
"""Chunk size for various other tasks.
@type: int"""


# Value lookup tables, for parsing headers:

_MPEG_VERSIONS = {
    0 : '2.5',
    2 : '2',
    3 : '1',
}
    
_LAYERS = {
    1 : '3',
    2 : '2',
    3 : '1',
}

_BITRATE__2__2_5 = {
    '1': (0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
    '2': (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
    '3': (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
}

_BITRATE = {
'1': {
    '1': (0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448),
      '2': (0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384),
      '3': (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
    },
'2' : _BITRATE__2__2_5,
'2.5' : _BITRATE__2__2_5,
} 

_SAMPLERATE = {
    '1':   (44100, 48000, 32000),
    '2':   (22050, 24000, 16000),
    '2.5': (11025, 12000, 8000),
}

_CHANNEL_MODES = ("stereo", "joint stereo", "dual channel", "mono")
    
_CHANNEL_MODE_EXT_1__2 = ("4-31", "8-31", "12-31", "16-31") 
    
_CHANNEL_MODE_EXT = {
    '1': _CHANNEL_MODE_EXT_1__2,
    '2': _CHANNEL_MODE_EXT_1__2,
    '3': ("", "IS", "MS", "IS+MS")
}
    
_EMPHASES = ("none", "50/15 ms", "reserved", "CCIT J.17")

_SAMPLES_PER_FRAME = {
    '1': {
        '1': 384, '2': 1152, '3': 1152,
    },
    '2': {
        '1': 384, '2': 1152, '3': 576,
    },
    '2.5': {
        '1': 384, '2': 1152, '3': 576,
    },
}
       
_SLOTS = { '1' : 4, '2' : 1, '3' : 1 }

_SLOT_COEFFS_2__2_5 = { '1': 12, '2': 144, '3': 72 }
  
_SLOT_COEFFS = {
    '1': { '1': 12, '2': 144, '3': 144 },
    '2': _SLOT_COEFFS_2__2_5,
    '2.5': _SLOT_COEFFS_2__2_5,
}

def _check_header_sync_bits(bits):
    """Check if given bits has sync bits.
    
    @param bits: bits to check for sync bits.
    @type bits: int
    
    @raise mpegmeta.MpegHeaderException: Raised if bits does not contain sync 
        bits.
    
    """
    if (bits & 2047) != 2047:
        raise MpegHeaderException('Sync bits does not match.')
    
def _get_header_mpeg_version(bits):
    """Get MPEG version from header bits.
    
    @param bits: Two version bits in MPEG header.
    @type bits: int
    
    @return: MPEG Version, one of the following values: C{"2.5", "2", "1"}. 
    @rtype: string
    
    @todo: Ponder about the usefulness of this being string. Same with
        L{_get_header_layer}.
    
    @raise mpegmeta.MpegHeaderException: Raised when layer cannot be determined.
    
    """
    
    try:
        return _MPEG_VERSIONS[bits]
    except (KeyError, IndexError):
        raise MpegHeaderException('Unknown MPEG version.')
    
def _get_header_layer(bits):
    """Get layer from MPEG Header bits.
    
    @param bits: Two layer bits in MPEG header.
    @type bits: int
    
    @return: MPEG Layer, one of the following values: C{'1', '2', '3'}.
    @rtype: string
    
    @raise mpegmeta.MpegHeaderException: Raised when layer cannot be determined.
    
    """

    
    try:
        return _LAYERS[bits]
    except (KeyError, IndexError):
        raise MpegHeaderException('Unknown Layer version')
    
def _get_header_bitrate(mpeg_version, layer, bitrate_bits):
    """ Get bitrate by mpeg version, layer_bitsbitrate_bitstrate bits index.
    
    @param mpeg_version: Version of the MPEG, as returned by 
        L{_get_header_mpeg_version}
    @type mpeg_version: string
    
    @param layer: Layer of the MPEG as returned by L{_get_header_layer}.
    @type layer: string
    
    @param bitrate_bits: Four bits in MPEG header.
    @type bitrate_bits: int
    
    @return: Bitrate in kilobits per second.
    @rtype: int
    
    @raise mpegmeta.MpegHeaderException: Raised when bitrate cannot be
        determined.
    
    """
    
    # TODO: LOW: Free bitrate
    if bitrate_bits == 0:
        raise MpegHeaderException('Free bitrate is not implemented, sorry.') 
    
    try:
        return _BITRATE[mpeg_version][layer][bitrate_bits]
    except (KeyError, IndexError):
        raise MpegHeaderException('Bitrate cannot be determined.')

    
def _get_header_sample_rate(mpeg_version, bits):
    """Get sample rate by MPEG version and given MPEG Header sample rate bits.
    
    @param mpeg_version: Version of the MPEG, as returned by 
        L{_get_header_mpeg_version}
    @type mpeg_version: string
    
    @param bits: Sample rate bits in MPEG header.
    @type bits: int
    
    @return: Sample rate in Hz
    @rtype: int
    
    @raise mpegmeta.MpegHeaderException: Raised when sample rate cannot be
        determined.
    
    """

    try:
        return _SAMPLERATE[mpeg_version][bits]
    except (KeyError, TypeError, IndexError):
        raise MpegHeaderException('Sample rate cannot be determined.')
    
def _get_header_channel_mode(bits):
    """Get channel mode.
    
    @param bits: Mode bits in MPEG header.
    @type bits: int
    
    @return: Returns one of the following: C{"stereo"}, C{"joint stereo"}, 
        C{"dual channel"}, C{"mono"}. 
    @rtype: string
    
    @raise mpegmeta.MpegHeaderException: Raised if channel mode cannot be 
        determined.
    """
    
    
    try:
        return _CHANNEL_MODES[bits]
    except (IndexError, TypeError):
        raise MpegHeaderException('Channel channel_mode cannot be determined.')

def _get_header_channel_mode_ext(layer, bits):
    """Get channel mode extension.
    
    @param layer: Layer of the MPEG as returned by 
        L{_get_header_layer<mpegmeta._get_header_layer>}.
    @type layer: string
    
    @param bits: Extension mode bits in MPEG header.
    @type bits: int
    
    @rtype: string 
    @return: Channel extension mode. One of the following values: C{"4-31", 
        "8-31", "12-31", "16-31", "", "IS", "MS", "IS+MS"}
       
    @raise mpegmeta.MpegHeaderException: Raised if channel mode extension cannot 
        be determined.
        
    """

    try:
        return _CHANNEL_MODE_EXT[layer][bits]
    except (KeyError, TypeError, IndexError):
        raise MpegHeaderException('Channel mode ext. cannot be determined.')

def _get_header_emphasis(bits):
    """Get emphasis of audio.
    
    @param bits: Emphasis bits in MPEG header.
    @type bits: int
    
    @return: Returns emphasis, one of the following: C{"none", "50/15 ms", 
        "reserved", "CCIT J.17"}
    @rtype: string 
    
    @raise mpegmeta.MpegHeaderException: Raised when emphasis cannot be
        determined.
    
    """
    
    
    try:
        return _EMPHASES[bits]
    except (TypeError, IndexError): 
        raise MpegHeaderException('Emphasis cannot be determined.')

def _get_header_bytes(header_offset, chunk):
    """Unpacks MPEG Frame header bytes from chunk of data.
    
    Value can then be used to parse and verify the bits.
    
    @see: L{MPEGFrame.parse<mpegmeta.MPEGFrame.parse>}
    @see: L{MPEGFrame.find_and_parse<mpegmeta.MPEGFrame.find_and_parse>}
    
    @param header_offset: Position I{within a chunk} where to look for header 
        bytes.
    @type header_offset: int
    
    @param chunk: Chunk of data where to get header bytes.
    @type chunk: string
    
    @return: Header bytes. Used by L{MPEGFrame.parse<mpegmeta.MPEGFrame.parse>}.
    @rtype: int
    
    @raise mpegmeta.MpegHeaderEOFException: Raised when end of chunk was 
        reached.
    
    """
    # Get first four bytes
    header = chunk[header_offset:header_offset + 4]
    if len(header) != 4:
        raise MpegHeaderEOFException('End of chunk reached, header not found.')
    
    # Unpack 4 bytes (the header size)
    (header_bytes,) = struct.unpack(">I", header)
    return header_bytes

def _get_samples_per_frame(mpeg_version, layer):
    """Get samples per frame.
    
    @param mpeg_version: Version of the mpeg, as returned by 
        L{_get_header_mpeg_version}
    @type mpeg_version: string
    
    @param layer: Layer of the MPEG as returned by L{_get_header_layer}.
    @type layer: string
    
    @rtype: int
    @return: Samples per frame.
    
    @raise mpegmeta.MpegHeaderException: Raised if samples per frame cannot be 
        determined.
    
    """
    try:
        return _SAMPLES_PER_FRAME[mpeg_version][layer]
    except (IndexError):
        raise MpegHeaderException('Samples per frame cannot be determined.')
 

def _get_frame_size(mpeg_version, layer, sample_rate, bitrate, padding_size):
    """Get size.
    
    @param mpeg_version: Version of the MPEG, as returned by 
        L{_get_header_mpeg_version}
    @type mpeg_version: string
    
    @param layer: Layer of the MPEG as returned by L{_get_header_layer}.
    @type layer: string
    
    @param sample_rate: Sampling rate in Hz.
    @type sample_rate: int
    
    @param bitrate: Bitrate in kilobits per second.
    @type bitrate: int
    
    @param padding_size: Size of header padding. 1 or 0.
    @type padding_size: int
    
    @return: Frame size in bytes.
    @rtype: int
    
    @raise mpegmeta.MpegHeaderException: Raised when frame size cannot be 
        determined.
    
    """
    try:
        coeff = _SLOT_COEFFS[mpeg_version][layer]
        slotsize = _SLOTS[layer]
    except (IndexError, KeyError, TypeError):
        raise MpegHeaderException('Frame size cannot be determined.')
    
    bitrate_k = bitrate * 1000
    
    framesize = int((coeff * bitrate_k / sample_rate) + padding_size) * slotsize
    if framesize <= 0:
        raise MpegHeaderException('Frame size cannot be calculated.')
    return framesize

def _get_filesize(file):
    """Get file size from file object.
    
    @param file: File object, returned e.g. by L{open<open>}.
    @type file: file object
    
    @return: File size in bytes.
    @rtype: int
    
    """
    offset = file.tell()
    file.seek(0, 2)
    filesize = file.tell()
    file.seek(offset)
    return filesize

def _get_vbr_bitrate(mpeg_size, sample_count, sample_rate):
    """Get average bitrate of VBR file.
    
    @param mpeg_size: Size of MPEG in bytes.
    @type mpeg_size: number
    
    @param sample_count: Count of samples, greater than C{0}.
    @type sample_count: number

    @param sample_rate: Sample rate in Hz.
    @type sample_rate: number
    
    @return: Average bitrate in kilobits per second.
    @rtype: float
    
    """
    bytes_per_sample = float(mpeg_size) / float(sample_count)
    bytes_per_second = bytes_per_sample * float(sample_rate)
    bits_per_second = bytes_per_second * 8
    return bits_per_second / 1000

def _get_sample_count(frame_count, samples_per_frame):
    """Get sample count.
    
    @param frame_count: Count of frames.
    @type frame_count: int
    
    @param samples_per_frame: Samples per frame.
    @type samples_per_frame: int
    
    @return: Sample count
    @rtype: int
    
    """
    return frame_count * samples_per_frame

def _get_duration_from_sample_count(sample_count, sample_rate):
    """Get MPEG Duration.
    @param sample_count: Count of samples.
    @type sample_count: int
    
    @param sample_rate: Sample rate in Hz.
    @type sample_rate: int
    
    @return: Duration of MPEG, with second accuracy.
    @rtype: datetime.timedelta
    
    """
    return timedelta(seconds=int(round(sample_count / sample_rate)))
    
def _get_duration_from_size_bitrate(mpeg_size, bitrate):
    """Calculate duration from constant bitrate and MPEG Size.
    
    @param mpeg_size: MPEG Size in bytes.
    @type mpeg_size: int
    
    @param bitrate: Bitrate in kilobits per second, for example 192.
    @type bitrate: int
    
    @raise mpegmeta.MpegHeaderException: Raised if duration cannot be 
        determined.
    
    @return: Duration of the MPEG, with second accuracy.
    @rtype: datetime.timedelta
    
    """
    try:
        return timedelta(seconds=(mpeg_size / (bitrate * 1000) * 8))
    except ZeroDivisionError:
        raise MpegHeaderException('Duration cannot be determined.')
    
def _get_vbr_frame_size(mpeg_size, frame_count):
    """Get VBR average frame size.
    
    @param mpeg_size: Size of MPEG in bytes.
    @type mpeg_size: int
    
    @param frame_count: Count of frames in MPEG, must be bigger than C{0}.
    @type frame_count: int
    
    @return: Average frame size.
    @rtype: number
    
    """
    return mpeg_size / frame_count
    
def _chunked_reader(file, chunk_size=None, start_position= -1,
                    max_chunks= -1, reset_offset=True):
    """Reads file in chunks for performance in handling of big files.
    
    @param file: File to be read, e.g. returned by L{open<open>}.
    @type file: file object
    
    @keyword chunk_size: Read in this sized chunks.
    @type chunk_size: int
    
    @keyword start_position: Start position of the chunked reading.
    @type start_position: int
    
    @keyword max_chunks: Maximum amount of chunks, C{-1} means I{infinity}.
    @type max_chunks: int
    
    @keyword reset_offset: Resets the offset of seeking between chunks. Used
        to correct the cursor position when file seeks / reads occurs inside 
        chunk iteration.
    @type reset_offset: bool
    
    @return: Generator of file chunks as tuples of chunk offset and chunk.
    @rtype: generator of (chunk_offset, chunk)
    
    """
    if start_position != -1:
        file.seek(start_position)
        
    offset = file.tell()
    chunk = ""
    chunk_size = chunk_size or DEFAULT_CHUNK_SIZE 
            
    i = 0
    while True:
        if 0 < max_chunks <= i:
            break
        
        if reset_offset:
            file.seek(offset + len(chunk))
        
        offset = file.tell()
        chunk = file.read(chunk_size)
        if not chunk:
            break
        yield (offset, chunk)
        i += 1

def _find_all_overlapping(string, occurrence):
    """Find all overlapping occurrences.
    
    @param string: String to be searched.
    @type string: string
    
    @param occurrence: Occurrence to search.
    @type occurrence: string
    
    @return: generator yielding I{positions of occurence}
    @rtype: generator of int
    
    """
    found = 0
    
    while True:
        found = string.find(occurrence, found)
        if found != -1:
            yield found
        else:
            return
        
        found += 1

# TODO: HIGH: Wrap Open and Close.
def _wrap_open_close(function, object, filename, mode='rb',
                    file_handle_name='_file'):
    """Wraps the objects file handle for execution of function.
    
    @param function: Function to be executed during file handle wrap.
    @type function: callable
    
    @param object: Object having the file handle.
    @type object: object
    
    @param filename: Filename opened.
    @type filename: string
    
    @keyword mode: Opening mode.
    @type mode: string
    
    @keyword file_handle_name: Name of the instance variable in object.
    @type file_handle_name: string
    
    @return: New function which being run acts as wrapped function call.
    @rtype: function
    
    """
    file_handle = getattr(object, file_handle_name)
    
    if (file_handle is not None) and (not file_handle.closed):
        function()
        return
    
    new_file_handle = open(filename, mode)
    setattr(object, file_handle_name, new_file_handle)
    function()
    new_file_handle.close()
        
def _join_iterators(iterable1, iterable2):
    """Joins list and generator.
    
    @param iterable1: List to be appended.
    @type iterable1: Generator
    
    @param iterable2: Generator to be appended.
    @type iterable2: generator
    
    @return: Generator yielding first iterable1, and then following iterable2.
    @rtype: generator
    
    """
    for item1 in iterable1:
        yield item1
        
    for item2 in iterable2:
        yield item2
        
def _genmin(generator, min):
    """Ensures that generator has min amount of items left.
    
    @param generator: Generator to be ensured.
    @type generator: generator
    
    @param min: Minimum amount of items in generator.
    @type min: int
    
    @raise ValueError: Raised when minimum is not met.
    
        >>> def yrange(n): # Note that xrange doesn't work, requires next()
        ...     for i in range(n):
        ...         yield i
        ... 
        >>> _genmin(yrange(5), min=4) #doctest: +ELLIPSIS
        <generator object _join_iterators at ...>
        >>> _genmin(yrange(5), min=5) #doctest: +ELLIPSIS
        <generator object _join_iterators at ...>
        >>> _genmin(yrange(5), min=6)
        Traceback (most recent call last):
          ...
        ValueError: Minimum amount not met.
        >>> 
        
    """
    cache = []
    for index in range(min): #@UnusedVariable
        try:
            cache.append(generator.next())
        except StopIteration:
            raise ValueError('Minimum amount not met.')
        
    return _join_iterators(cache, generator)

def _genmax(generator, max):
    """Ensures that generator does not exceed given max when yielding.
    
    For example when you have generator that goes to infinity, you might want to
    instead only get 100 first instead.
    
    @param generator: Generator
    @type generator: generator

    @param max: Maximum amount of items yields.
    @type max: int
    
    @rtype: generator
    @return: Generator limited by max.
    
        >>> list(_genmax(xrange(100), max=3))
        [0, 1, 2]
        
    """
    for index, item in enumerate(generator):
        yield item
        if index + 1 >= max:
            return
        
def _genlimit(generator, min, max):
    """Limit generator I{item count} between min and max.
    
    @param generator: Generator
    @type generator: generator

    @param min: Minimum amount of items in generator.
    @type min: int, or None
    
    @param max: Maximum amount of items.
    @type max: int, or None
    
    @note: If both are C{None} this returns the same generator.
    @raise ValueError: Raised when minimum is not met.
    
    """
    if (min is None) and (max is None):
        return generator
    
    if min is not None:
        generator = _genmin(generator, min)
        
    if max is not None:
        generator = _genmax(generator, max)
        
    return generator
        
class MPEGFrameBase(object):
    """MPEG frame base, should not be instated, only inherited.
    
    Variables defined here are constant through out the frames of L{MPEG}.
    
    """
    def __init__(self):
        self.is_private = False
        """Is private?
        @type: bool 
        """
        
        self.is_copyrighted = False
        """Is copyrighted?
        @type: bool
        """
        
        self.samples_per_frame = None
        """Samples per frame
        @type: int
        """ 
        
        self.is_original = False
        """Is original?
        @type: bool 
        """
        
        self.is_protected = False
        """Is protected?
        @type: bool 
        """
    
        self._padding_size = 0
        """Padding size of header.
        @type: int""" 
        
        self.version = None
        """MPEG Version.
        @type: string
        """
        
        self.layer = None
        """Layer number.
        @type: string 
        """
        
        self.sample_rate = None
        """Sampling rate in Hz.
        @type: int 
        """
        
        self.channel_mode = None
        """Channel mode.
        @type: string 
        """
        
        self.channel_mode_extension = None
        """Channel mode extension.
        @type: string 
        """
        
        self.emphasis = None
        """Emphasis.
        @type: string
        """
        
        self.offset = None
        """Offset of the MPEG Frame header I{in file}.
        
        Notice that this offset points to I{beginning of header's first byte}, 
        and is I{not} offset of beginning of data.
        
        @type: int
        
        """
        
class MPEGFrame(MPEGFrameBase):
    """MPEG I{Frame} meta data."""
    
    def __init__(self):
        super(MPEGFrame, self).__init__()
        
        self.bitrate = None
        """Bitrate in kilobits, for example 192.
        
        In the MPEG audio standard there is a X{free bitrate} format described.
        This free format means that the file is encoded with a constant bitrate,
        which is not one of the predefined bitrates. Only very few decoders can
        handle those files.
        
        @note: In rare X{free bitrate} case the bitrate mentioned in frame is 
            C{0}.
        @type: int
        
        """
        
        self.samples_per_frame = None
        """Samples per frame.
        @type: int
        """
        
        self.size = None
        """Frame size in bytes.
        
        @note: Includes the header (4) bytes.
        @note: Bitrate may be C{0}, thus frame size is C{None} and cannot be 
            calculated from I{one frame}, in that case the frame size, and
            bitrate requires second frame measurement.
        @type: int, or None
        
        """

    def get_forward_iterator(self, file, chunk_size=None):
        """Get forward iterator from this position.
        
        @param file: File object
        @type file: file object
        
        @param chunk_size: Chunked reading size, C{None} defaults to 
            L{DEFAULT_CHUNK_SIZE}.
        @type chunk_size: int
        
        @note: First frame of generator is I{next} frame.
        @return: Generator that iterates forward from this frame.
        @rtype: generator of L{MPEGFrame <mpegmeta.MPEGFrame>}
        
        """
        # TODO: LOW: Free bitrate.
        next_frame_offset = self.offset + self.size
        chunks = _chunked_reader(file, start_position=next_frame_offset,
                                chunk_size=(chunk_size or DEFAULT_CHUNK_SIZE))
        return MPEGFrame.parse_consecutive(next_frame_offset, chunks)
    
#    def get_backward_iterator(self, file):
#        # TODO: LOW: Backward iterator
#        raise NotImplementedError('Backward iteration not implemented!')
    
    @classmethod
    def find_and_parse(cls, file, max_frames=3, chunk_size=None, #IGNORE:R0913
                       begin_frame_search= -1, lazily_after=1,
                       max_chunks= -1, max_consecutive_chunks= -1): 
        """Find and parse from file.
        
        @param file: File object being searched.
        @type file: file object
        
        @keyword max_frames: Maximum of frames returned. Defaults to C{3}. 
            C{None} means give all frames as lazy generator. 
        @type max_frames: int, or None
        
        @keyword chunk_size: Size of chunked reading. Defaults to 
            L{DEFAULT_CHUNK_SIZE}, minimum C{4}.
        @type chunk_size: int
        
        @keyword begin_frame_search: Begin frame search from this position in 
            file. Defaults to C{-1}, meaning continue where file pointer has
            left.
        @type begin_frame_search: int 
        
        @keyword lazily_after: Check also next header(s), before becoming 
            lazy generator. Defaults to C{1}.
        @type lazily_after: int
        
        @keyword max_chunks: Maximum amount of chunks the chunked reader can 
            yield. C{-1} means infinity, and can be looped to end of file.
        @type max_chunks: int
        
        @keyword max_consecutive_chunks: Maximum of I{consecutive} chunks in 
            returned lazy generator. C{-1} means infinity, and can be looped to
            end of file.
        @type max_consecutive_chunks: int
        
        """
        chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
        
        chunk_size = max(chunk_size, 4)
        chunks = _chunked_reader(file, chunk_size=chunk_size,
                                start_position=begin_frame_search,
                                max_chunks=max_chunks)

        for chunk_offset, chunk in chunks:
            for found in _find_all_overlapping(chunk, chr(255)):
                consecutive_chunks = \
                    _chunked_reader(file,
                                    chunk_size=chunk_size,
                                    start_position=chunk_offset + found,
                                    max_chunks=max_consecutive_chunks)
                
                frames = MPEGFrame.parse_consecutive(chunk_offset + found,
                                                     consecutive_chunks) 
                try:
                    return _genlimit(frames, lazily_after + 1, max_frames)
                except ValueError:
                    pass
        return []
    
    @classmethod
    def parse_consecutive(cls, header_offset, chunks):
        """Parse consecutive MPEG Frame headers. 
        
        Parses from given position until header parsing error, or end of chunks.
        
        @param header_offset: Header offset I{within a file}.
        @type header_offset: int
        
        @param chunks: Generator yielding more chunks when I{End of Chunk} is 
            reached.
        @type chunks: generator, or list
        
        @return: Generator yielding MPEG frames.
        @rtype: generator of L{MPEGFrames<mpegmeta.MPEGFrame>}
        
        @see: L{_chunked_reader<mpegmeta._chunked_reader>}
        
        """
        previous_mpegframe = None
        previous_mpegframe_offset = None
        previous_chunk = ""
        next_mpegframe_offset = header_offset      
        
        for next_chunk_offset, next_chunk in chunks:
            # Get 4 bytes from previous chunk
            previous_chunk_end = previous_chunk[-4:]
            
            # Join the 4 bytes, if there were any, to tested chunk
            chunk = previous_chunk_end + next_chunk
            chunk_offset = next_chunk_offset - len(previous_chunk_end)
            
            # Yield all frames in chunk 
            while True:
                if (previous_mpegframe is not None) and \
                   (previous_mpegframe_offset is not None):
                    if previous_mpegframe.size is None:
                        return
                        # TODO: LOW: Free bitrate, you must search for the
                        # second frame.
                    next_mpegframe_offset = previous_mpegframe_offset + \
                                            previous_mpegframe.size
                next_mpegframe = None
                next_header_offset = next_mpegframe_offset - chunk_offset
                
                # Get header bytes within chunk
                try:
                    header_bytes = _get_header_bytes(next_header_offset, chunk)
                except MpegHeaderEOFException:
                    # We need next chunk, end of this chunk was reached
                    break
                
                # Parse and append if parseable
                try:
                    next_mpegframe = MPEGFrame.parse(header_bytes)
                except MpegHeaderException:
                    return
                else:
                    # Frame was parsed successfully
                    next_mpegframe.offset = next_mpegframe_offset
                    yield next_mpegframe
                
                previous_mpegframe_offset = next_mpegframe_offset
                previous_mpegframe = next_mpegframe
            previous_chunk = next_chunk
        return
   
    @classmethod
    def parse(cls, bytes):
        """Tries to create MPEG Frame from given bytes.
        
        @param bytes: MPEG Header bytes. Usually obtained with 
            L{_get_header_bytes()<mpegmeta._get_header_bytes>}
        @type bytes: int
        
        @rtype: L{MPEGFrame<mpegmeta.MPEGFrame>}
        @return: MPEG Frame
        
        @raise mpegmeta.MpegHeaderException: Raised if MPEG Frame cannot be 
            parsed.
            
        """
        # TODO: LOW: CRC, verify and parse.
        # http://www.codeproject.com/KB/audio-video/mpegaudioinfo.aspx#CRC
        
        # Header synchronization bits
        _check_header_sync_bits((bytes >> 21) & 2047) 
        
        # Header parseable information
        mpeg_version_bits = (bytes >> 19) & 3    
        layer_bits = (bytes >> 17) & 3  
        protection_bit = (bytes >> 16) & 1  
        bitrate_bits = (bytes >> 12) & 15 
        samplerate_bits = (bytes >> 10) & 3  
        padding_bit = (bytes >> 9) & 1  
        private_bit = (bytes >> 8) & 1  
        mode_bits = (bytes >> 6) & 3  
        mode_extension_bits = (bytes >> 4) & 3  
        copyright_bit = (bytes >> 3) & 1                              
        original_bit = (bytes >> 2) & 1
        emphasis_bits = (bytes >> 0) & 3

        self = MPEGFrame()
        
        self.version = _get_header_mpeg_version(mpeg_version_bits)
        self.layer = _get_header_layer(layer_bits)
        self.bitrate = _get_header_bitrate(self.version, self.layer,
                                           bitrate_bits)
        self.sample_rate = _get_header_sample_rate(self.version,
                                                   samplerate_bits)
        self.channel_mode = _get_header_channel_mode(mode_bits)
        self.channel_mode_extension = \
            _get_header_channel_mode_ext(self.layer, mode_extension_bits)
        self.emphasis = _get_header_emphasis(emphasis_bits)
        
        self._padding_size = padding_bit
        self.is_private = private_bit == 1
        self.is_copyrighted = copyright_bit == 1
        self.is_original = original_bit == 1
        self.is_protected = protection_bit == 1
        
        # Non-header parseable information
        self.samples_per_frame = _get_samples_per_frame(self.version,
                                                        self.layer)
        self.size = _get_frame_size(self.version, self.layer, self.sample_rate,
                                    self.bitrate, self._padding_size)
        return self
    
class MPEGFrameIterator(object):
    """MPEG Frame iterator, for lazy evaluation."""
    def __init__(self, mpeg, begin_frames, end_frames):
        """Create MPEG frame iterator.
        
        @param mpeg: MPEG Which frames are to be iterated over.
        @type mpeg: L{MPEG<mpegmeta.MPEG>}
        
        @param begin_frames: First frames of MPEG.
        @type begin_frames: function giving list of L{MPEGFrame}
         
        @param end_frames: End frames of MPEG. 
        @type end_frames: function giving list of L{MPEGFrame}
        
        """
        self.mpeg = mpeg
        """MPEG which frames are iterated.
        @type: L{MPEG<mpegmeta.MPEG>}
        """
        
        self._begin_frames = begin_frames
        """Begin frames.
        @type: list of L{MPEGFrame<mpegmeta.MPEGFrame>}
        """
        
        self._end_frames = end_frames
        """End frames.
        @type: list of L{MPEGFrame<mpegmeta.MPEGFrame>}, or None
        """
        
        self._has_parsed_all = False
        """Has parsing all occurred?
        @type: bool 
        """
        
        self._has_parsed_beginning = not callable(self._begin_frames)
        """Has parsing beginning occurred?
        @type: bool 
        """
        
        self._has_parsed_ending = not callable(self._end_frames)
        """Has parsing end occurred?
        @type: bool 
        """
    
    def __len__(self):
        pass
    
    def parse_all(self, force=False):
        """Parse all frames.
        
        @see: L{MPEG.parse_all}
        
        """
        # TODO: LOW: How do we deal corrupted MPEG files? 
        # Where some frames are misplaced, etc?
        
        if self._has_parsed_all and not force:
            # TODO: DEBUG!
            raise NotImplementedError('This should not happen, ever!')
            # return
        
        avg_bitrate = 0
        index = -1
        for index, frame in enumerate(self):
            avg_bitrate += frame.bitrate
        
        frame_count = index + 1
        bitrate = avg_bitrate / frame_count
        
        # Set MPEG values
        self.mpeg.frame_count = frame_count
        self.mpeg.bitrate = bitrate
        
        # Set has parsed all
        self._has_parsed_all = True
    
#    def __reversed__(self):
#        # TODO: LOW: Backward iterator
#        pass
    
    def __iter__(self):
        # Join begin frames, and generator yielding next frames from that on.
        
        # TODO: ASSUMPTION: Iterating frames uses parsing all chunk size.
        return _join_iterators(\
                 self._begin_frames,
                 self._begin_frames[-1].\
                    get_forward_iterator(self.mpeg._file,
                                         chunk_size=PARSE_ALL_CHUNK_SIZE))
    
    def __getitem__(self, key):
        # TODO: LOW: Following is misleading, _begin_frames and _end_frames does
        # not include all keys, works for now.
        if key < 0:
            # Lazy evaluate
            if callable(self._end_frames):
                self._end_frames = list(self._end_frames())
                self._has_parsed_ending = True
                
            return self._end_frames[key]
        else:
            # Lazy evaluate
            if callable(self._begin_frames):
                self._begin_frames = list(self._begin_frames())
                self._has_parsed_beginning = True
                
            return self._begin_frames[key]

class MPEG(MPEGFrameBase):
    """
    Parses MPEG file meta data.
    
    Uses Xing and VBRI headers if neccessary, for better performance with VBR
    files. VBR files that doesn't have those headers the file must parse all
    frames. 
    
    MPEG object is lazy
    ===================
    
    Laziness works when ...
    -----------------------
    
    Laziness works for the cases where we don't need to parse all frames. Being
    lazy for MPEG object means that it has passed at least:
    
     1. L{is mpeg test <mpegmeta.MPEG._is_mpeg_test>} returned without exception.
     2. L{beginning parsing <mpegmeta.MPEG._parse_beginning>} is done.
     
    Normal initialization of MPEG object does these things, user of this class 
    does not need to care about these. All MPEG objects are lazy, when they have
    been created without exceptions.
    
    Being lazy now, means doing the work later
    ------------------------------------------
    
    There are getters and setters only for those properties which might invoke 
    parsing all frames. Getters are the lazy ones. If the possibility of parsing 
    all frames is out of question, you should use getters directly, they have 
    option to prevent parsing all frames.
    
    By using properties we can ensure that all properties and instance variables
    returns I{meaningful value} instead of C{None}. To write this as a simple 
    rule that lazy getters should follow:
    
     - I{All getters should return meaningful value with B{default arguments}}.
     
    That is it! No errors should be raised, no C{None}'s should be given, just
    the meaningful value. If getter needs to parse to get the meaningful value,
    that is what it does. Currently there are only two major things that the
    MPEG object does lazily, when really required:
    
     - Parse ending of file
     - Parse all frames
    
    For the end user of this API this is convinient, it might not care if the 
    file is VBR, CBR, or what ever. For example if one cares only about the 
    duration of MPEG: 
    
    With creating the MPEG instance object I{we ensure} - did not yield parsing 
    exception - that by running C{mpeg.duration} the user gets the duration, 
    even if as worst case scenario it might require parsing all frames.
    
    On the other hand, if the user doesn't want to parse all frames, and is 
    satisfied for C{None} for the cases where it cannot be calculated without 
    full parsing, the API gives you possibility to use appropriate getters e.g. 
    L{_get_duration <mpegmeta.MPEG._get_duration>} with arguments to adjust for
    the case.
    
    @note: This does not provide any kind of updating or playing the mpeg 
    files, only reading out meta data.
    
    """
    def __init__(self, file, begin_start_looking=0, ending_start_looking=0,
                 mpeg_test=True):
        """Parses the MPEG file.
        
        @todo: If given filename, create file and close it always automatically 
            when not needed.
        @todo: C{parse_all_frames} is not implemented!
        
        @param file: File handle returned e.g. by open()
        @type file: file
        
        @param begin_start_looking: Start position of MPEG header search. For
            example if you know that file has ID3v2, it is adviced to give the 
            size of ID3v2 tag to this field.
            
            Value I{must be equal or lesser than} (<=) the beginning of MPEG. If
            the given value exceeds the first header, the given MPEG might be
            incorrect.
        @type begin_start_looking: int
        
        @param ending_start_looking: End position of MPEG I{relative to end of 
            file}. For example if you know that file has ID3v1 footer, give 
            C{128}, the size of ID3v1, this ensures that we can I{at least} skip
            over that.
            
            Value I{must be equal or lesser than} (<=) end of the last 
            MPEG header.
            
        @type ending_start_looking: int
        
        @param mpeg_test: Do mpeg test first before continuing with parsing the 
            beginning. This is useful especially if there is even slight 
            possibility that given file is not MPEG, we can rule them out fast. 
        @type mpeg_test: bool
        
        @raise mpegmeta.MpegHeaderException: Raised if header cannot be found.
        
        """
        super(MPEG, self).__init__()
        
        self._file = file
        """File object.
        @type: file object
        """
        
        self.is_vbr = False
        """Is variable bitrate?
        @type: bool
        """
        
        self.filesize = _get_filesize(file)
        """Filesize in bytes.
        @type: int
        """
        
        self.xing = None
        """XING Header, if any.
        @type: L{XING<mpegmeta.XING>}, or None
        """
        
        self.vbri = None
        """VBRI Header, if any.
        @type: L{VBRI<mpegmeta.VBRI>}, or None
        """
        
        self.frames = None
        """All MPEG frames.
        @type: iterable of L{MPEGFrames<mpegmeta.MPEGFrame>}
        """
        
        self._frame_count = None
        self._frame_size = None
        self._size = None
        self._duration = None
        self._bitrate = None
        self._begin_start_looking = begin_start_looking
        self._ending_start_looking = ending_start_looking
        
        test_frames = []
        if mpeg_test:
            test_frames = list(self._is_mpeg_test())
        
        # Parse beginning of file, when needed. In reality, this is run every 
        # time init is run. The _set_mpeg_details, XING, VBRI uses the first 
        # frames so we cannot make this very lazy. 
        begin_frames = lambda: self._parse_beginning(begin_start_looking)
        
        # Parse ending of file, when needed.
        end_frames = lambda: self._parse_ending(ending_start_looking)
        
        # Creates frame iterator between begin and end frames.
        self.frames = MPEGFrameIterator(self, begin_frames, end_frames)
        
        # Set MPEG Details
        self._set_mpeg_details(self.frames[0], test_frames)
        
        # Parse VBR Headers if can be found.
        self._parse_xing()
        self._parse_vbri()
        
    def _get_size(self, parse_all=False, parse_ending=True):
        """MPEG Size getter.
        
        @rtype: int, or None
        
        """
        if self._size is not None:
            return self._size
        
        if parse_ending: 
            # 100% accurate size, if parsing ending did indeed return frame from
            # same MPEG:
            self.size = self.frames[-1].offset + self.frames[-1].size - \
                        self.frames[0].offset
        else:
            # TODO: NORMAL: Estimation of size Following might be a good enough
            # for 99% of time, maybe it should be default? A biggest risk is
            # that files with a *huge* footer will yield totally inaccurate
            # values, is that risk too big?
            #
            # Should we choose a higher accuracy over performance with 99% of 
            # cases? 
            self.size = self.filesize - self._ending_start_looking - \
                        self.frames[0].offset
        
        # TODO: LOW: parse_all in here is redundant, parse_ending gives 100%
        # accurate.
        if parse_all:
            self.frames.parse_all()
            
        return self._size
        
    def _set_size(self, value):
        """MPEG Size setter."""
        self._size = value
    
    def _get_sample_count(self, parse_all=False, parse_ending=True):
        """Sample count getter.
        
        @rtype: int, or None
        
        """      
        frame_count = self._get_frame_count(parse_all=parse_all,
                                            parse_ending=parse_ending)
        if frame_count is not None:  
            return self.frame_count * self.samples_per_frame
        return None
    
    def _get_bitrate(self, parse_all=True):
        """Bitrate getter.
        
        @rtype: int, float, or None
        
        """
        if self._bitrate is not None:
            return self._bitrate
        
        if self.is_vbr:
            sample_count = self._get_sample_count(parse_all)
            mpeg_size = self._get_size()
            self.bitrate = _get_vbr_bitrate(mpeg_size, sample_count,
                                            self.sample_rate)
            
        return self._bitrate
    
    def _set_bitrate(self, value):
        """Bitrate setter."""
        self._bitrate = value
    
    def _get_frame_count(self, parse_all=False, parse_ending=True):
        """Frame count getter.
        
        @rtype: int, or None
        
        """
        if self._frame_count is not None:
            return self._frame_count
        
        if not self.is_vbr:
            # CBR
            mpeg_size = self._get_size(parse_all=parse_all,
                                       parse_ending=parse_ending)
            first_frame = self.frames[0]
            unpadded_frame_size = first_frame.size - first_frame._padding_size
            # unpadded_frames = float(self.size) / float(unpadded_frame_size)
            
            padded_frame_size = unpadded_frame_size + 1
            padded_frames = float(mpeg_size) / float(padded_frame_size)
            
            # TODO: NORMAL: Estimation of frame_count:
            # it seems to be either this:
            self._frame_count = int(math.ceil(padded_frames))
            # or this:
            #self._frame_count = int(unpadded_frames)
            # now how can we guess which one?
            
            # print unpadded_frames, padded_frames
            
            # Average it aint:
            #self._frame_count = int(round((unpadded_frames + padded_frames) / \
            #                    float(2)))
        else:
            # VBR
            self.frames.parse_all()
        #raise NotImplementedError('Frame count not yet lazy.')
        return self._frame_count
    
    def _set_frame_count(self, value):
        """Frame count setter."""
        self._frame_count = value
        
    def _get_frame_size(self, parse_all=True):
        """Frame size getter.
        
        @rtype: int, or None
        
        """
        if self._frame_size is not None:
            return self._frame_size
        
        if not self.is_vbr:
            # CBR
            self.frame_size = self.frames[0].size
        else:
            # VBR
            frame_count = self._get_frame_count()
            mpeg_size = self._get_size()
            self.frame_size = _get_vbr_frame_size(mpeg_size, frame_count)
            
        return self._frame_size
    
    def _set_frame_size(self, value):
        """Frame size setter."""
        self._frame_size = value
    
    def _get_duration(self, parse_all=True):
        """Duration getter.
        
        @rtype: datetime.timedelta, or None
        
        """
        if self._duration is not None:
            return self._duration
        
        if not self.is_vbr:
            # CBR
            sample_count = self._get_sample_count(parse_all=False,
                                                  parse_ending=True)
            if sample_count is not None:
                self.duration = \
                    _get_duration_from_sample_count(sample_count,
                                                    self.sample_rate)
#            mpeg_size = self._get_size()
#            bitrate = self._get_bitrate(parse_all)
#            if (bitrate is not None) and (mpeg_size is not None):
#                self.duration = \
#                    _get_duration_from_size_bitrate(mpeg_size=self.size, 
#                                                    bitrate=self.bitrate)
        else:
            # VBR
            sample_count = self._get_sample_count(parse_all)
            if sample_count is not None:
                self.duration = \
                    _get_duration_from_sample_count(sample_count,
                                                    self.sample_rate)
                
        return self._duration
    
    def _set_duration(self, value):
        """Duration setter."""
        self._duration = value
    
    size = property(_get_size, _set_size)
    """MPEG Size in bytes.
    
    @note: May start parsing of all frames.
    @note: May start parsing of beginning frames.
    @note: May start parsing of ending frames.
    @type: int 
    
    """
    
    sample_count = property(_get_sample_count)
    """Count of samples in MPEG.
    
    @note: May start parsing of all frames. 
    @type: int
    
    """
    
    frame_size = property(_get_frame_size, _set_frame_size)
    """Frame size in bytes.
     
    For VBR files this is I{average frame size}.
    @note: May start parsing of all frames.
    @type: int 
    
    """
    
    bitrate = property(_get_bitrate, _set_bitrate)
    """Bitrate of the I{file} in kilobits per second, for example 192.
    
    For VBR files this is I{average bitrate} returned as C{float}.
    @note: May start parsing of all frames.
    @type: int, or float
    
    """
        
    frame_count = property(_get_frame_count, _set_frame_count)
    """Count of frames in MPEG.
    
    @note: May start parsing of all frames.
    @type: int
    
    """
    
    duration = property(_get_duration, _set_duration)
    """Duration.
    
    @note: May start parsing of all frames.
    @type: datetime.timedelta
    
    """
    
    def _parse_xing(self):
        """Tries to parse and set XING from first mpeg frame.
        @see: L{MPEG.xing<mpegmeta.MPEG.xing>}
        @see: L{XING<mpegmeta.XING>}
        
        """
        try:
            self.xing = XING.find_and_parse(self._file, self.frames[0].offset)
        except XINGHeaderException:
            pass  
        else:
            VBRHeader.set_mpeg(self, self.xing)
            
    def _parse_vbri(self):
        """Tries to parse and set VBRI from first mpeg frame.
        @see: L{MPEG.vbri<mpegmeta.MPEG.vbri>}
        @see: L{VBRI<mpegmeta.VBRI>}
        
        """
        # Tries to parse VBRI Header in first mpeg frame.
        try:
            self.vbri = VBRI.find_and_parse(self._file, self.frames[0].offset)
        except VBRIHeaderException:
            pass  
        else:
            VBRHeader.set_mpeg(self, self.vbri)

                
    def _is_mpeg_test(self, test_position=None):
        """Test that the file is MPEG.
        
        Validates that from middle of the file we can find three valid 
        consecutive MPEG frames. 
        
        @raise mpegmeta.MpegHeaderException: Raised if MPEG frames cannot be 
            found.
            
        @return: List of test MPEG frames.
        @rtype: list
        
        """
        # The absolute theoretical maximum frame size is 2881 bytes: 
        #   MPEG 2.5 Layer II, 8000 Hz @ 160 kbps, with a padding slot.
        #  
        # To get three consecutive headers we need (in bytes):
        #   (Max Frame Size + Header Size) * (Amount of consecutive frames + 1)
        # 
        # This calculation yields (2881+4)*4 = 11 540, which I decided to round
        # to (2^14 = 16 384)
        
        # TODO: LOW: Some people use random position in the middle, but why?
        #
        # If test position is not given explicitely it is assumed to be at the
        # middle start and end of looking.
        if test_position is None:
            looking_length = self.filesize - self._ending_start_looking - \
                             self._begin_start_looking
            test_position = self._begin_start_looking + \
                            int(0.5 * looking_length)
             
        return MPEGFrame.find_and_parse(file=self._file,
                                        max_frames=3,
                                        chunk_size=16384,
                                        begin_frame_search=test_position,
                                        lazily_after=2,
                                        max_chunks=1)
                
    def _set_mpeg_details(self, first_mpegframe, mpegframes):
        """Sets details of I{this} MPEG from the given frames.
        
        Idea here is that usually one or multiple mpeg frames represents single 
        MPEG file with good probability, only if the file is VBR this fails.
        
        @param first_mpegframe: First MPEG frame of the file.
        @type first_mpegframe: L{MPEGFrame<mpegmeta.MPEGFrame>}
        
        @param mpegframes: List of MPEG frames, order and position does not 
            matter, only thing matters are the fact they are from same MPEG. 
            These are used determine the VBR status of the file. 
        @type mpegframes: list of L{MPEGFrames<mpegmeta.MPEGFrame>}
        
        """
        # Copy values of MPEG Frame to MPEG, where applicable.
        self.is_copyrighted = first_mpegframe.is_copyrighted
        self.is_original = first_mpegframe.is_original
        self.is_private = first_mpegframe.is_private
        self.is_protected = first_mpegframe.is_protected
        self.offset = first_mpegframe.offset
        self.channel_mode = first_mpegframe.channel_mode
        self.channel_mode_extension = first_mpegframe.channel_mode_extension
        self.emphasis = first_mpegframe.emphasis
        self.sample_rate = first_mpegframe.sample_rate
        self.samples_per_frame = first_mpegframe.samples_per_frame
        self.frame_size = first_mpegframe.size
        self.bitrate = first_mpegframe.bitrate

        # If no testing frames was given, resort to getting last three frames.
        if len(mpegframes) == 0:
            mpegframes = self.frames[-3:]
        
        # If any of the bitrates differ, this is most likely VBR. 
        self.is_vbr = any(mpegframe.bitrate != first_mpegframe.bitrate \
                          for mpegframe in mpegframes)
        
        if self.is_vbr:
            self.bitrate = None 
            self.frame_size = None
            self.frame_count = None
    
    def parse_all(self, force=False):
        """Parse all frames.
                
        By parsing all frames, MPEG is ensured to populate following fields 
        with I{accurate values}:
        
            - C{frame_count}
            - C{bitrate}
            
        Essentially all properties, and variables of MPEG should be as accurate
        as possible after running this.
            
        @param force: Force re-parsing all frames. Defaults to C{False}.
        @type force: bool
        
        """
        # Semantically, I think, only frames should have parse_all() only, thus
        # this MPEG.parse_all() exists purely because user of this API should
        # not need to guess the "extra" semantics of frames and MPEG.
        self.frames.parse_all(force=force)
    
    def _parse_beginning(self, begin_offset=0, max_frames=6):
        """Parse beginning of MPEG.
        
        @keyword begin_offset: Beginning offset, from beginning of file.
        @type begin_offset: int
        
        @keyword max_frames: Maximum of frames to be parsed, and returned 
            forward from first found frame. C{-1} means I{infinity}, and can be 
            looped to end of file.
        @type max_frames: int
        
        @return: List of MPEG frames.
        @rtype: list of L{MPEGFrames<mpegmeta.MPEGFrame>}
        
        @raise mpegmeta.MpegHeaderException: Raised if no frames was found. This
            should not happen if L{MPEG._is_mpeg_test} has passed.
            
        """
        try:
            return _genmin(\
                     MPEGFrame.find_and_parse(file=self._file,
                                              max_frames=max_frames,
                                              begin_frame_search=begin_offset),
                     1)
        except ValueError:
            raise MpegHeaderEOFException(
                        "There is not enough frames in this file.")
    
    def _parse_ending(self, end_offset=0, min_frames=3, rewind_offset=4000):
        """Parse ending of MPEG.
        
        @note: Performance wisely the max_frames argument would be useless, and 
            is not implemented. As this method must try recursively
            find_and_parse further and further from the ending until minimum of
            frames is met.
        
        @keyword end_offset: End offset as relative to I{end of file}, if you
            know the I{size of footers}, give that.
        @type end_offset: int
        
        @keyword min_frames: Minimum amount of frames from the end of file.
        @type min_frames: int
        
        @keyword rewind_offset: When minimum is not met, rewind the offset
            this much and retry. Defaults to C{4000}.
        @type rewind_offset: int
        
        @note: This might take a long time for files that does not have frames.
        @return: List of MPEG frames, amount of items is variable.
        @rtype: list of L{MPEGFrames<mpegmeta.MPEGFrame>}
        
        @raise mpegmeta.MpegHeaderEOFException: Raised if whole file does not
            include any frames. This should not happen if L{MPEG._is_mpeg_test}
            has passed.
        
        """
        # min_frames is always positive:
        min_frames = max(min_frames, 1)
        
        begin_frame_search = self.filesize - end_offset
        end_frames = []
        
        while True:
            # Oh noes, not enough frames.
            if len(end_frames) < min_frames:
                begin_frame_search -= rewind_offset
                # Retry from backwards...
                end_frames = \
                    list(MPEGFrame.find_and_parse(\
                            file=self._file,
                            max_frames=None,
                            begin_frame_search=begin_frame_search))
                if begin_frame_search < 0 and len(end_frames) < min_frames:
                    raise MpegHeaderException('No frames was found during')
            else:
                return end_frames
        
class MpegException(Exception):
    """MPEG Exception, all MPEG related exceptions inherit from this."""
    pass

class MpegHeaderException(MpegException):
    """MPEG Header Exception, unable to parse or read the header."""
    def __init__(self, message, mpeg_offset=None, bad_offset=None):
        """MPEG Header Exception.
        
        @param message: Message of the exception.
        @type message: string
        
        @keyword mpeg_offset: Offset of the MPEG Frame in file.
        @type mpeg_offset: int 
        
        @keyword bad_offset: Bad offset of the MPEG Frame in file.
        @type bad_offset: int
        
        """
        super(MpegHeaderException, self).__init__(message)
        
        self.mpeg_offset = mpeg_offset
        """MPEG Offset within file
        @type: int"""
        
        self.bad_offset = bad_offset
        """Bad offset within file
        @type: int"""

class MpegHeaderEOFException(MpegHeaderException):
    """MPEG Header End of File (Usually I{End of Chunk}) is reached."""
    pass


class VBRHeader(object):
    """VBR Header"""
    
    @classmethod
    def set_mpeg(cls, mpeg, vbr):
        """Set values of VBR header to MPEG.
        
        @param mpeg: MPEG to be set.
        @type mpeg: L{MPEG}
        
        @param vbr: VBR from where to set.
        @type vbr: L{VBRHeader}
        
        """
        if vbr.frame_count is not None:
            mpeg.frame_count = vbr.frame_count
            
        if vbr.mpeg_size is not None:
            mpeg.size = vbr.mpeg_size
        
    def __init__(self):
        self.offset = 0
        """Offset of header in file.
        @type: int"""
        
        self.size = 0
        """Size of header in file.
        @type: int"""
        
        self.frame_count = None
        """Frame count of MPEG. (Optional)
        @type: int, or None"""
        
        self.mpeg_size = None
        """MPEG Size in bytes. (Optional)
        @type: int, or None"""
        
        self.quality = None
        """VBR Quality.
        @type: int, or None 
        """
        
        # TODO: TOC!

class XING(VBRHeader):
    """XING Header.
    
    This header is often (but unfortunately not always) added to files which are 
    encoded with variable bitrate mode. This header stands after the first MPEG 
    audio header at a specific position. The whole first frame which contains 
    the XING header is a valid but empty audio frame, so even decoders which 
    don't consider this header can decode the file. The XING header stands after
    the side information in Layer III files.
    
    """
    def __init__(self):
        super(XING, self).__init__()
    
    @classmethod
    def find_and_parse(cls, file, first_mpeg_frame):
        """Find and parse XING header in MPEG File.
        
        @param file: File object.
        @type file: file object
        
        @param first_mpeg_frame: Offset of first mpeg frame in file.
        @type first_mpeg_frame: int
        
        @return: XING Header in given file.
        @rtype: L{XING<mpegmeta.XING>}
        
        @raise mpegmeta.XINGHeaderException: Raised if XING Header cannot be 
            parsed or found.
            
        """
        file.seek(first_mpeg_frame)
        # TODO: LOW: Search for Xing is not needed, it has specific place, but
        # what?
        chunk_offset, chunk = file.tell(), file.read(1024) 
        beginning_of_xing = chunk.find('Xing')
        
        # Found the beginning of xing
        if beginning_of_xing != -1:
            if len(chunk[beginning_of_xing + 4:]) <= 116:
                raise XINGHeaderException('EOF')
            
            # 4 bit flags
            (flags,) = struct.unpack('>I', chunk[beginning_of_xing + 4:
                                                 beginning_of_xing + 8])
            
            # Cursor
            cur = beginning_of_xing + 8 # "Xing" + flags = 8
            
            # Flags collected
            has_frame_count = (flags & 1) == 1
            has_mpeg_size = (flags & 2) == 2
            has_toc = (flags & 4) == 4
            has_quality = (flags & 8) == 8
            
            self = XING()
            
            if has_frame_count:
                (self.frame_count,) = struct.unpack('>i', chunk[cur:cur + 4])
                cur += 4
            
            if has_mpeg_size:
                (self.mpeg_size,) = struct.unpack('>i', chunk[cur:cur + 4])
                cur += 4
            
            if has_toc:
                toc_chunk = chunk[cur:cur + 100] #@UnusedVariable
                # TODO: TOC!
                cur += 100
            
            if has_quality:
                (self.quality,) = struct.unpack('>i', chunk[cur:cur + 4])
                cur += 4
                
            self.offset = chunk_offset + beginning_of_xing
            self.size = cur - beginning_of_xing
            
            return self
                        
        raise XINGHeaderException('XING Header is not found.')

class XINGException(Exception):
    """XING Related exceptions inherit from this."""
    pass

class XINGHeaderException(XINGException):
    """XING Header Exception."""
    pass

class VBRI(VBRHeader):
    """Fraunhofer Encoder VBRI Header.
    
    This header is only used by MPEG audio files encoded with the Fraunhofer 
    Encoder as far as I know. It is different from the XING header. You find it 
    exactly 32 bytes after the end of the first MPEG audio header in the file.
    
    """
    def __init__(self):
        super(VBRI, self).__init__()
        
        self.delay = 0
        """Delay.
        @type: float""" 
        
        self.version = None
        """Version number of VBRI.
        @type: int"""
        
    @classmethod
    def find_and_parse(cls, file, first_mpeg_frame):
        """Find and parse VBRI header in MPEG File.
        
        @param file: File object.
        @type file: file object
        
        @param first_mpeg_frame: Offset of first mpeg frame in file.
        @type first_mpeg_frame: int
        
        @return: XING Header in given file.
        @rtype: L{XING<mpegmeta.XING>}
        
        @raise mpegmeta.VBRIHeaderException: Raised if VBRI Header cannot be 
            parsed or found.
            
        """
        file.seek(first_mpeg_frame)
        chunk_offset, chunk = file.tell(), file.read(1024)
        
        beginning_of_vbri = 4 + 32 # Header 4 bytes, VBRI is in 32. byte
        
        # If positive match for VBRI
        if chunk[beginning_of_vbri:beginning_of_vbri + 4] == "VBRI":
            self = VBRI()
            self.offset = chunk_offset + beginning_of_vbri
            self.size = 26
            
            if len(chunk) < 24:
                raise VBRIHeaderException('VBRI EOF')
            
            fcur = beginning_of_vbri
            fcur += 4 # Size of "VBRI"
            entries_in_toc = 0 #@UnusedVariable
            scale_factor_of_toc = 0 #@UnusedVariable
            size_per_table = 0 #@UnusedVariable
            frames_per_table = 0 #@UnusedVariable
            
            (self.version, self.delay, self.quality, self.mpeg_size,
             self.frame_count, entries_in_toc, #@UnusedVariable
             scale_factor_of_toc, size_per_table, #@UnusedVariable
             frames_per_table) = struct.unpack('>HHHIIHHHH', #@UnusedVariable 
                                               chunk[fcur:fcur + 22])
             
            # TODO: TOC!
            
            return self 
        
        raise VBRIHeaderException('VBRI Header not found')

class VBRIException(Exception):
    """VBRI Exceptions inherit from this."""
    pass

class VBRIHeaderException(VBRIException):
    """VBRI Header exception"""
    pass