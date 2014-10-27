#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Monkee Magic <magic.monkee.magic@gmail.com>'
__version__ = '0.0.1'
__license__ = 'GPLv3'
__source__ = 'http://github.com/monk-ee/diskrobiot'

"""
diskrobiot.py - A python library for disk IO testing.

Copyright (C) 2014 Lyndon Swan <magic.monkee.magic@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

"""

import time
import argparse
import multiprocessing


class DiskRobIOt:
    blocksize = 64
    iterations = 100
    threads = 2
    diff = 0

    def __init__(self, arg):
        try:
            self.blocksize = int(arg.blocksize)
            self.iterations = int(arg.iterations)
            self.threads = int(arg.threads)
        except:
            raise

        self.output = multiprocessing.Queue()
        self.processes = [multiprocessing.Process(target=self._run, args=(x, self.output)) for x in range(int(self.threads))]
        for p in self.processes:
            p.start()
        # Exit the completed processes
        for p in self.processes:
            p.join()

        # Get process results from the output queue
        self.results = [self.output.get() for p in self.processes]
        self._results()

    def _run(self, thread_id, output):
        start_time = time.perf_counter()
        self._file_write_seq_access(thread_id)
        stop_time = time.perf_counter()
        diff = stop_time - start_time
        output.put(diff)

    def _file_write_seq_access(self, thread_id):
        chunk = b'\xff' * 1024 * self.blocksize
        with open("file" + str(thread_id) + ".file", "wb") as f:
            for i in range(self.iterations):
                f.write(chunk)
        f.close()

    def _results(self):
        # now work out write data written
        file_size = 1024 * self.blocksize * self.iterations
        for result in self.results:
            run_speed = 1 / result
            run = run_speed * file_size
            mb = run / 1024 / 1024
            print(str(mb) + ' Mb/sec with ' + str(self.blocksize) + 'K blocksize.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A utility for testing disk io.')
    parser.add_argument('--blocksize', default='64', help='The blocksize to write. Defaults to 64(k)')
    parser.add_argument('--iterations', default='100', help='The number of iterations of chunked writes. Defaults to 100')
    parser.add_argument('--threads', default='1', help='The number of threads. Defaults to single threaded.')
    args = parser.parse_args()
    dr = DiskRobIOt(args)