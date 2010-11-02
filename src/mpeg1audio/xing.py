"""
XING VBR Header parsing module.

"""

# Pylint disable settings:
# ------------------------
# ToDos, DocStrings:
# pylint: disable-msg=W0511,W0105

# Unused variable, argument:
# pylint: disable-msg=W0612,W0613

# Re-define built-in:
# pylint: disable-msg=W0622

from mpeg1audio import VBRHeader
import struct

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
    def find_and_parse(cls, file, first_frame_offset):
        """Find and parse XING header in MPEG File.
        
        :param file: File object.
        :type file: file object
        
        :param first_frame_offset: Offset of first mpeg frame in file.
        :type first_frame_offset: int
        
        :return: XING Header in given file.
        :rtype: :class:`XING`
        
        :raise XINGHeaderException: Raised if XING Header cannot be parsed or 
            found.
            
        """
        file.seek(first_frame_offset)
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
