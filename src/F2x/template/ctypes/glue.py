"""
F2x 'ctypes' template glue library.

This module contains helpers that are used by the code generated by the 'ctypes' library. It mainly deals with setting
correct C interfaces and converting values between FORTRAN and Python types. Arrays are handled by NumPy.

Usually there should be no need to access this module directly.
"""

import ctypes

import numpy


def constructor(cfunc):
    """
    Make a C function a constructor.

    The C interface is defined to accept no parameters and return a void pointer. It is also wrapped as a staticmethod
    to allow usage in classes.

    :param cfunc: The plain C function as imported from the C library using ctypes.
    :return: A static method with appropriate C interface.
    """
    cfunc.argtypes = []
    cfunc.restype = ctypes.c_void_p
    return staticmethod(cfunc)


def destructor(cfunc):
    """
    Make a C function a destructor.

    Destructors accept pointers to void pointers as argument. They are also wrapped as a staticmethod for usage in
    classes.

    :param cfunc: The C function as imported by ctypes.
    :return: The configured destructor.
    """
    cfunc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    cfunc.restype = None
    return staticmethod(cfunc)


def array_from_pointer(ctype, dims, ptr):
    """
    Helper that converts a pointer to a ctypes array.

    The array will have flat layout.

    :param ctype: Type of the contents of the array.
    :param dims: List with the current sizes of the array.
    :param ptr: Address of array memory.
    :return: A ctypes array that points to the referred data.
    """
    array_size = 1
    for size in dims:
        array_size *= size

    array_type = ctype * array_size
    return array_type.from_address(ctypes.addressof(ptr.contents))


class NullPointerError(BaseException):
    """
    This exception is raised when Python wrapper code tries to access a C pointer that was not (yet) allocated (i.e. is
    null). This exception is handled to automatically allocate dynamic arrays upon first assignment.
    """
    pass


def _getter(ctype, cfunc):
    if issubclass(ctype, FType):
        cfunc.argtypes = [ctypes.c_void_p]
        cfunc.restype = ctypes.c_void_p

        def _get(ptr):
            cptr = cfunc(ptr)
            if cptr is None:
                raise NullPointerError()
            return ctype(ctypes.c_void_p(cptr), False)

        return _get

    elif ctype == ctypes.c_char_p:
        cfunc.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
        cfunc.restype = None

        def _get(ptr):
            cptr = ctypes.c_char_p(0)
            cfunc(ptr, ctypes.byref(cptr))
            return cptr.value.decode('utf-8').rstrip()

        return _get

    else:
        cfunc.argtypes = [ctypes.c_void_p]
        cfunc.restype = ctype
        return cfunc


def _setter(ctype, cfunc, strlen=None):
    if cfunc is None:
        return None

    elif ctype == ctypes.c_char_p:
        cfunc.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctype)]
        cfunc.restype = None

        def _set(ptr, value):
            cstring = ctypes.create_string_buffer(value.encode('utf-8'), strlen)
            cvalue = ctypes.cast(cstring, ctypes.c_char_p)
            cfunc(ptr, ctypes.byref(cvalue))

        return _set

    else:
        cfunc.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctype)]
        cfunc.restype = None

        def _set(ptr, value):
            cvalue = ctype(value)
            cfunc(ptr, ctypes.byref(cvalue))

        return _set


def _allocator(ctype, cfunc):
    if cfunc is None:
        return None

    cfunc.argtypes = [ctypes.c_void_p]
    cfunc.restype = None
    return cfunc


class Field(object):
    def __init__(self, ctype, getter, setter=None, allocator=None, strlen=None):
        self.ctype = ctype
        self.getter = _getter(ctype, getter)
        self.setter = _setter(ctype, setter, strlen)
        self.allocator = _allocator(ctype, allocator)

    def __get__(self, instance, owner):
        if instance is None:
            return self

        try:
            return self.getter(instance.ptr)

        except NullPointerError:
            self.allocator(instance.ptr)
            return self.getter(instance.ptr)

    def __set__(self, instance, value):
        if self.setter:
            self.setter(instance.ptr, value)

        elif issubclass(self.ctype, FType):
            try:
                target = self.getter(instance.ptr)
            except NullPointerError:
                self.allocator(instance.ptr)
                target = self.getter(instance.ptr)
            target.copy_from(value)

        else:
            raise AttributeError("Not settable.")


