mpegmeta
========

Pure Python MPEG related meta information retrieval package `mpegmeta`.

 * [GitHub repository of `mpegmeta`](http://github.com/Ciantic/mpegmeta.git)

Capable of retrieving duration (also duration of VBR MP3 files, using XING and 
VBRI headers and parsing all frames), bitrate, average bitrate, sample count... 
This was done because other packages seemed to be licensed under GPL, this one 
is licensed under LGPL. License might be changed in future to MIT License / BSD 
license.

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

    >>> import mpegmeta
    >>> try:
    ...     mpeg = mpegmeta.MPEG(open('data/song.mp3', 'rb'))
    ... except mpegmeta.MPEGHeaderException:
    ...     pass
    ... else:
    ...     print mpeg.duration
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
`docs/EpyDoc for MPEGMeta.launch`. Currently the launch configuration has one
hard-coded file path, so it is wise to edit this configuration before using it.

### pylint

All source files are also analyzed using pylint, and in ideal case all source
files of *package* should be free of pylint errors or warnings.