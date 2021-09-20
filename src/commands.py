#!/usr/bin/env python3
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


def _name(uid, uid_type):
    """Handler to name() to get the name of a given id. If a uid/gid of 
    an inactive account is provided the original uid or gid is returned.
    @param uid_type <int>:
        Type of identifer, either 'user' or 'group'.
    @params uid_records <dict>:
        Lookup of previously encountered uid/gid.
    @return name <str>:
        Returns the name of the user_id or group_id
    """
    try:
        # Search for id in the unix database
        if uid_type == 'user':
            name = getpwuid(uid).pw_name
        elif uid_type == 'group':
            name = getgrgid(uid).gr_name
    except KeyError:
        # The uid or gid does not exist in unix database.
        # This could be an old user or group that does not
        # exist anymore; however, the file will still 
        # will use the uid or gid in listings with ls.
        # Example:
        # -rw-rw---- 1 39452 CCBR 24931746426 Feb  5  2020 ./rawdata/file.bam
        name = uid 
    return name


def name(uid, uid_type, uid_records):
    """Converts a user_id/group_id into a user_name/group_name while maintaining 
    a local lookup of previously converted ids to prevent redundant unix database search.
    Using a local cache or lookup is about twice as fast and prevents unneccesary hammering of
    the unix user/group database. 'uids' of inactive/deleted users or groups cannot be converted
    so the uid will be returned as the user/group name. 
    @param uid <int>:
        Unique identifer for a user or group.
    @param uid_type <int>:
        Type of identifer, either 'user' or 'group'.
    @params uid_records <dict>:
        Lookup of previously encountered uid/gid.
    @return name <str>:
        Returns the name of the user_id or group_id 
    """
    try:
        # Try searching records/cache of previous lookups
        # to prevent hammering of unix group database.
        # This method is about twice as fast as just
        # converting every id we encounter.
        name = uid_records[uid]
    except KeyError:
        # The uid or gid is not in our records,
        # search the unix group database and add 
        # it to the record of encountered ids.
        name = _name(uid, uid_type) 
        uid_records[uid] = name

    return name 


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

    # Keeps track of previously converte user/group
    # ids to avoid redundant lookups in the unix 
    # user/group database. 
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

            # Get the file's permissions, inode reference, 
            # owner and group name, modified timestamp, and 
            # size of the file in bytes and a human readable
            # format.
            mode = stat_res.st_mode
            permissions = stat.filemode(mode)
            inode = stat_res.st_ino
            owner = name(stat_res.st_uid, 'user', users)
            group = name(stat_res.st_gid, 'group', users)
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