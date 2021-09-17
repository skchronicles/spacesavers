#!/bin/bash
# Usage:
# bash /path/to/fastq_get_serialnumber_flowcellid.sh <FASTQ or FASTQ.gz>
# output:
# 1. absolute path to fastq/fastq.gz file
# 2. serial number of sequencer
# 3. flowcellid
# 4. sequenced at SF? Y or N
# Example:
# bash /data/kopardevn/GitRepos/spacesavers/scripts/fastq_get_serialnumber_flowcellid.sh /gpfs/gsfs4/users/CCBR/projects/ccbr709/kopardevn_analysis/ccbr709/dummy_chipseq_180731/trim/CB45_KO_0.R2.trim.fastq.gz
# gives:
# /gpfs/gsfs4/users/CCBR/projects/ccbr709/kopardevn_analysis/ccbr709/dummy_chipseq_180731/trim/CB45_KO_0.R2.trim.fastq.gz	D00761	C8H23ANXX	Y



function usage {
  echo "Usage:"
  echo "bash $0 </path/to/fastq>"
  echo "One argument required!"
}

function get_sn_fid_sf {
firstline=$1
firstlinefirstword=$(echo $firstline|awk '{print $1}')
n=$(echo "$firstlinefirstword"|awk -F":" '{print NF}')
sn="."
fid="."
sf="."
if [ "$n" != "7" ];then
  if [ "$n" == "5" ];then
    sn=$(echo "$firstlinefirstword"|awk -F":" -v OFS="\t" '{print substr($1,2)}')
  else
    firstfourchar=$(echo "$firstlinefirstword"|awk '{print substr($1,1,4)}')
    if [ "$firstfourchar" == "@SRR" ];then
      srr=$(echo "$firstlinefirstword"|awk '{print substr($1,2)}'|awk -F"." '{print $1}')
      sn="SRA_FASTQ_FILE_$srr"
      sf="N"
    else
      sn="NON-STANDARD_FASTQ_FILE_$n"
      sf="UNKNOWN"
    fi  
  fi
  fid="UNKNOWN"
else
  sn=$(echo "$firstlinefirstword"|awk -F":" -v OFS="\t" '{print substr($1,2)}')
  fid=$(echo "$firstlinefirstword"|awk -F":" -v OFS="\t" '{print $3}')
  sf="N"
  for sfsn in "A00430" "A00946" "D00545" "D00553" "D00761" "J00170" "M01595" "M02560" "M06438" "NB501156" "NB501223" "NCI-GA1" "NCI-GA2" "NCI-GA3" "NCI-GA4" "NS500326" "NS500328" "NS500417" "SN1108" "SN165" "SN7001190R" "SN7001343"
  do
    if [ "$sfsn" == "$sn" ];then 
      sf="Y"
    fi
  done
fi
echo "$sn\t$fid\t$sf"
}

if [ "$#" != "1" ];then
  usage 
  exit 1
fi

filepath=$1
sn_fid_sf=".\t.\t.\t"
filename=$(basename -- "$filepath")
abspath=$(readlink -f "$filepath")
extension="${filename##*.}"
filename="${filename%.*}"
if [ -f "$abspath" ];then
  if [ -r "$abspath" ];then
    if [ "$extension" == "gz" ];then
      firstline=$(zcat $abspath | head -n1)
    else
      firstline=$(head -n1 $abspath)
    fi
    checkzero=$(echo $firstline|wc -c)
    if [ "$checkzero" -le "1" ]; then
        sn_fid_sf="EMPTY_FILE\tEMPTY_FILE\tEMPTY_FILE"
    else
        sn_fid_sf=$(get_sn_fid_sf $firstline)
    fi
  else
    sn_fid_sf="NO_READ_PERMISSION\tNO_READ_PERMISSION\tNO_READ_PERMISSION"
  fi
fi
echo -ne "$filepath\t$sn_fid_sf\n"
