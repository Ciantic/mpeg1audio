#!/usr/bin/env python

import sys
assert sys.version >= '2.5', "Requires Python v2.5 or above"
from distutils.core import setup, Extension

setup(
    name="mpeg1audio",
    version="0.5.2",
    author="Jari Pennanen",
    author_email="jari.pennanen@gmail.com",
    url="http://github.com/Ciantic/mpeg1audio/",
    description="Python MPEG-1 Audio information retrieval package.",
    long_description="Retrieves MPEG-1 Audio meta information such as duration, sampling rate, bitrate, average bitrate (for VBR MP3) files, etc.",
    license="FreeBSD",
    packages=["mpeg1audio"],
    package_dir={'mpeg1audio': 'src/mpeg1audio'}
)
