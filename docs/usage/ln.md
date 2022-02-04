# <code>./spacesaver <b>ln</b></code>

## About 

!!! warning

    This sub command **should only be run** by advanced users. 

The `./spacesaver` executable is composed of several inter-related sub commands. Please see `./spacesaver -h` for all available options. This part of the documentation describes options, concepts, and output for <code>./spacesaver <b>ln</b></code> sub command in more detail. 

<code>./spacesaver <b>ln</b></code> can be used to remove duplicate files. To save diskspace, hardlinks will be created between any encountered duplicate files. The oldest occurence from the set of duplicated files will be used as a template. From this file, new hardlinks will be created. Hard links point to the same node on a device or file system, and do not take up any appreciable disk space. A significant amount of disk space can be recovered or saved by replacing duplicated files with hard links.

Hard links come with a few caveats! 

Please read through the section below to understand any issues that can a rise when creating multiple hard links:

  - Hard links cannot be created across different devices, volumes, or file systems.  
  - Some file systems do not support multiple hard links, such as FAT; however, most modern POSIX complaint operating systems such as linux or macOS support this feature.  
  - Creating multiple hard links has the effect of giving one file multiple names. From the file system's perspective, they are all the same. Each hard link will independently point to the same data on disk.   
  - If you update one hard link, the changes will propagate to all the other hard links. This causes an alias effect which can lead to desired or even catastrophic results.

!!! danger "Disclaimer"

    Use a healthy amount of caution and common sense when running this command. Seriously, with great power comes great responsibility! 
    
    Treat it with the same respect as an `rm` command. **If you do not fully understand the conditions described above, you should not run `spacesaver ln`**. The `-m` option can be used to set a minimum file size in bytes. If a file does not exceed this minimum file size, then a hard link will not be created!

## Synopsis
```text
$ spacesaver ln [-h] [-m MINSIZE] DIRECTORY [DIRECTORY ...]
```

The synopsis for each command shows its parameters and their usage. Optional parameters are shown in square brackets.

The ln sub command takes one or more directories as input. Within a given directory, duplicated files will be replaced with hardlinks. It is advised to always run the `spacesaver ls` prior to running this command. Please note that symlinks or multiple occurences of hard links will be skipped over as these files do not take up any appreciable disk space. Only one instance of a set of hard links pointing to the same inode will be evaluated.

Use you can always use the `-h` option for information on a specific command. 

### Required Arguments

Each of the following arguments are required. Failure to provide a required argument will result in a non-zero exit-code.

  `DIRECTORY [DIRECTORY ...]`  
> **Input directories to find duplicates.**  
> *type: path*  
> 
> One or more directories can be provided as positional arguments. From the command-line, each directory should seperated by a space. Globbing is supported! This makes selecting paths easier. Please note that duplicates are reported and replaced relative to other files within a provided directory.
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

  `-m`            
> **Minimum size of a file in bytes.**  
> *type: int*  
> *default: 10485760*
> 
> To create a hard link, the size of a given duplicated file must exceed this value. The default file size is 10 MiB. A file smaller than this default will not get replaced with a hardlink.
>
> ***Example:*** `-m 1073741824`

## Example

Please note that this sub command may take a while to process depending on the shear number or the size of files existing in a given subtree. As so, this command should not be run on the head node! Please allocate an interactive node prior to running this command or submit this command as a job via sbatch. 

To assess the number or size of files that exist in a provided directory, please run the `spacesaver ls` prior to running `spacesaver ln`.

```bash 
# Step 0.) Grab an interactive node
# Do not run this on the head node!
srun -N 1 -n 1 --time=12:00:00 -p interactive --mem=16gb  --cpus-per-task=4 --pty bash
module purge

# Step 1.) Find duplicate files
./spacesaver ls /data/CCBR/rawdata/ccbr123/ > ccbr123_ls.tsv

# Step 1A.) Option: Take a peek 
# at any identified duplicates
more ccbr123_ls.tsv

# Step 2.) Replace duplicate files
# that are greater than 1 GiB in
# size with hard links
./spacesaver ln -m 1073741824 /data/CCBR/ccbr123/rawdata/
```