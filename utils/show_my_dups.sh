#!/bin/bash

me=$(readlink -f $0)

if [[ "$#" != "1" ]];then
	cat << EOF
	Usage:
	This script outputs your duplicate files found using spacesavers
	sorted by descending size.
	eg.
	%> bash $me <aggregated df file>
EOF
exit
fi

large_dups_file=$1

head -n1 $large_dups_file

awk -F"\t" -v u=$USER -v OFS="\t" '{if ($3==u) {print}}' $large_dups_file | sort -k10,10nr
