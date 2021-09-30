#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Python standard library
from __future__ import print_function
import time


def timer(func):
    """Decorator that calculates how long a function takes to run.
    The elapsed time is printed to standard output.
    @param func <func>:
        Function to time
    """
    def timed(*args, **kw):
        # Start time
        ts = time.time()
        # Run target function
        result = func(*args, **kw)
        # End time
        te = time.time()
        print('{}\t{} ms'.format(func.__name__, (te - ts) * 1000)) 
        return result
    return timed


if __name__ == '__main__':
    # Add test later
    print('Generating a random string of length 64: {}'.format(random_string()))