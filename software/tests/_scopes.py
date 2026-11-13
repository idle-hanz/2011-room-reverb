"""Put slow tests in their own classes so pytest-xdist loadscope can split them.

A function stays on the module's one worker. A method goes with its class.
The test function objects are unchanged, so the assertions stay the same.
"""
from __future__ import annotations


def isolate(module_globals, groups) -> None:
    module_name = module_globals["__name__"]
    for index, names in enumerate(groups):
        methods = {}
        for name in names:
            methods[name] = staticmethod(module_globals[name])
        class_name = "TestScope" + str(index)
        cls = type(class_name, (), methods)
        cls.__module__ = module_name
        cls.__test__ = True
        module_globals[class_name] = cls
        for name in names:
            del module_globals[name]


def find(module_globals, name):
    """Look up a test after isolate() moved it onto a class. Used by script entry points."""
    fn = module_globals.get(name)
    if callable(fn):
        return fn
    for obj in module_globals.values():
        if isinstance(obj, type) and obj.__name__.startswith("TestScope") and name in obj.__dict__:
            return getattr(obj, name)
    raise KeyError(name)
