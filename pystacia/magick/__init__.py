# coding: utf-8
# pystacia/magick/__init__.py
# Copyright (C) 2011-2012 by Paweł Piotr Przeradowski
#
# This module is part of Pystacia and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from pystacia.util import memoized

from os.path import dirname, join, exists
try:
    from xml.etree.cElementTree import ElementTree
except ImportError:
    from xml.etree.ElementTree import ElementTree  # @Reimport


@memoized
def get_version():
    options = get_options()

    try:
        version = options['LIB_VERSION_NUMBER']
    except KeyError:
        try:
            version = options['VERSION']
        except KeyError:
            return None
        else:
            return tuple(int(x) for x in version.split('.'))
    else:
        return tuple(int(x) for x in version.split(','))


@memoized
def get_options():
    def get_options_hack(path):
        options = {}

        parser = ElementTree()
        root = parser.parse(path)
        for element in root.findall('configure'):
            attrs = element.attrib
            options[attrs['name']] = attrs['value']

        return options

    dll_path = dirname(get_dll()._name)
    config_path = join(dll_path, 'configure.xml')

    if exists(config_path):
        return get_options_hack(config_path)
    else:
        return impl.get_options()


@memoized
def get_version_str():
    return c_call('magick_', 'get_version', None)


@memoized
def get_delegates():
    try:
        delegates = get_options()['DELEGATES']
    except KeyError:
        return []

    return delegates.split()


@memoized
def get_depth():
    depth = get_options().get('QuantumDepth')
    return int(depth) if depth else None


@memoized
def get_formats():
    return impl.get_formats()

from pystacia.api import get_dll
from pystacia.api.func import c_call
from pystacia.magick import _impl as impl
