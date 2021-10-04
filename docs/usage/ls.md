# <code>./spacesaver <b>ls</b></code>

## About 
The `./spacesaver` executable is composed of several inter-related sub commands. Please see `./spacesaver -h` for all available options. This part of the documentation describes options, concepts, and output for <code>./spacesaver <b>ls</b></code> sub command in more detail. 

<code>./spacesaver <b>ls</b></code> can be used to identify duplicate files. The output of this command is similar to the unix `ls -Rilath` command; however, entries corresponding to duplicated files are collapsed into one line. 


To reduce overall strain on the file system and run time, a set of heuristics are used to filter a list of candidate duplicates prior to running computionally intensive steps. And as so, before calculating an MD5
checksum of the entire file, potential duplicates are identifed by matching their file sizes and the checksum of the file's first 64 KiB chunk. This significantly reduces the search search of the ls sub command prior to calculating an MD5 checksum of the entire file.

<code>./spacesaver <b>ls</b></code> only has *one required input*, a path or set of paths.

## Synopsis
```text
$ spacesaver ls [-h] DIRECTORY [DIRECTORY ...]
```

The synopsis for each command shows its parameters and their usage. Optional parameters are shown in square brackets.

The ls sub command takes one or more directories as input. Within a given directory, each file will be recursively listed with its duplicates. Please note that symlinks or multiple occurences of hard links will be skipped over as these files do not take up any appreciable disk space. Only one instance of a set of hard links pointing to the same inode will be reported.

Use you can always use the `-h` option for information on a specific command. 

### Required Arguments

Each of the following arguments are required. Failure to provide a required argument will result in a non-zero exit-code.

  `DIRECTORY [DIRECTORY ...]`  
> **Input directories to find duplicates.**  
> *type: path*  
> 
> One or more directories can be provided as positional arguments. From the command-line, each directory should seperated by a space. Globbing is supported! This makes selecting paths easier. Please note that duplicates are reported relative to other files within a directory.
> 
> ***Example:*** `/data/CCBR/rawdata/ccbr123/`

### Optional Arguments

Each of the following arguments are optional and do not need to be provided. 

  `-h, --help`            
> **Display Help.**  
> *type: boolean*
> 
> Shows command's synopsis, help message, and an example command
> 
> ***Example:*** `--help`

## Output 

The output of the ls sub command is similar to the unix long listing of a file with more information. It is displayed to standard ouput.

Here is a description of each column's output:

|          | Column Name      | Example Value                         |
|----------|------------------|---------------------------------------|
| *1*      | Inode            | 1055643                               |
| *2*      | Permissions      | -rw-rw----                            |
| *3*      | Owner            | kuhnsa                                |
| *4*      | Group            | CCBR                                  |
| *5*      | Bytes            | 588895                                |
| *6*      | Size             | 575.093 KiB                           |
| *7*      | MDate            | 2021-09-20-17:20                      |
| ***8***  | ***File***       | /path/to/oldest_duplicate.txt         |
| *9*      | NDuplicates      | 2                                     |
| *10*     | BDuplicates      | 1177790                               |
| *11*     | SDuplicates      | 1.123 MiB                             |
| *12*     | DOwners          | kuhnsa\|kopardevn                     |
| ***13*** | ***Duplicates*** | /path/to/dup1.txt\|/path/to/dup2.txt  |

***Please note:*** The output is seperated or delimited by tabs: `\t`, and columns containing multiple values for a list of files are seperated by a pipe: `|`. When reporting duplicates, one file is selected as the master copy. This is the oldest file from a set of duplicated files. The master copy is listed in Column 8, *File*. Any encountered duplicates will be reported in the last column, *Duplicates*.


## Example

Please note this sub command may take a while to process depending on the shear number or the size of files existing in a given sub tree. As so, this command should not be run on the head node! Please allocate an interactive node prior to running this command or submit this command as a job via sbatch.

```bash 
# Step 0.) Grab an interactive node
# Do not run this on the head node!
srun -N 1 -n 1 --time=12:00:00 -p interactive --mem=16gb  --cpus-per-task=4 --pty bash
module purge

# Step 1.) Find duplicate files
./spacesaver ls /data/CCBR/rawdata/ccbr123/ > ccbr123_ls.tsv
```