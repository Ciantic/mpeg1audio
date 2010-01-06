"""mpegmeta - package tests"""

from datetime import timedelta
from mpegmeta import MPEG, MpegException, MPEGFrame, chunked_reader, _genlimit
import mpegmeta
import os
import unittest
import doctest

class MPEGSong2Tests(unittest.TestCase):
    """Simple CBR song 2 tests."""
    def setUp(self):
        self.mpeg = MPEG(file=open('data/song2.mp3', 'rb'))
        
    def testFrameCount(self):
        """CBR (2) frame count"""
        self.assertEqual(self.mpeg.frame_count, 12471)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, True)
        
class MPEGSong3Tests(unittest.TestCase):
    """Simple CBR song 3 tests."""
    def setUp(self):
        self.mpeg = MPEG(file=open('data/song3.mp3', 'rb'))
        
    def testFrameCount(self):
        """CBR (3) frame count"""
        self.assertEqual(self.mpeg.frame_count, 9452)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, True)
        
    def testSize(self):
        """CBR (3) size"""
        self.assertEqual(self.mpeg.size, 5925826)
        
class MPEGTests(unittest.TestCase):
    """Simple CBR MPEG tests."""
    def setUp(self):
        self.mpeg = MPEG(file=open('data/song.mp3', 'rb'))
        
    def testPositions(self):
        """CBR frame positions"""
        self.assertEqual(self.mpeg.frames[0].offset, 2283)
        self.assertEqual(self.mpeg.frames[1].offset, 3119)
        self.assertEqual(self.mpeg.frames[2].offset, 3955)
        self.assertEqual(self.mpeg.frames[3].offset, 4791)
        self.assertEqual(self.mpeg.frames[4].offset, 5627)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
    
    def testBitrate(self):
        """CBR bitrate"""
        self.assertEqual(self.mpeg.bitrate, 256)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testDuration(self):
        """CBR duration"""
        self.assertEqual(self.mpeg.duration, timedelta(seconds=192))
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, True)
    
    def testSampleRate(self):
        """CBR sample rate"""
        self.assertEqual(self.mpeg.sample_rate, 44100)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
    
    def testSamplesPerFrame(self):
        """CBR samples per frame"""
        self.assertEqual(self.mpeg.samples_per_frame, 1152)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testFrameSize(self):
        """CBR frame size"""
        self.assertEqual(self.mpeg.frame_size, 836)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testFrameCount(self):
        """CBR frame count"""
        self.assertEqual(self.mpeg.frame_count, 7352)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, True)
        
    def testIsVBR(self):
        """CBR is VBR?"""
        self.assertEqual(self.mpeg.is_vbr, False)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
class VBRXingTests(unittest.TestCase):
    """VBR Xing header tests."""
    def setUp(self):
        self.mpeg = MPEG(file=open('data/vbr_xing.mp3', 'rb'))
        
    def testIsVBR(self):
        """VBR Xing is VBR?"""
        self.assertEqual(self.mpeg.is_vbr, True)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
    
    def testDuration(self):
        """VBR Xing duration"""
        self.assertEqual(self.mpeg.duration, timedelta(seconds=308))
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)

    def testFrameSize(self):
        """VBR Xing average frame size"""
        # TODO: Following is not verified!
        self.assertEqual(self.mpeg.frame_size, 635)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False) 
        
    def testFrameCount(self):
        """VBR Xing frame count"""
        self.assertEqual(self.mpeg.frame_count, 11805)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testBitrate(self):
        """VBR Xing average bitrate"""
        self.assertEqual(int(self.mpeg.bitrate), 194)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testQuality(self):
        """VBR Xing quality"""
        self.assertEqual(self.mpeg.xing.quality, 78)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testOffset(self):
        """VBR Xing offset of header"""
        self.assertEqual(self.mpeg.xing.offset, 4132)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
class VBRFraunhoferTests(unittest.TestCase):
    """VBR Fraunhofer Encoder header tests."""
    def setUp(self):
        self.mpeg = MPEG(file=open('data/vbr_fraunhofer.mp3', 'rb'))
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testIsVBR(self):
        """VBR Fraunhofer is VBR?"""
        self.assertEqual(self.mpeg.is_vbr, True)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testBitrate(self):
        """VBR Fraunhofer average bitrate"""
        self.assertEqual(int(self.mpeg.bitrate), 94)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testFrameCount(self):
        """VBR Fraunhofer frame count"""
        self.assertEqual(self.mpeg.frame_count, 8074)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testDelay(self):
        """VBR Fraunhofer delay"""
        self.assertEqual(self.mpeg.vbri.delay, 4630)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testQuality(self):
        """VBR Fraunhofer quality"""
        self.assertEqual(self.mpeg.vbri.quality, 80)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testOffset(self):
        """VBR Fraunhofer offset of VBRI header?"""
        self.assertEqual(self.mpeg.vbri.offset, 4132)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
    
    def testDuration(self):
        """VBR Fraunhofer duration"""
        self.assertEqual(self.mpeg.duration, timedelta(seconds=210))
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
class VBRHeaderlessTests(unittest.TestCase):
    """VBR headerless tests."""
    def setUp(self):
        self.mpeg = MPEG(file=open('data/vbr_empty.mp3', 'rb'))
        
    def testIsVBR(self):
        """VBR headerless is VBR?"""
        self.assertEqual(self.mpeg.is_vbr, True)
        self.assertEqual(self.mpeg.frames._has_parsed_all, False)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
    def testBitrate(self):
        """VBR headerless average bitrate"""
        self.assertEqual(int(self.mpeg.bitrate), 94)
        self.assertEqual(self.mpeg.frames._has_parsed_all, True)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, True)
        
    def testFrameCount(self):
        """VBR headerless frame count"""
        self.assertEqual(self.mpeg.frame_count, 8074)
        self.assertEqual(self.mpeg.frames._has_parsed_all, True)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
    
    def testDuration(self):
        """VBR headerless duration"""
        self.assertEqual(self.mpeg.duration, timedelta(seconds=210))
        self.assertEqual(self.mpeg.frames._has_parsed_all, True)
        self.assertEqual(self.mpeg.frames._has_parsed_ending, False)
        
class ChunkedReadTests(unittest.TestCase):
    def setUp(self):
        self.file = open('data/song.mp3', 'rb')
        
    def testParseConsecutive(self):
        """Chunked parse consecutive"""
        chunks = chunked_reader(self.file, chunk_size=4)
        self.assertEqual([2283, 3119, 3955], [f.offset for f in _genlimit(MPEGFrame.parse_consecutive(header_offset=2283, chunks=chunks), 2,3)])
        
    def testFindAndParse(self):
        """Chunked find and parse"""
        self.assertEqual([2283, 3119, 3955], [f.offset for f in list(MPEGFrame.find_and_parse(self.file, max_frames=3, chunk_size=4, begin_frame_search=2273))])
        
if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MPEGTests))    
    suite.addTest(unittest.makeSuite(MPEGSong2Tests))    
    suite.addTest(unittest.makeSuite(MPEGSong3Tests))    
    suite.addTest(unittest.makeSuite(VBRXingTests))
    suite.addTest(unittest.makeSuite(VBRFraunhoferTests))
    suite.addTest(unittest.makeSuite(VBRHeaderlessTests))
    suite.addTest(unittest.makeSuite(ChunkedReadTests))
    unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Doc tests
    doctest.testmod(mpegmeta)