def _global_getter(ctype, cfunc):
    if issubclass(ctype, FType):
        cfunc.argtypes = []
        cfunc.restype = ctypes.c_void_p

        def _get():
            cptr = cfunc()
            if cptr is None:
                raise NullPointerError()
            return ctype(ctypes.c_void_p(cptr), False)

        return _get

    elif ctype == ctypes.c_char_p:
        cfunc.argtypes = [ctypes.POINTER(ctypes.c_char_p)]
        cfunc.restype = None

        def _get():
            cptr = ctypes.c_char_p(0)
            cfunc(ctypes.byref(cptr))
            return cptr.value.decode('utf-8').rstrip()

        return _get

    else:
        cfunc.argtypes = []
        cfunc.restype = ctype
        return cfunc


def _global_setter(ctype, cfunc, strlen=None):
    if cfunc is None:
        return None

    elif ctype == ctypes.c_char_p:
        cfunc.argtypes = [ctypes.POINTER(ctype)]
        cfunc.restype = None

        def _set(value):
            cstring = ctypes.create_string_buffer(value.encode('utf-8'), strlen)
            cvalue = ctypes.cast(cstring, ctypes.c_char_p)
            cfunc(ctypes.byref(cvalue))

        return _set

    else:
        cfunc.argtypes = [ctypes.POINTER(ctype)]
        cfunc.restype = None

        def _set(value):
            cvalue = ctype(value)
            cfunc(ctypes.byref(cvalue))

        return _set


def _global_allocator(ctype, cfunc):
    if cfunc is None:
        return None

    cfunc.argtypes = []
    cfunc.restype = None
    return cfunc


class Global(Field):
    def __init__(self, ctype, getter, setter=None, allocator=None, strlen=None):
        self.ctype = ctype
        self.getter = _global_getter(ctype, getter)
        self.setter = _global_setter(ctype, setter, strlen)
        self.allocator = _global_allocator(ctype, allocator)

    def __get__(self, instance, owner):
        if instance is None:
            return self

        try:
            return self.getter()

        except NullPointerError:
            self.allocator()
            return self.getter()

    def __set__(self, instance, value):
        if self.setter:
            self.setter(value)

        elif issubclass(self.ctype, FType):
            try:
                target = self.getter()
            except NullPointerError:
                self.allocator()
                target = self.getter()
            target.copy_from(value)

        else:
            raise AttributeError("Not settable.")


class FTypeFieldArray(object):
    def __init__(self, field, ptr):
        self.field = field
        self.ptr = ptr

    def __len__(self):
        return self.field.dims[0]

    def __getitem__(self, index):
        if not isinstance(index, (list, tuple)):
            return self[(index, )]

        return self.field.getter(self.ptr, index)

    def __setitem__(self, index, value):
        if not isinstance(index, (list, tuple)):
            self[(index, )] = value

        self[index].copy_from(value)
    
    def allocate(self, sizes):
        self.field.allocator(sizes)


def _array_getter(name, ctype, cfunc):
    if issubclass(ctype, FType):
        cfunc.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_int32))]
        cfunc.restype = ctypes.c_void_p

        def _get(instance, index):
            index = (ctypes.c_int32 * len(instance.dims[name]))(*index)
            cindex = ctypes.cast(index, ctypes.POINTER(ctypes.c_int32))
            cptr = cfunc(instance.ptr, ctypes.byref(cindex))
            return ctype(cptr, False)

        return _get

    else:
        cfunc.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(ctype))]
        cfunc.restype = None

        def _get(instance):
            cptr = ctypes.POINTER(ctype)()
            cfunc(instance.ptr, ctypes.byref(cptr))
            try:
                carray = array_from_pointer(ctype, instance.dims[name], cptr)
            except ValueError:
                raise NullPointerError

            return numpy.ndarray(instance.dims[name], ctype, carray, order='F')

        return _get


def _array_allocator(name, cfunc):
    if cfunc is None:
        return

    cfunc.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_int32))]
    cfunc.restype = None

    def _alloc(instance, sizes):
        csizes = (ctypes.c_int32 * len(instance.dims[name]))(*sizes)
        cptr = ctypes.cast(csizes, ctypes.POINTER(ctypes.c_int32))
        cfunc(instance.ptr, ctypes.byref(cptr))
        instance.dims[name][:] = sizes

    return _alloc


