import importlib


class _LazyModule:
    __slots__ = ("_name", "_module")

    def __init__(self, name):
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_module", None)

    def _load(self):
        mod = object.__getattribute__(self, "_module")
        if mod is None:
            name = object.__getattribute__(self, "_name")
            mod = importlib.import_module(name)
            object.__setattr__(self, "_module", mod)
        return mod

    def __getattr__(self, attr):
        return getattr(self._load(), attr)

    def __repr__(self):
        name = object.__getattribute__(self, "_name")
        mod = object.__getattribute__(self, "_module")
        if mod is None:
            return f"<LazyModule '{name}' (not loaded)>"
        return repr(mod)


np = _LazyModule("numpy")
scipy_stats = _LazyModule("scipy.stats")
pd = _LazyModule("pandas")
