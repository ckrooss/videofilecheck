#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import tqdm


class TqdmHandler(logging.Handler):
    """
    Use tqdm.write for logging:
    Allows python logging to work without glitches while a tqdm progress bar is visible
    """

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)
