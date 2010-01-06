"""MPEG Headers related parsing."""

# Pylint disable settings:
# ------------------------
# ToDos, DocStrings:
# pylint: disable-msg=W0511,W0105
 
# Unused variable, argument:
# pylint: disable-msg=W0612,W0613

from datetime import timedelta
import struct

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
    
    @raise mpegmeta.MPEGHeaderException: Raised if bits does not contain sync 
        bits.
    
    """
    if (bits & 2047) != 2047:
        raise MPEGHeaderException('Sync bits does not match.')
    
def _get_header_mpeg_version(bits):
    """Get MPEG version from header bits.
    
    @param bits: Two version bits in MPEG header.
    @type bits: int
    
    @return: MPEG Version, one of the following values: C{"2.5", "2", "1"}. 
    @rtype: string
    
    @todo: Ponder about the usefulness of this being string. Same with
        L{_get_header_layer}.
    
    @raise mpegmeta.MPEGHeaderException: Raised when layer cannot be determined.
    
    """
    
    try:
        return _MPEG_VERSIONS[bits]
    except (KeyError, IndexError):
        raise MPEGHeaderException('Unknown MPEG version.')
    
def _get_header_layer(bits):
    """Get layer from MPEG Header bits.
    
    @param bits: Two layer bits in MPEG header.
    @type bits: int
    
    @return: MPEG Layer, one of the following values: C{'1', '2', '3'}.
    @rtype: string
    
    @raise mpegmeta.MPEGHeaderException: Raised when layer cannot be determined.
    
    """

    
    try:
        return _LAYERS[bits]
    except (KeyError, IndexError):
        raise MPEGHeaderException('Unknown Layer version')
    
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
    
    @raise mpegmeta.MPEGHeaderException: Raised when bitrate cannot be
        determined.
    
    """
    
    # TODO: LOW: Free bitrate
    if bitrate_bits == 0:
        raise MPEGHeaderException('Free bitrate is not implemented, sorry.') 
    
    try:
        return _BITRATE[mpeg_version][layer][bitrate_bits]
    except (KeyError, IndexError):
        raise MPEGHeaderException('Bitrate cannot be determined.')

    
def _get_header_sample_rate(mpeg_version, bits):
    """Get sample rate by MPEG version and given MPEG Header sample rate bits.
    
    @param mpeg_version: Version of the MPEG, as returned by 
        L{_get_header_mpeg_version}
    @type mpeg_version: string
    
    @param bits: Sample rate bits in MPEG header.
    @type bits: int
    
    @return: Sample rate in Hz
    @rtype: int
    
    @raise mpegmeta.MPEGHeaderException: Raised when sample rate cannot be
        determined.
    
    """

    try:
        return _SAMPLERATE[mpeg_version][bits]
    except (KeyError, TypeError, IndexError):
        raise MPEGHeaderException('Sample rate cannot be determined.')
    
def _get_header_channel_mode(bits):
    """Get channel mode.
    
    @param bits: Mode bits in MPEG header.
    @type bits: int
    
    @return: Returns one of the following: C{"stereo"}, C{"joint stereo"}, 
        C{"dual channel"}, C{"mono"}. 
    @rtype: string
    
    @raise mpegmeta.MPEGHeaderException: Raised if channel mode cannot be 
        determined.
    """
    
    
    try:
        return _CHANNEL_MODES[bits]
    except (IndexError, TypeError):
        raise MPEGHeaderException('Channel channel_mode cannot be determined.')

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
       
    @raise mpegmeta.MPEGHeaderException: Raised if channel mode extension cannot 
        be determined.
        
    """

    try:
        return _CHANNEL_MODE_EXT[layer][bits]
    except (KeyError, TypeError, IndexError):
        raise MPEGHeaderException('Channel mode ext. cannot be determined.')

def _get_header_emphasis(bits):
    """Get emphasis of audio.
    
    @param bits: Emphasis bits in MPEG header.
    @type bits: int
    
    @return: Returns emphasis, one of the following: C{"none", "50/15 ms", 
        "reserved", "CCIT J.17"}
    @rtype: string 
    
    @raise mpegmeta.MPEGHeaderException: Raised when emphasis cannot be
        determined.
    
    """
    
    
    try:
        return _EMPHASES[bits]
    except (TypeError, IndexError): 
        raise MPEGHeaderException('Emphasis cannot be determined.')

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
    
    @raise mpegmeta.MPEGHeaderEOFException: Raised when end of chunk was 
        reached.
    
    """
    # Get first four bytes
    header = chunk[header_offset:header_offset + 4]
    if len(header) != 4:
        raise MPEGHeaderEOFException('End of chunk reached, header not found.')
    
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
    
    @raise mpegmeta.MPEGHeaderException: Raised if samples per frame cannot be 
        determined.
    
    """
    try:
        return _SAMPLES_PER_FRAME[mpeg_version][layer]
    except (IndexError):
        raise MPEGHeaderException('Samples per frame cannot be determined.')
 

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
    
    @raise mpegmeta.MPEGHeaderException: Raised when frame size cannot be 
        determined.
    
    """
    try:
        coeff = _SLOT_COEFFS[mpeg_version][layer]
        slotsize = _SLOTS[layer]
    except (IndexError, KeyError, TypeError):
        raise MPEGHeaderException('Frame size cannot be determined.')
    
    bitrate_k = bitrate * 1000
    
    framesize = int((coeff * bitrate_k / sample_rate) + padding_size) * slotsize
    if framesize <= 0:
        raise MPEGHeaderException('Frame size cannot be calculated.')
    return framesize

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
    
    @raise mpegmeta.MPEGHeaderException: Raised if duration cannot be 
        determined.
    
    @return: Duration of the MPEG, with second accuracy.
    @rtype: datetime.timedelta
    
    """
    try:
        return timedelta(seconds=(mpeg_size / (bitrate * 1000) * 8))
    except ZeroDivisionError:
        raise MPEGHeaderException('Duration cannot be determined.')
    
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

class MPEGHeaderException(Exception):
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
        super(MPEGHeaderException, self).__init__(message)
        
        self.mpeg_offset = mpeg_offset
        """MPEG Offset within file
        @type: int"""
        
        self.bad_offset = bad_offset
        """Bad offset within file
        @type: int"""

class MPEGHeaderEOFException(MPEGHeaderException):
    """MPEG Header End of File (Usually I{End of Chunk}) is reached."""
    pass