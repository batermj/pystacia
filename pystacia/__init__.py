# coding: utf-8
# pystacia/__init__.py
# Copyright (C) 2011 by Paweł Piotr Przeradowski
#
# This module is part of Pystacia and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""pystacia is a raster graphics library utilizing ImageMagick."""


def init():
    """Find ImageMagick DLL and initialize it.
       
       Searches available paths with :func:`pystacia.util.find_library`
       and then fallbacks to standard :func:`ctypes.util.find_liblrary`.
       Loads the DLL into memory, initializes it and warns if it has
       unsupported API and ABI versions.
    """
    from pystacia.util import find_library
    from pystacia.api import name, abis
    # first let's look in some places that may override system-wide paths
    resolved_path = find_library(name, abis)
    # still nothing? let ctypes figure it out
    if not resolved_path:
        from ctypes.util import find_library  # @Reimport
        resolved_path = find_library('MagickWand')
    if not resolved_path:
        raise TinyException('Could not find or load magickWand')
    
    from ctypes import CDLL
    factory = CDLL
    global cdll
    cdll = factory(resolved_path)
    from pystacia.api.func import annote
    annote(cdll)
    cdll.MagickWandGenesis()
    
    import atexit
    atexit.register(lambda: cdll.MagickWandTerminus())
    
    # warn if unsupported
    from pystacia import magick
    from pystacia.api import min_version
    version = magick.get_version()
    if version < min_version:
        from warnings import warn
        template = formattable('Unsupported version of MagickWand {0}')
        warn(template.format(version))

from pystacia.util import memoized


@memoized
def __raw_lena(factory=None):
    """Decode standard lena test image from bzipped YCbCr stream."""
    filename = join(dirname(__file__), 'lena.ycbcr.bz2')
    return dict(raw=bz2_readfile(filename), format='ycbcr',
                height=512, width=512, depth=8, factory=factory)

# weakref memoization to let garbage collector clear it when needed
# helps pypy a lot
__lena = None


def __lena_image(factory=None):
    """Perform weakref memoization of Lena."""
    global __lena
    
    if not __lena:
        lena = image.read_raw(**__raw_lena(factory))
        __lena = weakref.ref(lena)
    else:
        lena = __lena()
        if not lena:
            lena = image.read_raw(**__raw_lena(factory))
            __lena = weakref.ref(lena)
    
    return lena.copy()


def lena(width=None, factory=None):
    """Return standard lena test image.
       
       Resulting :class:`.Image` object is a TrueType in, RGB colorspace,
       8bit per channel image. For background on the test image see:
       http://en.wikipedia.org/wiki/Lenna.
       
       :param width: Returned image will be of this size. When not specified
         defaults to 512x512 which is how the bitmap is stored internally.
       
    """
    img = __lena_image(factory)
    
    if width:
        img.rescale(width, width)

    img.convert_colorspace(image.colorspaces.rgb)
        
    return img


def magick_logo(factory=None):
    """Return ImageMagick logo image.
        
       Resulting image is 640x480, palette, RGB colorspace image.
    """
    return image.read_special('logo:', factory=factory)


def rose(factory=None):
    """Return rose image.
    
       Resulting image is 70x48, RGB, truecolor.
    """
    return image.read_special('rose:', factory=factory)


def wizard(factory=None):
    """Return wizard image.
    
       Resulting image is 480x640, palette, RGB image.
    """
    return image.read_special('wizard:', factory=factory)


def granite(factory=None):
    """Return granite texture.
    
       Resulting image is 128x128 pallette, RGB image.
    """
    return image.read_special('granite:', factory=factory)


def netscape(factory=None):
    """Return standard Netscape 216 color cube.
       
       Color cube also known as "Websafe Colors".
       216x144, palette, RGB.
    """
    return image.read_special('netscape:', factory=factory)


import pystacia.api.enum as enum_api


def enum_lookup(mnemonic, throw=True):
    """Translate lazyenum's mnemonic into its numeral value.
        
       :param mnemonic: A :class:`pystacia.lazyenum.EnumValue` instance to be
         looked up
        
       :param throw: Raises an exception if mnemonic cant be mapped when
         ``True`` otherwise returns ``None``
    """
    value = enum_api.lookup(mnemonic, magick.get_version())
    if throw and value == None:
        template = "Enumeration '{enum}' cant map mnemonic '{mnemonic}'"
        template = formattable(template)
        enum = mnemonic.enum.name
        mnemonic = mnemonic.name
        raise TinyException(template.format(enum=enum, mnemonic=mnemonic))

    return value


def enum_reverse_lookup(enum, value):
    """Translate numeral value into its lazyenum mnemonic"""
    return enum_api.reverse_lookup(enum, value, magick.get_version())


cdll = None

import weakref
from os.path import dirname, join

from pystacia.compat import formattable, bz2_readfile
from pystacia.util import TinyException

init()

from pystacia import magick
from pystacia import image

#convenience imports
from pystacia.image import read, read_blob, read_raw
from pystacia.image import blank, checkerboard
from pystacia.image import (
    composites, types, filters, colorspaces, compressions, axes)
from pystacia import color
from pystacia.image import Image


__all__ = [
    'lena', 'magick_logo', 'rose', 'wizard', 'granite', 'netscape',
    'read', 'read_blob', 'read_raw',
    'blank', 'checkerboard',
    'composites', 'types', 'filters', 'colorspaces', 'compressions', 'axes',
    'color',
    'Image']