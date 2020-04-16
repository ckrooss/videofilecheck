#!/usr/bin/env python
# -*- coding: utf-8 -*-


class SubBar:
    """
    ContextManager to create a sub-progressbar from bar:
    - temporarily change the description to the new name
    - set it to the original name after exiting
    """

    def __init__(self, it, bar, name, unit):
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
