[![Build Status](https://travis-ci.org/ckrooss/videofilecheck.svg?branch=master)](https://travis-ci.org/ckrooss/videofilecheck)
# Video File Check
Checks video files for errors and records results. Supports continuing a canceled scan and
partial scans for updated files.

# What it does
Recurse into a directory that contains media files.
Calculate a hash for each file and try to decode the file as fast as possible using ffmpeg.
Any decoding errors are recorded and mark the file as "bad".

The results are stored in a JSON file for viewing and for resuming/updating the same data later.
Results are only updated when the file hash has changed.

# Usage Example
```
~ $ vcheck scan /mnt/videofiles
2019-12-29 16:23:25 [videofilecheck.lib.database] [INFO] dbpath is ~/.vcheck_db.json
2019-12-29 16:23:25 [videofilecheck.lib.database] [INFO] Loading existing database with 3 entries
2019-12-29 16:23:25 [videofilecheck.videofilecheck] [INFO] Settings: nthreads=2 dbpath=~/.vcheck_db.json output=results.txt force_rescan=False path_only=False
2019-12-29 16:23:25 [videofilecheck.videofilecheck] [INFO] Found 3 videofiles in total
2019-12-29 16:23:25 [videofilecheck.videofilecheck] [INFO] Calculating md5 of seriesA/S01E02.mkv
2019-12-29 16:23:25 [videofilecheck.videofilecheck] [INFO] Calculating md5 of seriesA/S01E01.mkv
2019-12-29 16:23:26 [videofilecheck.videofilecheck] [INFO] Found "seriesA/S01E02.mkv" in db, hash matches, using old status "FAILED"
2019-12-29 16:23:26 [videofilecheck.videofilecheck] [INFO] Calculating md5 of seriesB/S08E11.avi
2019-12-29 16:23:26 [videofilecheck.videofilecheck] [WARNING] FFMPEG decoding FAILED: seriesA/S01E02.mkv
2019-12-29 16:23:26 [videofilecheck.videofilecheck] [INFO] Found "seriesA/S01E01.mkv" in db, hash matches, using old status "OK"
2019-12-29 16:23:26 [videofilecheck.videofilecheck] [INFO] Found "seriesB/S08E11.avi" in db, hash matches, using old status "OK"

~ $ cat results.txt
FAILED seriesA/S01E02.mkv
  OK   seriesA/S01E01.mkv
  OK   seriesB/S08E11.avi
```

# Parameters
```
usage: vcheck [-h] [-n NTHREADS] [-d DBPATH] [-o OUTPUT] [-f] [-p] [-v | -q] command videodir

positional arguments:
  command               Subcommand to run: scan, show
  videodir              Directory that will be recursively scanned

optional arguments:
  -h, --help            show this help message and exit
  -n NTHREADS, --nthreads NTHREADS
                        Number of threads to run in parallel (Default: 2)
  -d DBPATH, --dbpath DBPATH
                        Database path to use to store results (Default: ~/.vcheck_db.json)
  -o OUTPUT, --output OUTPUT
                        Output textfile to store the human readable results (Default: ./results.txt)
  -f, --force-rescan    Rescan every file, even if it has been scanned before (Default: No)
  -p, --path-only       Only scan files using their path, skip hashing file content (Default: No)
  -v, --verbose         log more
  -q, --quiet           log less
```
