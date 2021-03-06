# coding: utf-8

# pystacia/api/__init__.py
# Copyright (C) 2011-2012 by Paweł Piotr Przeradowski

# This module is part of Pystacia and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from __future__ import with_statement

import os
from os import getcwd, chdir
from os.path import join, exists, dirname
from warnings import warn
import atexit
from logging import getLogger
from threading import Lock


logger = getLogger('pystacia.api')


def dll_template(osname, abi):
    if osname == 'macos':
        return 'lib{name}.{abi}.dylib' if abi else 'lib{name}.dylib'
    elif osname == 'linux':
        return 'lib{name}.so.{abi}' if abi else 'lib{name}.so'
    elif osname == 'windows':
        return 'lib{name}-{abi}.dll' if abi else 'lib{name}.dll'

    return None


def process_depends(depends_path, path, osname, factory):
    depends = open(depends_path)

    for line in depends:
        depname, depabi = line.split()
        template = formattable(dll_template(osname, depabi))
        dll_path = join(path, template.format(name=depname,
                                              abi=depabi))
        try:
            factory(dll_path)
        except:
            pass

    depends.close()


def find_in_path(path, name, abis, osname, factory):
    depends_path = join(path, 'depends.txt')
    if exists(depends_path):
        process_depends(depends_path, path, osname, factory)

    for abi in abis:
        template = dll_template(osname, abi)
        if not template:
            continue

        template = formattable(template)

        dll_path = join(path, template.format(name=name, abi=abi))

        logger.debug('Trying: ' + dll_path)

        if exists(dll_path):
            logger.debug('Found: ' + dll_path)

            if osname == 'windows':
                old_path = getcwd()
                chdir(path)

            try:
                factory(dll_path)
            except:
                from sys import exc_info
                msg = formattable('Caught exception while loading '
                                  '{0}: {1}. Rolling back')
                logger.debug(msg.format(dll_path, exc_info()[1]))

                if osname == 'windows':
                    chdir(old_path)
            else:
                if osname == 'windows':
                    chdir(old_path)

                return dll_path


def gather_paths(environ):
    paths = []

    path = registry.get('library_path', environ.get('PYSTACIA_LIBRARY_PATH'))
    if path:
        paths.append(path)

    if not registry.get('skip_package', environ.get('PYSTACIA_SKIP_PACKAGE')):
        import pystacia
        path = dirname(pystacia.__file__)
        paths.append(join(path, 'cdll'))

    if not registry.get('skip_virtual_env',
                        environ.get('PYSTACIA_SKIP_VIRTUAL_ENV')):
        try:
            path = environ['VIRTUAL_ENV']
        except KeyError:
            pass
        else:
            paths.append(join(path, 'lib'))
            paths.append(join(path, 'dll'))

    if not registry.get('skip_cwd', environ.get('PYSTACIA_SKIP_CWD')):
        paths.append(getcwd())

    return paths


def find_library(name, abis, environ=None, osname=None, factory=None):
    logger.debug('Trying to find ImageMagick...')

    if not environ:
        environ = os.environ

    if not factory:
        factory = CDLL

    if not osname:
        osname = get_osname()

    paths = gather_paths(environ)

    logger.debug('Following paths will be searched: ' + ';'.join(paths))

    for path in paths:
        if not exists(path):
            logger.debug('Path does not exist: ' + path)
            continue

        dll_path = find_in_path(path, name, abis, osname, factory)
        if dll_path:
            return dll_path

    # still nothing? let ctypes figure it out
    if not registry.get('skip_system', environ.get('PYSTACIA_SKIP_SYSTEM')):
        return ctypes_find_library(name)

    return None


class library_path_transaction:
    def __init__(self, path):
        self.path = path

    def begin(self):
        self.old_path = getcwd()
        chdir(self.path)

        return self

    def commit(self):
        chdir(self.old_path)
        return self

    def rollback(self):
        chdir(self.old_path)


__lock = Lock()


def init_dll(dll):
    def shutdown():
        logger.debug('Cleaning up traced instances')
        _cleanup()

        c_call(None, 'terminus')

        if jython:
            from java.lang import System  # @UnresolvedImport
            System.exit(0)

    logger.debug('Critical section - init MagickWand')
    with __lock:
        if not dll.__inited:
            c_call(None, 'genesis', __init=False)

            logger.debug('Registering atexit handler')
            atexit.register(shutdown)

            dll.__inited = True

    version = magick.get_version()
    if version < min_version:
        msg = formattable('Unsupported version of MagickWand {0}')
        warn(msg.format(version))


def get_dll(init=True, environ=None, isolated=False):
    """Find ImageMagick DLL and initialize it.

       Searches available paths with :func:`find_library`
       and then fallbacks to standard :func:`ctypes.util.find_liblrary`.
       Loads the DLL into memory, initializes it and warns if it has
       unsupported API and ABI versions.
    """
    if not hasattr(get_dll, '__dll') or isolated:
        logger.debug('Critical section - load MagickWand')
        with __lock:
            if not hasattr(get_dll, '__dll') or isolated:
                if not environ:
                    environ = os.environ

                path = find_library(name, abis, environ=environ)
                if not path:
                    msg = 'Could not find or load MagickWand'
                    raise PystaciaException(msg)

                msg = formattable('Loading MagickWand from {0}')
                logger.debug(msg.format(path))
                dll = CDLL(path)
                if not isolated:
                    get_dll.__dll = dll
                    get_dll.__dll.__inited = False
                else:
                    return dll

    dll = get_dll.__dll

    if init and not dll.__inited:
        init_dll(dll)

    return dll


from pystacia import registry
from pystacia.util import get_osname, PystaciaException
from pystacia.compat import formattable, jython
from pystacia.common import _cleanup
from pystacia import magick
from pystacia.api.func import c_call
from pystacia.api.compat import CDLL, find_library as ctypes_find_library


min_version = (6, 5, 9, 0)
name = 'MagickWand'
abis = (5, 4, 3, None)
