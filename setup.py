#!/usr/bin/env python

import sys
assert sys.version >= '2.5', "Requires Python v2.5 or above"
from distutils.core import setup, Extension

setup(
    name="mp3meta",
    version="0.5.2",
    author="Jari Pennanen",
    author_email="jari.pennanen@gmail.com",
    url="http://github.com/Ciantic/mp3meta/",
    description="Python MPEG Meta information retrieval package.",
    long_description="Retrieves MPEG Meta information such as duration, sampling rate, bitrate, average bitrate (for VBR MP3) files, etc.",
    license="LGPL",
    packages=["mp3meta"],
    package_dir={'mp3meta': 'src/mp3meta'}
)
