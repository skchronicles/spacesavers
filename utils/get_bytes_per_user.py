#!/usr/bin/env python3
import pandas as pd
import collections
import sys
from pathlib import Path
import math

pd.set_option('display.max_columns', None)  # or 1000
pd.set_option('display.max_rows', None)  # or 1000
pd.set_option('display.max_colwidth', None)  # or 199

#infile=sys.argv[1]
#infile="/data/CCBR/dev/spacesavers/logs/all_lss.tsv"
#outfile="bytes_per_user.v2.tsv"
infile=sys.argv[1]
outfile=sys.argv[2]
large_dup_path=sys.argv[3]

# read the file
x=pd.read_csv(infile,header=0,delimiter="\t",low_memory=False)
x=x.fillna(0)
x=x[x['Bytes']>0]
x=x.reset_index()

large_dup_cutoff=100*1024*1024
large_dup=x[x['BDuplicates']>large_dup_cutoff]
filepath = Path(large_dup_path)
filepath.parent.mkdir(parents=True, exist_ok=True)
large_dup.to_csv(filepath,sep="\t",header=True,index=False)

tbites=dict()
dbites=dict()

users=x.Owner.unique()

for u in users:
	tbites[u]=0
	dbites[u]=0

for i,row in x.iterrows():
	bites=int(row['Bytes'])
	dupbites=int(row['BDuplicates'])
	try:
		tbites[row['Owner']] += int(row['Bytes'])
	except KeyError:
		continue
	if dupbites==0:
		continue
	downers=collections.Counter(row['DOwners'].split("|"))
	for k,v in downers.items():
		try:
			dbites[k] += bites * v
		except KeyError:
			continue
		try:
			tbites[k] += bites * v
		except KeyError:
			continue

o=open(outfile,'w')
o.write("%s\t%s\t%s\n"%("User","Total_Bytes","Duplicate_Bytes"))
tbites = collections.OrderedDict(sorted(tbites.items(),key=lambda item:item[1]))
for u,b in tbites.items():
	tb=b
	db=dbites[u]
	o.write("%s\t%d\t%d\n"%(u,tb,db))
o.close()
