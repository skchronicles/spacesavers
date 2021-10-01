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
from benchmark import timer


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


def scored(age):
    """Score a file based on its size and scaled age where 
    AgeScore = nBytesFile * ageScoreFile
    @param age <float>:
        Age of file in days
    @ return score <float>:
        Age-scaled score of a file
    """
    # Default score for files older than 1000 days
    score = 1.0 # or ~2.7 years
    s1 = 0.1    # scaling factor 1
    s2 = 0.8    # scaling factor 2 
    if age <= float(30*6): 
        # Score for files less than 6 months old
        score = age / (30*6) * s1
    elif age <= float(30*24):
        # Score for files between 6 and 24 months old 
        age = age - (30*6)
        score = s1 + age / (30*(24-6)) * s2
    elif age <= 1000:
        # Score for files between 24 and 33 months old
        age = age - (30*24)
        score = s1 + s2 + age/ (1000-(30*24)) * (1-(s1 + s2)) 
    
    return score


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
        6=mdate, 7=file, 8=nduplicates, 9=bduplicates, 10=sduplicates, 
        11=downers, 12=duplicates
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
            file_info.extend([file, '0', '0', '0 B', '', '']) # empty string for duplicates
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
            file_info.extend([file, '0', '0', '0 B', '', '']) # empty string for duplicates
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
        duplicated = ndups * int(file_info[4])
        file_info.extend([file, str(ndups), str(duplicated), str(readable_size(duplicated)),  owners, duplicates])
        yield file_info


