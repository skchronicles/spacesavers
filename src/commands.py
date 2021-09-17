#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python standard library
from __future__ import print_function, division
import os, stat, datetime, math
from pwd import getpwuid  # convert uid to user name
from grp import getgrgid  # convert gid to group name  

# Local imports
from utils import fatal, err
from shells import bash


def normalized(path):
    """Normalizes a given path on the filesystem.
    @param path <str>:
        Path on the file sytem
    @return npath <str>:
        Returns a normalized and absolute path
    """
    # Normalize references to home directory alias ("~")
    npath = os.path.expanduser(path)
    # Convert relative paths
    npath = os.path.abspath(npath)

    return npath 


def readable_size(sbytes):
    """Converts bytes into a human readable size. Size is reported in units
    based on powers of 2 (where one KiB is 1024 bytes).
    @param sbytes <int>:
        Size in bytes
    @return size <str>:
        Returns human readable size
    """
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")

    # Prevents math domain error when taking log of 0
    if sbytes <= 0:
        return "0 B"    
    
    i = int(math.floor(math.log(sbytes, 1024)))
    p = math.pow(1024, i)
    size = "{} {}".format(round(sbytes / p, 3), units[i])
    
    return size


def _ls(path, md5=False):
    """Private function for spacesavers ls() which recursively lists
    information about files and directories for a given path.
    @param path <str>:
        Path to recusively list directory contents
    @param md5 <bool>:
        Report MD5 of potential duplicates
    """
    # Normalize path
    path = normalized(path)

    # Convert userids to groupids
    users = {}

    # Recursively descend the directory tree
    # and list information about its files
    for pdir, chdirs, files in os.walk(path):
        for f in files:
            # Get absolute referece to file  
            file = os.path.join(pdir, f)
            # Use os.stat() in the standard library to
            # get detailed information about the file: 
            # https://docs.python.org/3/library/stat.html
            # Results are similar to the unix cmd stat
            try:
                stat_res = os.stat(file)
            except Exception as e:
                # Possible errors inlcude 
                err('WARNING: Failed to get info on "{}" due to "{}" error!'.format(file, e))
                continue   # goto next file
            
            mode = stat_res.st_mode
            permissions = stat.filemode(mode)
            inode = stat_res.st_ino
            owner = stat_res.st_uid  # TODO: convert id to name later
            group = stat_res.st_gid  # TODO: convert id to name later
            mdate = datetime.datetime.fromtimestamp(stat_res.st_mtime).strftime('%Y-%m-%d-%H:%M')
            bsize = stat_res.st_size
            hsize = readable_size(bsize)
            # Format results before printing to standard 
            # output and convert all values to strings 
            info = [inode, permissions, owner, group, bsize, hsize, mdate, file]
            info = [str(val) for val in info]
            print('{}'.format('\t'.join(info)))

    return


if __name__ == '__main__':
    # Add tests later
    pass