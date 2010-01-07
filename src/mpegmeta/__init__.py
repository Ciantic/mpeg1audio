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
    ... except mpegmeta.MPEGHeaderException:
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

# Too many lines per module:
# pylint: disable-msg=C0302

# Too many instance attributes, Too few public methods:
# pylint: disable-msg=R0902,R0903

# TODO: LOW: I don't like the verboseness of EpyDoc syntax, maybe change to
# reStructuredText?

from datetime import timedelta
from headers import MPEGHeaderEOFException, MPEGHeaderException
import headers
#from headers import get_duration_from_sample_count, \
#    _get_duration_from_size_bitrate, _get_frame_size, \
#    get_bitrate, get_bytes, get_channel_mode, \
#    get_channel_mode_ext, get_emphasis, get_layer, \
#    get_mpeg_version, get_sample_rate, _get_sample_count, \
#    get_samples_per_frame, get_vbr_bitrate, get_vbr_frame_size, \
#    check_sync_bits, MPEGHeaderEOFException, MPEGHeaderException
import math
import utils
import struct

__all__ = ['MPEGFrameBase', 'MPEGFrameIterator', 'MPEGFrame', 'MPEG', 
           'MPEGHeaderException', 'MPEGHeaderEOFException']

PARSE_ALL_CHUNK_SIZE = 153600
"""Chunk size of parsing all frames.
@type: int"""
        
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
            L{utils.DEFAULT_CHUNK_SIZE}.
        @type chunk_size: int
        
        @note: First frame of generator is I{next} frame.
        @return: Generator that iterates forward from this frame.
        @rtype: generator of L{MPEGFrame}
        
        """
        # TODO: LOW: Free bitrate.
        next_frame_offset = self.offset + self.size
        chunks = utils.chunked_reader(file, start_position=next_frame_offset,
                                       chunk_size=chunk_size)
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
            L{utils.DEFAULT_CHUNK_SIZE}, minimum C{4}.
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
        chunk_size = chunk_size or utils.DEFAULT_CHUNK_SIZE
        
        chunk_size = max(chunk_size, 4)
        chunks = utils.chunked_reader(file, chunk_size=chunk_size,
                                start_position=begin_frame_search,
                                max_chunks=max_chunks)

        for chunk_offset, chunk in chunks:
            for found in utils.find_all_overlapping(chunk, chr(255)):
                consecutive_chunks = \
                    utils.chunked_reader(file,
                                    chunk_size=chunk_size,
                                    start_position=chunk_offset + found,
                                    max_chunks=max_consecutive_chunks)
                
                frames = MPEGFrame.parse_consecutive(chunk_offset + found,
                                                     consecutive_chunks) 
                try:
                    return utils.genlimit(frames, lazily_after + 1, max_frames)
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
        
        @see: L{utils.chunked_reader}
        
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
                    header_bytes = headers.get_bytes(next_header_offset, chunk)
                except MPEGHeaderEOFException:
                    # We need next chunk, end of this chunk was reached
                    break
                
                # Parse and append if parseable
                try:
                    next_mpegframe = MPEGFrame.parse(header_bytes)
                except MPEGHeaderException:
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
            L{headers.get_bytes}
        @type bytes: int
        
        @rtype: L{MPEGFrame}
        @return: MPEG Frame
        
        @raise mpegmeta.MPEGHeaderException: Raised if MPEG Frame cannot be 
            parsed.
            
        """
        # TODO: LOW: CRC, verify and parse.
        # http://www.codeproject.com/KB/audio-video/mpegaudioinfo.aspx#CRC
        
        # Header synchronization bits
        headers.check_sync_bits((bytes >> 21) & 2047) 
        
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
        
        self.version = headers.get_mpeg_version(mpeg_version_bits)
        self.layer = headers.get_layer(layer_bits)
        self.bitrate = headers.get_bitrate(self.version, self.layer,
                                           bitrate_bits)
        self.sample_rate = headers.get_sample_rate(self.version,
                                                   samplerate_bits)
        self.channel_mode = headers.get_channel_mode(mode_bits)
        self.channel_mode_extension = \
            headers.get_channel_mode_ext(self.layer, mode_extension_bits)
        self.emphasis = headers.get_emphasis(emphasis_bits)
        
        self._padding_size = padding_bit
        self.is_private = private_bit == 1
        self.is_copyrighted = copyright_bit == 1
        self.is_original = original_bit == 1
        self.is_protected = protection_bit == 1
        
        # Non-header parseable information
        self.samples_per_frame = headers.get_samples_per_frame(self.version,
                                                               self.layer)
        self.size = headers.get_frame_size(self.version, self.layer, 
                                           self.sample_rate, self.bitrate, 
                                           self._padding_size)
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
        return utils.join_iterators(\
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
        
        @raise mpegmeta.MPEGHeaderException: Raised if header cannot be found.
        
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
        
        self.filesize = utils.get_filesize(file)
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
            self.bitrate = headers.get_vbr_bitrate(mpeg_size, sample_count,
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
            self.frame_size = headers.get_vbr_frame_size(mpeg_size, frame_count)
            
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
                    headers.get_duration_from_sample_count(sample_count,
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
                    headers.get_duration_from_sample_count(sample_count,
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
        from xing import XING, XINGHeaderException
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
        from vbri import VBRI, VBRIHeaderException
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
        
        @raise mpegmeta.MPEGHeaderException: Raised if MPEG frames cannot be 
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
        
        @raise mpegmeta.MPEGHeaderException: Raised if no frames was found. This
            should not happen if L{MPEG._is_mpeg_test} has passed.
            
        """
        try:
            return utils.genmin(\
                     MPEGFrame.find_and_parse(file=self._file,
                                              max_frames=max_frames,
                                              begin_frame_search=begin_offset),
                     1)
        except ValueError:
            raise MPEGHeaderEOFException(
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
        
        @raise mpegmeta.MPEGHeaderEOFException: Raised if whole file does not
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
                    raise MPEGHeaderException('No frames was found during')
            else:
                return end_frames

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