class ArrayField(object):
    def __init__(self, name, ctype, dims, getter, allocator=None):
        self.name = name
        self.ctype = ctype
        self.dims = dims
        self.getter = _array_getter(self.name, self.ctype, getter)
        self.allocator = _array_allocator(self.name, allocator)

    def __get__(self, instance, owner):
        if issubclass(self.ctype, FType):
            return FTypeFieldArray(self, instance)

        else:
            return self.getter(instance)

    def __set__(self, instance, value):
        if issubclass(self.ctype, FType):
            array = FTypeFieldArray(self, instance)
            for target, source in zip(array, value):
                target.copy_from(source)

        else:
            try:
                array = self.getter(instance)
            except NullPointerError:
                value = numpy.array(value)
                self.allocator(instance, value.shape)
                array = self.getter(instance)

            array[:] = value


def _global_array_getter(name, ctype, cfunc):
    if issubclass(ctype, FType):
        cfunc.argtypes = [ctypes.POINTER(ctypes.POINTER(ctypes.c_int32))]
        cfunc.restype = ctypes.c_void_p

        def _get(instance, index):
            index = (ctypes.c_int32 * len(instance.dims[name]))(*index)
            cindex = ctypes.cast(index, ctypes.POINTER(ctypes.c_int32))
            cptr = cfunc(ctypes.byref(cindex))
            return ctype(cptr, False)

        return _get

    else:
        cfunc.argtypes = [ctypes.POINTER(ctypes.POINTER(ctype))]
        cfunc.restype = None

        def _get(instance):
            cptr = ctypes.POINTER(ctype)()
            cfunc(ctypes.byref(cptr))
            try:
                carray = array_from_pointer(ctype, instance.dims[name], cptr)
            except ValueError:
                raise NullPointerError

            return numpy.ndarray(instance.dims[name], ctype, carray, order='F')

        return _get


def _global_array_allocator(name, cfunc):
    if cfunc is None:
        return

    cfunc.argtypes = [ctypes.POINTER(ctypes.POINTER(ctypes.c_int32))]
    cfunc.restype = None

    def _alloc(instance, sizes):
        csizes = (ctypes.c_int32 * len(instance.dims[name]))(*sizes)
        cptr = ctypes.cast(csizes, ctypes.POINTER(ctypes.c_int32))
        cfunc(ctypes.byref(cptr))
        instance.dims[name][:] = sizes

    return _alloc


class ArrayGlobal(ArrayField):
    def __init__(self, name, ctype, dims, getter, allocator=None):
        self.name = name
        self.ctype = ctype
        self.dims = dims
        self.getter = _global_array_getter(self.name, self.ctype, getter)
        self.allocator = _global_array_allocator(self.name, allocator)

    def __get__(self, instance, owner):
        if issubclass(self.ctype, FType):
            return FTypeFieldArray(self, instance)

        else:
            return self.getter(instance)

    def __set__(self, instance, value):
        if issubclass(self.ctype, FType):
            array = FTypeFieldArray(self, instance)
            for target, source in zip(array, value):
                target.copy_from(source)

        else:
            try:
                array = self.getter(instance)
            except NullPointerError:
                value = numpy.array(value)
                self.allocator(instance, value.shape)
                array = self.getter(instance)

            array[:] = value


class FType(object):
    _new = None
    _free = None

    def __init__(self, cptr=None, owned=None, **kwargs):
        if cptr is None:
            self.ptr = ctypes.c_void_p(self._new())
            self.owned = owned if owned is not None else True

        else:
            self.ptr = cptr
            self.owned = owned if owned is not None else False

        self.dims = {
            name: list(field.dims)
            for name, field in self.fields(ArrayField)
        }

        for name, value in kwargs.items():
            setattr(self, name, value)

    def __del__(self):
        if self.owned:
            self.owned = False
            self._free(ctypes.byref(self.ptr))

    def copy_from(self, other):
        for name, _ in self.fields():
            try:
                value = getattr(other, name)
            except (UnicodeDecodeError, ValueError, NullPointerError):
                continue

            setattr(self, name, value)

    @classmethod
    def fields(cls, types=(Field, ArrayField)):
        for name, field in cls.__dict__.items():
            if isinstance(field, types):
                yield name, field
