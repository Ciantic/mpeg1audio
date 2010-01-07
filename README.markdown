mpegmeta
--------

Pure Python MPEG related meta information retrieval package `mpegmeta`.

 * [GitHub repository of `mpegmeta`](http://github.com/Ciantic/mpegmeta.git)

Capable of retrieving duration (also duration of VBR MP3 files, using XING and 
VBRI headers and parsing all frames), bitrate, average bitrate, sample count... 
This was done because other packages seemed to be licensed under GPL, this one 
is licensed under LGPL. License might be changed in future to MIT License / BSD 
license.

### Documentation

Documentation can be found under `docs` -directory, they are included only
in releases. Other releases, such as GitHub repository does not include HTML
generated documents. I'm trying to create automated way to generate EpyDoc
HTML directly from repository automatically, and put that some place... But 
until that is implemented, there will be no documentation available online.

### Installation

This package uses `distutils` and is easily installed using that:

	$ setup.py install
	
Under Windows you can start the command prompt with administrator rights (by 
right clicking `cmd.exe` and using "Run as administrator") then run the above 
command.

### Usage example

    >>> import mpegmeta
    >>> try:
    ...     mpeg = mpegmeta.MPEG(open('data/song.mp3', 'rb'))
    ... except mpegmeta.MPEGHeaderException:
    ...    pass
    ... else:
    ...     print mpeg.duration
    0:03:12
