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


    usage: DiskRobIOt.py [-h] [--blocksize BLOCKSIZE]

                         [--fileiterations FILEITERATIONS]

                         [--iterations ITERATIONS] [--path PATH]


    A utility for testing disk io.

    optional arguments:

    -h, --help            show this help message and exit

    --blocksize BLOCKSIZE

                            The blocksize to write. Defaults to 64(k)

    --fileiterations FILEITERATIONS

                            The number of iterations of chunked writes. Defaults

                            to 100

    --iterations ITERATIONS

                           The number of times to run the test. Defaults to 100

    --path PATH               The path to run the test