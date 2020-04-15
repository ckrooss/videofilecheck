#!/usr/bin/env python
# -*- coding: utf-8 -*-
from time import time, sleep
from os import walk, chdir, nice
from os.path import join, expanduser, relpath, abspath, getsize, isfile
from concurrent.futures import ThreadPoolExecutor as Executor, as_completed
import argparse
from tqdm import tqdm
from threading import get_ident, Lock

from .lib.database import Database
from .lib.ffmpeg import ffmpeg_scan, ffmpeg_remux
from .lib.checksum import checksum
from .lib.cache import CachedFile, UnCachedFile
from .lib.tqdmlog import TqdmHandler

import logging

formatter = logging.Formatter(fmt="%(asctime)s [%(name)-30s] [%(levelname)-8s] %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S")
handler = TqdmHandler(logging.NOTSET)
handler.setFormatter(formatter)
log = logging.getLogger("videofilecheck")
log.addHandler(handler)

WANTED_FILES = [".mkv", ".mp4", ".avi"]


class App:
    def __init__(self, config):
        self.nthreads = int(config.nthreads) if config.nthreads is not None else 2
        self.dbpath = abspath(expanduser(config.dbpath) if config.dbpath is not None else expanduser("~/.vcheck.json"))
        self.db = Database(self.dbpath)
        self.force_rescan = config.force_rescan if config.force_rescan is not None else False
        self.path_only = config.path_only if config.path_only is not None else False
        self.verbose = True if config.verbose else False
        self.worker_ids = []
        self.lock = Lock()

        log.debug(
            "Settings: nthreads=%s dbpath=%s force_rescan=%s path_only=%s"
            % (self.nthreads, self.dbpath, self.force_rescan, self.path_only)
        )

    def get_worker_idx(self):
        thread_id = get_ident()

        with self.lock:
            if thread_id not in self.worker_ids:
                self.worker_ids.append(thread_id)

        return self.worker_ids.index(thread_id) + 1

    def find_video_files(self, rootdir):
        videofiles = []

        for root, subdirs, files in walk(rootdir):

            for file in files:
                if any(file.endswith(ext) for ext in WANTED_FILES):
                    videofiles.append(join(root, file))
                else:
                    continue

            idx = 0
            while idx < len(subdirs):
                if subdirs[idx].startswith("@") or subdirs[idx].startswith(".Trash"):
                    subdirs.remove(subdirs[idx])
                    idx = 0
                else:
                    idx += 1

        # make path relative to rootdir so e.g. the mountpoint does not invalidate the cache
        videofiles = sorted([relpath(p, rootdir) for p in videofiles])
        return videofiles

    def store_result_to_db(self, videofile, filehash, result):
        # limit result to 10 lines of output
        out_lines = "\n".join(result.output.splitlines()[:10])
        entry = dict(
            videofile=videofile, hash=filehash, status=result.success, timestamp=int(time()), filesize=getsize(videofile), output=out_lines
        )

        self.db.set(entry)
        self.db.flush()

    def worker(self, videofile):
        try:
            worker_idx = self.get_worker_idx()

            thread_title = "Thread #%s - %50.50s" % (worker_idx, videofile.split("/")[-1])
            with tqdm(position=worker_idx, leave=False) as bar:

                bar.desc = thread_title

                with CachedFile(videofile, bar) as vid:
                    if self.path_only:
                        filehash = None
                    else:
                        filehash = checksum(vid.cached, bar=bar)

                    db_result = self.db.get(vid.original, filehash, getsize(videofile))

                    if self.force_rescan:
                        log.debug('Forcing a rescan for "%s"' % vid.original)
                        db_result = None

                    if db_result is None:
                        result = ffmpeg_scan(vid.cached, bar)
                        if filehash is None:
                            filehash = checksum(vid.cached, bar=bar)

                        if result.success:
                            log.info("%s - OK" % vid.original)
                        else:
                            log.info("%s - FAIL" % vid.original)
                        self.store_result_to_db(vid.original, filehash, result)
                        return (vid.original, result.success)
                    else:
                        log.debug('Found "%s" in db, using old status %s' % (vid.original, db_result))
                        return (vid.original, db_result)
        except Exception:
            import traceback
            traceback.print_exc()

    def scan(self, videodir):
        """Scan videofiles in videodir recursively. Ignore existing results if force is set"""

        if isfile(videodir):
            with tqdm() as bar:
                print(ffmpeg_scan(videodir, bar))
                return

        chdir(videodir)
        vfiles = self.find_video_files(".")
        log.debug("Found %s videofiles in total" % len(vfiles))

        with Executor(max_workers=self.nthreads) as exe:
            futures = [exe.submit(self.worker, vfile) for vfile in vfiles]

            failed = []

            for future in tqdm(as_completed(futures), total=len(vfiles), unit="file"):
                sleep(0.001)  # TQDM doesnt update without a very short sleep :/
                if future.exception() is not None:
                    log.error(future.exception())
                    continue

                vfile, success = future.result()
                if not success:
                    failed.append(vfile)

            for vfile in failed:
                log.warning("FAILED: %s" % vfile)

            self.db.flush()

    def rescan(self, videodir):
        """Rescan all files in videodir that have a previous status of FAILED"""
        if isfile(videodir):
            print(ffmpeg_scan(videodir))
            return

        chdir(videodir)
        vfiles = self.find_video_files(".")

        for vfile in vfiles:
            db_result = self.db.get(vfile)

            if db_result is not None and db_result is False:
                log.debug("Rescanning previously failed file %s" % vfile)
                self.db.delete(vfile)

        self.scan(videodir)

    def show(self):
        log.info("Broken Files:")
        n_broken = 0
        n_ok = 0
        for _, entry in sorted(self.db.get_all()):
            if entry["status"] is False:
                log.info(entry["videofile"])
                if "output" in entry:
                    for l in entry["output"].splitlines():
                        log.info("> " + l)
                n_broken += 1
            else:
                n_ok += 1

        log.info(
            "Found issues with %s/%s files (%.1f%%)"
            % (n_broken, n_broken + n_ok, 100 * float(n_broken) / (n_broken + n_ok))
        )


