#!/usr/bin/env python

import sys
assert sys.version >= '2.5', "Requires Python v2.5 or above"
from distutils.core import setup, Extension

setup(
    name="mpegmeta",
    version="0.5.1",
    author="Jari Pennanen",
    author_email="jari.pennanen@gmail.com",
    url="http://github.com/Ciantic/mpegmeta/",
    description="Python MPEG Meta information retrieval package.",
    long_description="Retrieves MPEG Meta information such as duration, sampling rate, bitrate, average bitrate (for VBR MP3) files, etc.",
    license="LGPL",
    packages=["mpegmeta"],
    package_dir={'mpegmeta': 'src/mpegmeta'}
)