def _df(handler, path, split=False, quota=200):
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
    @param quota <int:
        Diskspace quota of a given area 
    @yields df_info <list>:
        0=mount, 1=duplicated, 2=available, 3=%duplicated, 4=score
    """
    # Calculate a path's age-weighted score.
    # PathScore is the weighted sum of three
    # scores pertaining to the average file's 
    # age and size, the duplication rate of a 
    # given path, and overall occupancy/footprint
    # of a path against a defined quota threshold
    # where PathScore = 100 - (100 * (wAge*AgeScore + wDup*DupScore + wOcc*OccScore))
    duplicated = 0
    available = 0
    score = 0.0
    # Weights for AgeScore, DupScore, and OccScore
    # where wAge + wDup + wOcc = 1 
    wAge = 0.25
    wDup = 0.45
    wOcc = 0.35
    # List to aggregate per file age scores
    # AgeScore is the average per file age_score
    age_scores = []
    age_bytes = []

    for file_listing in handler:
        # Contents of file listing
        # 0=inode, 1=permissions, 2=owner,
        # 3=group, 4=bytes, 5=size, 6=mdate, 
        # 7=file, 8=nduplicates, 9=bduplicates,
        # 10=sduplicates, 11=downers, 12=duplicates
        if split:
            # Needed when standard input is provided
            # to parse _ls() input
            file_listing = file_listing.strip().split('\t')

        # Caculate size of duplicated diskspace and total diskspace
        filesize = int(file_listing[4])         # size of file in bytes
        ncopies  = int(file_listing[8])         # number of redundant copies
        duplicated += filesize * ncopies        # duplication size of files
        available += filesize * (ncopies + 1)   # total size of files

        mtime = datetime.datetime.strptime(file_listing[6], '%Y-%m-%d-%H:%M')
        age = datetime.datetime.today() - mtime
        age = round(age.total_seconds() / 86400.0, 4) # convert seconds to days
        try:
            age_scores.append((filesize * scored(age)) / (filesize))
        except ZeroDivisionError:
            # File size is 0 bytes, add contribution of scaled age
            age_scores.append(scored(age) / age)

    # Age Score is the average age score of all files,
    # where age is scaled via the scored() function.
    # AgeScore = sum(bytesPerFiles * scored(ageScorePerFile)) / len(Nfiles)
    AgeScore = sum(age_scores) / len(age_scores) 
    
    # DupScore = DuplicatedBytes / TotalBytes
    DupScore = duplicated / float(available)   # 0 indicates no duplicated files 
    percent_duplicates = "{}%".format(round(DupScore * 100, 3))
    
    # OccScore = totalBytes / (0.05 * quota) if totalBytes is less than 5% of 
    # quota. If a directory is greater than 5% of the quota, DupScore gets the
    # worst possible score.
    OccScore = 1.0
    quota_bytes = quota * (2**40) # convert TiB to bytes
    if float(available) <= (0.05*float(quota_bytes)):
        OccScore = float(available) / (0.05 * quota_bytes)
    
    # Calculate the final weighted score of a path
    Score = str(round(100 - (100 * ((wAge*AgeScore) + (wDup*DupScore) + (wOcc*OccScore))), 1))
    # Calculate the individual weighted components
    AgeC = str(round(100 * (wAge*AgeScore), 1))
    DupC = str(round(100 * (wDup*DupScore), 1))
    OccC = str(round(100 * (wOcc*OccScore), 1))

    yield [path, readable_size(duplicated), readable_size(available), percent_duplicates, AgeC, DupC, OccC, Score]


def _ln(path):
    """Generator for spacesavers ln which recursively replaces
    duplicated files with hardlink in a given path.
    Any symbolic links or multiple references to the same inode, 
    i.e. hard links (only one inode reference is preserved), 
    are skipped over when finding duplicate files.
    @param path <str>:
        Path to recusively list directory contents
    @yields ln_info <list>:
        0=target, 1=newlink
    """
    # Finds duplicated files and a create a hard link 
    # if the user running the script has at least two 
    # duplicated files. If a duplicated file is shared
    # across users and each user owns only one copy of 
    # a file, then a hard link is NOT created. Hard links 
    # will only be created from duplicated files the user
    # owns! This reduces the chance of introducing any
    # undesired results.
    for file_listing in _ls(path):
        # Contents of file listing
        # 0=inode, 1=permissions, 2=owner,
        # 3=group, 4=bytes, 5=size, 6=mdate, 
        # 7=file, 8=nduplicates, 9=bduplicates,
        # 10=sduplicates, 11=downers, 12=duplicates
        
        # Check for duplicated files
        nduplicates = int(file_listing[8])
        if nduplicates == 0:
            # File is unique
            # goto next file listing
            continue

        # Get username of user running the script
        # to compare against the owner of the old 
        # copy of the file (master copy)
        user = str(_name(os.getuid(), 'user'))
        owner = str(file_listing[2])
        dup_owners = str(file_listing[11]).split('|')
        dup_files = str(file_listing[12]).split('|')

        # Safety measure: skip over processes run
        # as root or duplicate files owned by root
        if user == 'root' or owner == 'root':
            continue

        # Saftey measure: remove any duplicate
        # files owned by root to help sanitize
        # any erroneous user input. This will
        # also filter any files from the dup
        # list that we do not own! Remember 
        # we only want to create hard links
        # from files we actually own.
        for i in range(len(dup_owners)):
            if str(dup_owners[i]) != user:
                rm = dup_owners[i].pop(i)
                rm = dup_files[i].pop(i)
        
        # Oldest duplicate file from which
        # the other hard links will be
        # created from.
        mastercopy = str(file_listing[7])
        # Index of where to start finding
        # duplicate files. The index is set
        # to 1 when the user running the script
        # does not own the master copy AND when
        # the user owns at least two of the
        # duplicates. 
        dindex = 0
        if user != owner:
            if len(dup_files) < 2:
                # User only own one of the
                # duplicated files, a user
                # must own at least two
                # duplicated files to 
                # create a hardlink
                continue

            # Master copy is now the next 
            # oldest file that is owned 
            # by the user.
            mastercopy = str(dup_files[0])
            dindex = 1   # reset duplicate index
        
        for dup in dup_files[dindex:]:
            yield [mastercopy, dup]


if __name__ == '__main__':
    # Test age-scaling function
    import matplotlib.pyplot as plt
    file_scores = []
    x = []
    for i in range(0,2000):
        x.append(i)
        file_scores.append(scored(i))

    # Plot values to viz results
    fig, ax = plt.subplots()
    ax.plot(x, file_scores)
    ax.set(xlabel='Age (Days)', ylabel='Score', title='')
    ax.grid()
    fig.savefig("scores.png")