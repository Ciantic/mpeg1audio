from mpegmeta import MPEG
import mpegmeta

def benchmark_chunk_size(size, parsing_method):
    if parsing_method == 'parse_all':
        mpegmeta.PARSE_ALL_CHUNK_SIZE = size
    else:
        mpegmeta.DEFAULT_CHUNK_SIZE = size
    
    # TODO: BENCHMARKS: This is most likely highly biased to use only one file:
    mpeg = MPEG(file=open('data/song.mp3', 'rb'))
    
    if parsing_method == 'parse_all':
        mpeg.parse_all()
        
    if parsing_method == 'parse_ending':
        mpeg.frames[-1]
        
    mpeg._file.close()
    
def benchmark_parsing(chunk_sizes, number, parsing_method):
    from timeit import Timer
    print "Benchmarking %s for %s-times:" % (parsing_method, number)
    print "Chunk size, Seconds"
    for size in chunk_sizes:
        time = Timer("benchmark_chunk_size(%s, '%s')" % (size, parsing_method), 
                          "from __main__ import benchmark_chunk_size").timeit(number)
        print "% 10d % 6.3fs" % (size, time) 
    print "Done..."
    print ""
    
if __name__ == '__main__':
#    benchmark_parsing([1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192, 9216, 10240, 51200, 102400], 
#                      number = 5000, 
#                      parsing_method = '')
#
    benchmark_parsing([1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192, 9216, 10240, 51200, 102400], 
                      number = 10000, 
                      parsing_method = 'parse_ending')
#
#    benchmark_parsing([1024, 8192, 10240, 51200, 81920, 102400, 153600, 163840, 204800, 1024000], 
#                      number = 60, 
#                      parsing_method = 'parse_all')
