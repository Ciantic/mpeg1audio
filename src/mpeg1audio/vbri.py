"""
VBRI (Fraunhofer Encoder) Header

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

class VBRI(VBRHeader):
    """Fraunhofer Encoder VBRI Header.
    
    This header is only used by MPEG audio files encoded with the Fraunhofer
    Encoder. It is different from the XING header. You find it exactly 32 bytes
    after the end of the first MPEG audio header in the file.
    
    """
    def __init__(self):
        super(VBRI, self).__init__()

        self.delay = 0
        """Delay.
        :type: float"""

        self.version = None
        """Version number of VBRI.
        :type: int"""

    @classmethod
    def find_and_parse(cls, file, first_frame_offset):
        """Find and parse VBRI header in MPEG File.
        
        :param file: File object.
        :type file: file object
        
        :param first_frame_offset: Offset of first mpeg frame in file.
        :type first_frame_offset: int
        
        :return: XING Header in given file.
        :rtype: :class:`XING`
        
        :raise VBRIHeaderException: Raised if VBRI Header cannot be 
            parsed or found.
            
        """
        file.seek(first_frame_offset)
        chunk_offset, chunk = file.tell(), file.read(1024)

        beginning_of_vbri = 4 + 32 # Header 4 bytes, VBRI is in 32nd byte.

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
