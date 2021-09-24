#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Python standard library
from __future__ import print_function, division
import os, stat, datetime, math
from pwd import getpwuid  # convert uid to user name
from grp import getgrgid  # convert gid to group name  

# Local imports
from utils import fatal, err, md5sum
from shells import bash


def normalized(path):
    """Normalizes a given path on the filesystem. Symlinks will be
    dereferenced along with path aliases like "~". 
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


def file_stats(file, users):
    """Gets detailed information about a file using os.stat(). Returns a list containing
    a file's inode, permissions, owner, group, bytes_size, human_readable_size, 
    modification_date.
    @param file <str>:
        Name of file to get detailed information
    @params users <dict>:
        Lookup of previously encountered uid/gid.
    @returns info <list>:
        List containing detailed information about a file:
            0=inode, 1=permissions, 3=owner, 4=group, 5=bsize, 6=hsize, 7=mdate
    """
    # Use os.stat() in the standard library to
    # get detailed information about the file: 
    # https://docs.python.org/3/library/stat.html
    # Results are similar to the unix cmd stat
    try:
        stat_res = os.stat(file)
    except Exception as e:
        # Possible errors include permissions
        # issues or non-existent file 
        err('WARNING: Failed to get info on "{}" due to "{}" error!'.format(file, e))
        return []   # cannot get stats
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
    info = [inode, permissions, owner, group, bsize, hsize, mdate]
    info = [str(val) for val in info]

    return info


def dereferenced(files):
    """Filters a list of files with multiple references
    to the same inode. A list of files with multiple
    hardlinks will be filtered so only one reference 
    to an inode will be preserved.
    @params files <list>:
        A list of files to filter for hardlinks
    @returns unique_files <list>:
        A filterfed list of files where only one 
        reference to an inode is preserved
    """
    # Set to keep track of hard links
    # {inodeX, inodeY, inodeZ, ...}
    inodes = set()
    unique_files = []

    for file in files:
        inode = os.stat(file).st_ino
        if inode not in inodes:
            # First occurence of inode, preserve
            # only one reference to a file
            inodes.add(inode) 
            unique_files.append(file)

    return unique_files


def traversed(path, skip_links = True):
    """Generator to recursively traverse a given directory structure and yields the 
    absolute path + file name of each file encountered. By default, sym links are 
    skipped over. 
    @param path <str>:
        Path to recusively list directory contents
    @param skip_links <bool>:
        Skips over sym-linked files when True 
    """
    # Normalize path, coverts to absolute path and 
    # dereferences path alias (like "~" -> "/home") 
    path = normalized(path)

    # Recursively descend the directory tree
    # and list information about its files
    for pdir, chdirs, files in os.walk(path):
        for f in files:
            # Get absolute referece to file  
            file = os.path.join(pdir, f)
            # Check whether to skip over symlinks
            if skip_links and os.path.islink(file):
                continue  # Skip over symlink

            yield file


def _ls(path):
    """Generator for spacesavers ls which recursively lists
    information about files and directories for a given path. 
    Any symbolic links or multiple references to the same inode, 
    i.e. hard links (only one inode reference is preserved), 
    are skipped over when listing files.
    @param path <str>:
        Path to recusively list directory contents
    @yields file_info <list>:
        0=inode, 1=permissions, 2=owner, 3=group, 4=bytes, 5=size, 
        6=mdate, 7=file, 8=nduplicates, 9=downers, 10=duplicates
    """
    # TODO: Refactor this later, rewrite as a class 
    # using the chain of responsibility design pattern

    # Keeps track of previously converte user/group
    # ids to avoid redundant lookups in the unix 
    # user/group database, size and 64 KiB hashes 
    # of encountered files to reduce search space
    # of required MD5 calculations.
    users = {}   # {uid: user_name, gid: group_name, ...}
    sizes  = {}  # {size_bytes: ['/path/f1.txt', '/path/f2.txt'], ...}
    mini_hashes = {}  # {(hash64KiB, size_bytes): ['/path/f1.txt', '/path/f2.txt'], ...}
    full_hashes = {}  # {(hashFile, size_bytes): ['/path/f1.txt', '/path/f2.txt'], ...}


    # Recursively descend the directory tree
    # and list information about its files,
    # symbolic links are skipped over here.
    for file in traversed(path):
        # Find files that have the same size.
        # Duplicate files will always have the 
        # same size and candidates more checks
        # like a partial mini-hash of the file 
        # (first 64KiB MD5) AND calculating an 
        # MD5 of the entire file.
        try:
            filesize = os.path.getsize(file)
            if filesize not in sizes: 
                sizes[filesize] = []
            sizes[filesize].append(file)
        except Exception as e:
            # Possible errors include permissions
            # issues or non-existent file
            err('WARNING: Failed to get info on "{}" due to "{}" error!'.format(file, e))
            continue   # goto next file

    # Calculate a mini hash for files with 
    # the same filesize. These are candidate
    # dups that can be further filtered. The mini 
    # hash is calcualted from the first 64 KiB
    # of the file.
    for size, files in sizes.items():
        # Filter files with multiple references 
        # to the same inode, i.e. multiple hardlinks.
        # Keeps only one reference to a set of hardlinks.
        files = dereferenced(files)
        if len(files) < 2:
            # Skip over mini hash calcualation 
            # the file size is unique, so it 
            # is NOT a candidate dup file.
            file = files[0]
            file_info = file_stats(file, users)
            if not file_info: continue   # cannot get info on file
            file_info.extend([file, '0', '', '']) # empty string for duplicates
            yield file_info
            continue                    # goto the next file

        for file in files:
            try:
                # Calculate a mini hash of the first
                # 64 KiB chunk/block of the file. Files
                # with the same mini hash will be candidates
                # for an MD5 checksum of the entire file.
                mini_hash = md5sum(file, first_block_only = True)
                if (mini_hash, size) not in mini_hashes:
                    mini_hashes[(mini_hash, size)] = []
                mini_hashes[(mini_hash, size)].append(file)
            except Exception as e:
                # Possible errors include permissions
                # issues or non-existent file
                err('WARNING: Failed to get info on "{}" due to "{}" error!'.format(file, e))
                continue   # goto next file
    
    # Calculate a full hash for files with 
    # the same mini hash. These are the final 
    # candidates for duplication.
    for hash_tuple, files in mini_hashes.items():
        if len(files) < 2:
            # Skip over full hash calcualation 
            # the mini hash is unique, so it 
            # is NOT a candidate dup file.
            file = files[0]
            file_info = file_stats(file, users)
            if not file_info: continue   # cannot get info on file
            file_info.extend([file, '0', '', '']) # empty string for duplicates
            yield file_info
            continue                    # goto the next file

        size = hash_tuple[1]
        for file in files:
            try:
                # Calculate a full hash for files with 
                # the same mini hash.             
                full_hash = md5sum(file)
                if (full_hash, size) not in full_hashes:
                    full_hashes[(full_hash, size)] = []
                full_hashes[(full_hash, size)].append(file)
            except Exception as e:
                # Possible errors include permissions
                # issues or non-existent file
                err('WARNING: Failed to get info on "{}" due to "{}" error!'.format(file, e))
                continue   # goto next file

    # Final link in chain of responsibilty.  
    # Display information for duplicate files.
    for hash_tuple, files in full_hashes.items():
        try:
            # Find the oldest file to represent the master copy
            # of all the duplicates, sort files from oldest to newest.
            files = sorted(files, key=lambda t: os.stat(t).st_mtime)
            # Get a list of the duplicate file owners
            owners = "|".join([name(os.stat(f).st_uid, 'user', users) for f in files[1:]])
        except Exception as e:
            # Possible errors include permissions
            # issues or non-existent file
            err('WARNING: Failed to get info on "{}" due to "{}" error!'.format(files, e))
            continue   # goto next file
        file = files[0]
        ndups = len(files[1:])
        duplicates = "|".join(files[1:])
        file_info = file_stats(file, users)
        if not file_info: continue   # cannot get info on file
        file_info.extend([file, str(ndups), owners, duplicates])
        yield file_info


def _df(handler, path, split=False):
    """Generator for spacesavers df which recursively lists
    information about files and directories for a given path. 
    Any symbolic links or multiple references to the same inode, 
    i.e. hard links (only one inode reference is preserved), 
    are skipped over when listing files.
    @param handler <iter>:
        A iterable object containing the out from the ls command,
        _ls returns a generator yielding lists of information; however,
        standard input is recieved as raw text, the split option should
        be set to True when using with standard input
    @param path <str>:
        Path to recusively list directory contents
    @param split <bool>:
        Split iterable contents into a list, set True with standard input
    @yields df_info <list>:
        0=mount, 1=duplicated, 2=available, 3=%duplicated, 4=score
    """
    duplicated = 0
    available = 0
    score = 0.0
    # Calculate an age weighted score duplication score
    # where scorePerFile = age * duplicatedBytes
    # and Score = sum(scoreDupsFiles) / sum(scoreAllFiles)  
    scoreDups, scoreAll = 0.0, 0.0
    for file_listing in handler:
        if split:
            # Needed when standard input provided
            file_listing = file_listing.strip().split('\t')
        mount = path
        # Caculate size of duplicated diskspace and total diskspace
        filesize = int(file_listing[4])  # size of file in bytes
        ncopies  = int(file_listing[8])  # number of redundant copies
        duplicated += filesize * ncopies
        available += filesize * (ncopies + 1)
        mtime = datetime.datetime.strptime(file_listing[6], '%Y-%m-%d-%H:%M')
        age = datetime.datetime.today() - mtime
        age = round(age.total_seconds() / 86400.0, 4) # convert seconds to days 
        scoreAll += available * age
        if ncopies >= 1:
            scoreDups += available * age
        
    percent_duplicates = "{}%".format(round((duplicated/ float(available)) * 100, 3))
    score = str(100 - int(scoreDups / scoreAll) * 100) 

    yield [mount, readable_size(duplicated), readable_size(available), percent_duplicates]


if __name__ == '__main__':
    # Add tests later
    pass