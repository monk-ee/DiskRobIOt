#!/usr/bin/env python -u
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


Assumptions:
        if the following is true:
            iops * transfersizeinbytes = bytespersecond
        then
            iops = bytespersecond / transfersizeinbytes

    bytespersecond =
"""

import time
import argparse
import multiprocessing
from random import shuffle
import os
from statistics import mean, median


class DiskRobIOt:
    blocksize = 64
    iterations = 100
    file_iterations = 100
    diff = 0
    file_size = 0
    cleanup = False
    chunk = ""
    path = ""

    def __init__(self, arg):
        try:
            self.blocksize = int(arg.blocksize)
            self.iterations = int(arg.iterations)
            self.file_iterations = int(arg.fileiterations)
            self.path = str(arg.path)
        except:
            raise
        self.file_size = 1024 * self.blocksize * self.file_iterations
        self.chunk = 1024 * self.blocksize
        self._ratioplex()

    def _ratioplex(self, write=2, random=4, sequential=4):
        self.prep_read_files(random, sequential)
        self.output = multiprocessing.Queue()
        self.processes = [multiprocessing.Process(target=self._run_low_writes, args=(x, self.output)) for x in
                          range(write)]
        self.processes += [multiprocessing.Process(target=self._run_reads_rand, args=(x, self.output)) for x in
                           range(random)]
        self.processes += [multiprocessing.Process(target=self._run_reads_seq, args=(x, self.output)) for x in
                           range(sequential)]

        for p in self.processes:
            p.start()
        # Exit the completed processes
        for p in self.processes:
            p.join()
        # Get process results from the output queue
        self.results = [self.output.get() for p in self.processes]
        self._results()

    def prep_read_files(self, random, sequential):
        for count in range(random):
            self._file_write_seq_access(count, "read")
        for count in range(sequential):
            self._file_write_seq_access(count, "read")

    def _run_low_writes(self, thread_id, output):
        start_time = time.perf_counter()
        for iter in range(self.iterations):
            self._raw_file_write_seq_access(thread_id)
        stop_time = time.perf_counter()
        diff = stop_time - start_time
        output.put(diff)

    def _run_reads_seq(self, thread_id, output):
        start_time = time.perf_counter()
        for iter in range(self.iterations):
            self._raw_file_read_seq_access(thread_id)
        stop_time = time.perf_counter()
        diff = stop_time - start_time
        output.put(diff)

    def _run_reads_rand(self, thread_id, output):
        start_time = time.perf_counter()
        for iter in range(self.iterations):
            self._raw_file_read_random_access(thread_id)
        stop_time = time.perf_counter()
        diff = stop_time - start_time
        output.put(diff)

    def _file_write_seq_access(self, thread_id, name="write"):
        chunk = b'\xff' * 1024 * self.blocksize
        with open(self.path + name + "file" + str(thread_id) + ".file", "wb", 0) as f:
            for i in range(self.file_iterations):
                f.write(chunk)
                f.flush()
                os.fsync(f.fileno())
        f.close()

    """
    rawio unbuffered start with close
    """
    def _raw_file_write_seq_access(self, thread_id, name="write"):
        chunkblock = b'\xff' * 1024 * self.blocksize
        with open(self.path + name + "file" + str(thread_id) + ".file", "wb", buffering=0) as f:
            for i in range(self.file_iterations):
                f.write(chunkblock)
                f.flush()
                os.fsync(f.fileno())
        f.close()

    def _raw_file_read_seq_access(self, thread_id):
        locations = list(range(0, self.file_iterations))
        for position in locations:
            f = open(self.path + "readfile" + str(thread_id) + ".file", "rb", buffering=0)
            f.seek((self.chunk * position), 0)
            piece = f.read(self.chunk)
            f.close()
            if not piece:
                break

    def _raw_file_read_random_access(self, thread_id):
        locations = list(range(0, self.file_iterations))
        shuffle(locations)
        for position in locations:
            f = open(self.path + "readfile" + str(thread_id) + ".file", "rb", buffering=0)
            f.seek((self.chunk * position), 0)
            piece = f.read(self.chunk)
            f.close()
            if not piece:
                break

    """
    rawio unbuffered stop
    """

    def _results(self):
        print("Iterations " + str(self.iterations) + " @ " + str(self.blocksize) + 'K blocksize with ' + str(
            self.file_size / 1024 / 1024) + 'Mb File.')
        # now work out write data written
        self._iops = 0
        self._mb = 0
        for result in self.results:
            print(str(self._calculate_mb(result)) + ' Mb/sec ' + str(self._calculate_iops(result)) + ' IOPS')

        meanie = mean(self.results)
        print("Mean: " + str(self._calculate_mb(meanie)) + ' Mb/sec ' + str(self._calculate_iops(meanie)) + ' IOPS')
        medie = median(self.results)
        print("Median: " + str(self._calculate_mb(medie)) + ' Mb/sec ' + str(self._calculate_iops(medie)) + ' IOPS')


    def _calculate_mb(self, result):
        run_ratio = 1 / (result / self.iterations)
        run = run_ratio * self.file_size
        mb = run / 1024 / 1024
        return mb

    def _calculate_iops(self, result):
        run_ratio = 1 / (result / self.iterations)
        iops = (run_ratio * self.iterations)
        # iops = run / self.file_size
        return iops


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A utility for testing disk io.')
    parser.add_argument('--blocksize', default='64', help='The blocksize to write. Defaults to 64(k)')
    parser.add_argument('--fileiterations', default='100',
                        help='The number of iterations of chunked writes. Defaults to 100')
    parser.add_argument('--iterations', default='100', help='The number of times to run the test. Defaults to 100')
    parser.add_argument('--path', default='', help='The path to run the test')

    args = parser.parse_args()
    dr = DiskRobIOt(args)