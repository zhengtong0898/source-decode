#!/usr/bin/env python
import argparse
import subprocess
import sys
from pathlib import Path

js_path = Path(__file__).parents[1] / 'static' / 'admin' / 'js'


def main():
    description = """With no file paths given this script will automatically
compress files of the admin app. Requires the Google Closure Compiler library
and Java version 7 or later."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('file', nargs='*')
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_argument("-q", "--quiet", action="store_false", dest="verbose")
    options = parser.parse_args()

    if not options.file:
        if options.verbose:
            sys.stdout.write("No filenames given; defaulting to admin scripts\n")
        files = [
            js_path / f
            for f in ["actions.js", "collapse.js", "inlines.js", "prepopulate.js"]
        ]
    else:
        files = [Path(f) for f in options.file]

    for file_path in files:
        to_compress = file_path.expanduser()
        if to_compress.exists():
            to_compress_min = to_compress.with_suffix('.min.js')
            cmd = ['npx']
            if not options.verbose:
                cmd.append('-q')
            cmd.extend([
                'google-closure-compiler',
                '--language_out=ECMASCRIPT_2015',
                '--rewrite_polyfills=false',
                '--js', str(to_compress),
                '--js_output_file', str(to_compress_min),
            ])
            if options.verbose:
                sys.stdout.write("Running: %s\n" % ' '.join(cmd))
            subprocess.run(cmd)
        else:
            sys.stdout.write("File %s not found. Sure it exists?\n" % to_compress)


if __name__ == '__main__':
    main()
