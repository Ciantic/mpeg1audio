    
MPEGAudio object is lazy
========================

Laziness works when ...
-----------------------

Laziness works for the cases where we don't need to parse all frames, or
ending of the file. Being lazy for MPEGAudio object means that it has passed
at least:

 1. :func:`is mpeg test <mpeg1audio.MPEGAudio._is_mpeg_test()>` returned without
    exception. 
 2. :func:`beginning parsing <mpeg1audio.MPEGAudio._parse_beginning()>` is
    done.
 
Normal initialization of MPEGAudio object does these things, user of this
class does not need to care about these. All MPEGAudio objects are lazy,
when they have been created without exceptions.

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
MPEGAudio object does lazily, when really required:

 - Parse ending of file
 - Parse all frames

For the end user of this API this is convinient, it might not care if the 
file is VBR, CBR, or what ever. For example if one cares only about the 
duration of MPEGAudio: 

With creating the MPEGAudio instance object I{we ensure} - did not yield
parsing exception - that by running C{mpeg.duration} the user gets the
duration, even if as worst case scenario it might require parsing all
frames.

On the other hand, if the user doesn't want to parse all frames, and is
satisfied for C{None} for the cases where it cannot be calculated without
full parsing, the API gives you possibility to use appropriate getters with 
arguments to adjust for the case.
