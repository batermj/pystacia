# coding: utf-8

# pystacia/common.py
# Copyright (C) 2011-2012 by Paweł Piotr Przeradowski

# This module is part of Pystacia and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from __future__ import with_statement

from threading import Lock
from weakref import WeakValueDictionary


"""Resource management utilities."""


class state(object):

    """State management context guard

       Used for push - pop paradigm with objects supporting
       _get_state and _set_state contract. Typically used with
       "with" statement.

       >>> resource = Resource(None)
       >>> with state(resource, quality=10, format='png'):
       ...     resource.do_sth()
    """

    def __init__(self, resource, **kw):
        self.__resource = resource
        self.__state = []
        self.__kw = kw

    def push(self):
        """Push state"""
        resource = self.__resource

        for prop, value in self.__kw.items():
            if value is None:
                continue
            old_value = resource._get_state(prop)
            self.__state.append((prop, old_value))
            resource._set_state(prop, value)

    def pop(self):
        """Pop state"""
        for prop, value in reversed(self.__state):
            self.__resource._set_state(prop, value)

    __enter__ = push

    def __exit__(self, type, value, traceback):  # @ReservedAssignment
        self.pop()


class Resource(object):

    """Base class for :term:`ImageMagick` resources.

       Serves a base for classes that need to call
       C functions to allocate underlying structures.
       Also keeps track of all objects with weak references
       so they can be freed all at once if they are still
       alive at the time program exits.

       Subclasses need to implement three methods: _alloc, _free and _copy to
       conform to the interface.
    """

    def __init__(self, resource=None):
        """Construct new instance of resource."""
        self.__resource = resource if resource is not None else self._alloc()

        if self.__resource is None:
            tmpl = formattable('{0} _alloc method returned None')
            raise PystaciaException(tmpl.format(self.__class__.__name__))

        _track(self)

    def _claim(self, untrack=True):
        """Claim resource and close this instance.

           This is used to transfer management of underlying
           resource to another
           entity. This instance is closed afterwards.

           Not to be called directly under normal circumstances
        """
        self.__resource, resource = None, self.__resource

        if untrack:
            _untrack(self)

        return resource

    def _replace(self, resource):
        """Free current resource, claim resource from another object.

           Frees underlying resource, claims resource from another object
           and sets this object resource to claimed resource, effectively
           transferring resource property to this object.

           Not to be called directly
        """
        if isinstance(resource, Resource):
            resource = resource._claim()

        if resource is None:
            raise PystaciaException('Replacement resource cannot be None')

        self._free()
        self.__resource = resource

    def close(self, untrack=True):
        """Free resource and close the object

           Call this method when the object is no longer needed or to free
           the data immediately. It's also automatically called when you
           use with context protocol.
        """
        self._free()
        self._claim(untrack)

    def copy(self):
        """Get independent copy of this resource."""
        resource = self._clone()

        if resource is None:
            tmpl = formattable('{0} _clone method returned None')
            raise PystaciaException(tmpl.format(self.__class__.__name__))

        return self.__class__(resource)

    @property
    def closed(self):
        """Check if instance is already closed.

           Returns ``True`` if object is no longer usable i.e.
           :meth:``pystacia.common.Resource.close`` has been called.
        """
        return self.__resource is None

    @property
    def resource(self):
        """Get underlying C resource.

           You can use this method to get access to raw C struct that you
           can use with :term:`ctypes` calls directly. It can be useful
           when you want to perform custom operations.
        """
        if self.__resource is None:
            tmpl = formattable('{0} already closed.')
            raise PystaciaException(tmpl.format(self.__class__.__name__))

        return self.__resource

    def __del__(self):
        """Automatically free object on GC."""
        if not self.closed:
            self.close()


_registry = WeakValueDictionary()
"""Dictionary keeping references to all resources."""


__lock = Lock()


def _track(resource):
    key = id(resource)
    if key not in _registry:
        with __lock:
            if key not in _registry:
                _registry[key] = resource


def _untrack(resource):
    key = id(resource)
    if key in _registry:
        with __lock:
            if key in _registry:
                del _registry[key]


def _cleanup():
    """Free all tracked instances.

       Closes and destroys all currently allocated resources. This gets called
       from atexit handler just before :term:`ImageMagick` gets uninitialized.
    """
    msg = formattable('Tracked weakrefs: {0}')
    logger.debug(msg.format(len(_registry)))
    alive = 0
    unclosed = 0

    with __lock:
        for obj in _registry.values():
            alive += 1
            if not obj.closed:
                unclosed += 1
                obj.close(untrack=False)

    msg = formattable('Alive weakrefs: {0}')
    logger.debug(msg.format(alive))

    msg = formattable('Unclosed resources: {0}')
    logger.debug(msg.format(unclosed))

    logger.debug('Finished cleanup')

from pystacia import logger
from pystacia.util import PystaciaException
from pystacia.compat import formattable