def cli():
    nice(15)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="command", help="Command", dest="command")
    scanning_parsers = [subparsers.add_parser("scan"), subparsers.add_parser("rescan"), subparsers.add_parser("remux")]
    all_parsers = [*scanning_parsers, subparsers.add_parser("show")]

    for p in scanning_parsers:
        p.add_argument("videodir", help="Directory that will be recursively scanned")

    for p in all_parsers:
        p.add_argument("-v", "--verbose", help="log more", action="store_true")
        p.add_argument("-n", "--nthreads", help="Number of threads to run in parallel (Default: 2)")
        p.add_argument("-d", "--dbpath", help="Database path to use to store results (Default: ~/.vcheck.json)")
        p.add_argument(
            "-f",
            "--force-rescan",
            help="Rescan every file, even if it has been scanned before (Default: No)",
            action="store_true",
        )
        p.add_argument(
            "-p",
            "--path-only",
            help="Only scan files using their path, skip hashing file content (Default: No)",
            action="store_true",
        )

    args = parser.parse_args()

    baselogger = logging.getLogger("videofilecheck")
    if args.verbose:
        baselogger.setLevel(logging.DEBUG)
    else:
        baselogger.setLevel(logging.INFO)

    app = App(args)

    if args.command == "scan":
        log.info("Running scan on video(s) at %s" % args.videodir)
        app.scan(args.videodir)
    elif args.command == "rescan":
        log.info("Running rescan on video(s) at %s" % args.videodir)
        app.rescan(args.videodir)
    elif args.command == "show":
        log.info("Showing results")
        app.show()
    elif args.command == "remux":
        log.info("Remuxing %s" % args.videodir)
        ffmpeg_remux(file=args.videodir)
    else:
        parser.print_usage()
        exit(1)
