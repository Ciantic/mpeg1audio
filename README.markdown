mp3meta
========

Pure Python MPEG-1 Audio related meta information retrieval package `mp3meta`.

 * [GitHub repository of `mp3meta`](http://github.com/Ciantic/mp3meta.git)

Capable of retrieving duration (also duration of VBR MP3 files, using XING and 
VBRI headers and parsing all frames), bitrate, average bitrate, sample count... 
This was done because other packages seemed to be licensed under GPL, this one 
is licensed under LGPL. License might be changed in future to MIT License / BSD 
license.

**Note**: This is not meant to retrieve ID3v1 or ID3v2 tags. They are not part
of MPEG Audio Layer I,II,III. If you are interested on ID-tags, I recommend 
[pytagger](http://code.google.com/p/liquidx/wiki/pytagger).

## For users of this package

### Documentation

Documentation can be found under `docs` -directory, they are included only
in releases. Other releases, such as GitHub repository does not include HTML
generated documents. I'm trying to create automated way to generate EpyDoc
HTML directly from repository as new commits come in... But until that is 
implemented, there will be *no documentation available online*.

### Installation

This package uses `distutils` and is easily installed using that:

	$ setup.py install
	
Under Windows you can start the command prompt with administrator rights (by 
right clicking `cmd.exe` and using "Run as administrator") then run the above 
command.

### Usage example

    >>> import mp3meta
    >>> try:
    ...    mp3 = mp3meta.MPEGAudio(open('data/song.mp3', 'rb'))
    ... except mp3meta.MPEGAudioHeaderException:
    ...    pass
    ... else:
    ...    print mp3.duration
    0:03:12
    
## For developers of this package

### Unit testing

There exists directory `tests/` which has `tests.py` and `benchmarks.py`,
but I have not provided contents of `tests/data/` yet. I'm looking for MP3 files
that can be distributed without copyright issues. Currently I'm in search for
pretty much any kind of files: Normal CBR, VBR Xing, VBRI Fraunhofer encoded, 
and Free bitrate -MP3 files.

### PyDev and Eclipse

This project uses PyDev and Eclipse, and for this reason there are `.project` 
and `.pydevproject` files. For documentation there is EpyDoc launch
configuration that can generate documentation from within Eclipse, see
`docs/EpyDoc for mp3meta.launch`. Currently the launch configuration has one
hard-coded file path, so it is wise to edit this configuration before using it.

There is also launch configuration for unit testing `tests/Tests for 
mp3meta.launch`, it seems to be dependant on naming of `mp3meta` in workspace. 

### pylint

All source files are also analyzed using pylint, and in ideal case all source
files of *package* should be free of pylint errors or warnings.