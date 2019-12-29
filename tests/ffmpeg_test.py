#!/usr/bin/env python
# -*- coding: utf-8 -*-
from videofilecheck.lib.ffmpeg import ffmpeg_no_errors, remove_ignored_stuff


def test_nothing_ignored():
    source = " my\nsrc\nstring "
    result = remove_ignored_stuff(source)
    assert(source == result)


def test_everything_ignored():
    source = \
        """[null @ 0x55b005a3df00] Application provided invalid, non monotonically increasing dts to muxer in stream 0: 2500 >= 2500\n""" \
        """[null @ 0x55b005a3df00] Application provided invalid, non monotonically increasing dts to muxer in stream 0: 2502 >= 2502\n""" \
        """[null @ 0x55b005a3df00] Application provided invalid, non monotonically increasing dts to muxer in stream 0: 2504 >= 2504\n"""

    result = remove_ignored_stuff(source)
    result = result.strip()
    assert(len(result) == 0)


def test_half_ignored():
    source = \
        """[null @ 0x55b005a3df00] Application provided invalid, non monotonically increasing dts to muxer in stream 0: 2500 >= 2500\n""" \
        """Lorem Ipsum\n""" \
        """Dolor Sit\n""" \
        """[null @ 0x55b005a3df00] Application provided invalid, non monotonically increasing dts to muxer in stream 0: 2504 >= 2504\n"""

    result = remove_ignored_stuff(source)
    result = result.strip()
    assert(len(result) != 0)
