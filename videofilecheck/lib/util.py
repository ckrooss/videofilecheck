class FakeBar:
    def __init__(self):
        self.desc = ""
        self.unit = None
        self.unit_scale = None

    def reset(self, *args):
        pass

    def update(self, *args):
        pass

    def refresh(self, *args):
        pass

class SubBar:
    def __init__(self, it, bar, name, unit):
        if bar is None:
            bar = FakeBar()

        self.bar = bar
        try:
            it.seek(0, 2)
            iterlen = it.tell()
            it.seek(0)
        except:
            iterlen = len(iterable)

        bar.reset(iterlen)
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
