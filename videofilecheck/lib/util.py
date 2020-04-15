"""class FakeBar:
    def __init__(self):
        self.desc = ""
        self.unit = None
        self.unit_scale = None
        self.value = 0

    def reset(self, n=0):
        self.total = n

    def update(self, n=1):
        self.value += n

    def refresh(self, *args):
        pass
"""


class SubBar:
    def __init__(self, it, bar, name, unit):
        """if bar is None or bar.disable:
            bar = FakeBar()"""

        self.bar = bar
        iterlen = 0
        try:
            it.seek(0, 2)
            iterlen = it.tell()
            it.seek(0)
        except Exception:
            iterlen = len(it)

        bar.n = 0
        bar.total = iterlen
        self.original_desc = bar.desc
        bar.desc = bar.desc + "[%6.6s]" % name
        bar.unit = unit
        bar.unit_scale = True
        self.bar = bar

    def __enter__(self):
        return self.bar

    def __exit__(self, *args):
        self.bar.desc = self.original_desc
        return
