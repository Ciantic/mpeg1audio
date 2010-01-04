"""mpegmeta - package tests"""

from datetime import timedelta
from mpegmeta import MPEG, MpegException, MPEGFrame, chunked_reader, _genlimit
import mpegmeta
import os
import unittest
import doctest

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
    
    def testBitrate(self):
        """CBR bitrate"""
        self.assertEqual(self.mpeg.bitrate, 256)
        
    def testDuration(self):
        """CBR duration"""
        self.assertEqual(self.mpeg.duration, timedelta(seconds=192))
    
    def testSampleRate(self):
        """CBR sample rate"""
        self.assertEqual(self.mpeg.sample_rate, 44100)
    
    def testSamplesPerFrame(self):
        """CBR samples per frame"""
        self.assertEqual(self.mpeg.samples_per_frame, 1152)
        
    def testFrameSize(self):
        """CBR frame size"""
        self.assertEqual(self.mpeg.frame_size, 836)
        
    def testFrameCount(self):
        """CBR frame count - parse all"""
        self.assertEqual(self.mpeg.frame_count, 7352)
        self.assertEqual(self.mpeg.frame_count, 7352) # Test that we don't parse all two times, cache is in use
        self.assertEqual(self.mpeg.frame_count, 7352) # ...
        self.assertEqual(self.mpeg.frame_count, 7352) # ...
        
    def testIsVBR(self):
        """CBR is VBR?"""
        self.assertEqual(self.mpeg.is_vbr, False)
        
class VBRXingTests(unittest.TestCase):
    """VBR Xing header tests."""
    def setUp(self):
        self.mpeg = MPEG(file=open('data/vbr_xing.mp3', 'rb'))
        
    def testIsVBR(self):
        """VBR Xing is VBR?"""
        self.assertEqual(self.mpeg.is_vbr, True)
    
    def testDuration(self):
        """VBR Xing duration"""
        self.assertEqual(self.mpeg.duration, timedelta(seconds=308))

    def testFrameSize(self):
        """VBR Xing average frame size"""
        # TODO: Following is not verified!
        self.assertEqual(self.mpeg.frame_size, 635) 
        
    def testFrameCount(self):
        """VBR Xing frame count"""
        self.assertEqual(self.mpeg.frame_count, 11805)
        
    def testBitrate(self):
        """VBR Xing average bitrate"""
        self.assertEqual(int(self.mpeg.bitrate), 194)
        
    def testQuality(self):
        """VBR Xing quality"""
        self.assertEqual(self.mpeg.xing.quality, 78)
        
    def testOffset(self):
        """VBR Xing offset of header"""
        self.assertEqual(self.mpeg.xing.offset, 4132)
        
class VBRFraunhoferTests(unittest.TestCase):
    """VBR Fraunhofer Encoder header tests."""
    def setUp(self):
        self.mpeg = MPEG(file=open('data/vbr_fraunhofer.mp3', 'rb'))
        
    def testIsVBR(self):
        """VBR Fraunhofer is VBR?"""
        self.assertEqual(self.mpeg.is_vbr, True)
        
    def testBitrate(self):
        """VBR Fraunhofer average bitrate"""
        self.assertEqual(int(self.mpeg.bitrate), 94)
        
    def testFrameCount(self):
        """VBR Fraunhofer frame count"""
        self.assertEqual(self.mpeg.frame_count, 8074)
        
    def testDelay(self):
        """VBR Fraunhofer delay"""
        self.assertEqual(self.mpeg.vbri.delay, 4630)
        
    def testQuality(self):
        """VBR Fraunhofer quality"""
        self.assertEqual(self.mpeg.vbri.quality, 80)
        
    def testOffset(self):
        """VBR Fraunhofer offset of VBRI header?"""
        self.assertEqual(self.mpeg.vbri.offset, 4132)
    
    def testDuration(self):
        """VBR Fraunhofer duration"""
        self.assertEqual(self.mpeg.duration, timedelta(seconds=210))
        
class VBRHeaderlessTests(unittest.TestCase):
    """VBR headerless tests."""
    def setUp(self):
        self.mpeg = MPEG(file=open('data/vbr_empty.mp3', 'rb'))
        
    def testIsVBR(self):
        """VBR headerless is VBR?"""
        self.assertEqual(self.mpeg.is_vbr, True)
        
    def testBitrate(self):
        """VBR headerless average bitrate"""
        self.assertEqual(int(self.mpeg.bitrate), 94)
        
    def testFrameCount(self):
        """VBR headerless frame count"""
        self.assertEqual(self.mpeg.frame_count, 8074)
    
    def testDuration(self):
        """VBR headerless duration"""
        self.assertEqual(self.mpeg.duration, timedelta(seconds=210))
#        
#    def testDelay(self):
#        """VBR headerless delay"""
#        self.assertEqual(self.mpeg.vbri.delay, 4630)
#        
#    def testQuality(self):
#        """VBR headerless quality"""
#        self.assertEqual(self.mpeg.vbri.quality, 80)
        
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
    suite.addTest(unittest.makeSuite(VBRXingTests))
    suite.addTest(unittest.makeSuite(VBRFraunhoferTests))
    suite.addTest(unittest.makeSuite(VBRHeaderlessTests))
    suite.addTest(unittest.makeSuite(ChunkedReadTests))
    unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Doc tests
    doctest.testmod(mpegmeta)
