#!/usr/bin/env python3
import pandas as pd
import collections
import sys
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description='Get per user statistics')
parser.add_argument('-i','--ln', help='input file: output file from "spacesaver ln" command', required=True)
parser.add_argument('-p','--peruserbytes', help='output file: name of per user bytes output file', required=True)
parser.add_argument('-l','--largedups', help='output file: list of large duplicates per user', required=True)
parser.add_argument('-d','--dist', help='output file: age distribution of files owned by each user', required=True)
args = vars(parser.parse_args())

pd.set_option('display.max_columns', None)  # or 1000
pd.set_option('display.max_rows', None)  # or 1000
pd.set_option('display.max_colwidth', None)  # or 199

#infile=sys.argv[1]
#infile="/data/CCBR/dev/spacesavers/logs/all_lss.tsv"
#outfile="bytes_per_user.v2.tsv"
infile=args['ln']
outfile=args['peruserbytes']
large_dup_path=args['largedups']
outfile2=args['dist']

# read the file
# file columns
# 0=inode, 1=permissions, 2=owner,
# 3=group, 4=bytes, 5=size, 6=mdate, 7=age,
# 8=file, 9=nduplicates, 10=bduplicates,
# 11=sduplicates, 12=downers, 13=duplicates
x=pd.read_csv(infile,header=0,delimiter="\t",low_memory=False)
x=x.fillna(0)
x=x[x['Bytes']>0]
x=x.reset_index()

large_dup_cutoff=100*1024*1024
# print(x['BDuplicates'])
large_dup=x[x['BDuplicates']>large_dup_cutoff]
filepath = Path(large_dup_path)
filepath.parent.mkdir(parents=True, exist_ok=True)
large_dup.to_csv(filepath,sep="\t",header=True,index=False)

tbites=dict()
dbites=dict()
age_distribution_count=dict()
age_distribution_bites=dict()

users=x.Owner.unique()

for u in users:
    tbites[u]=0
    dbites[u]=0
    age_distribution_count[u]=dict()
    age_distribution_bites[u]=dict()

for i,row in x.iterrows():
    bites=int(row['Bytes'])
    dupbites=int(row['BDuplicates'])
    age=str(row['Age'])
    user=row['Owner']
    # print(row['DOwners'])
    if dupbites!=0:
        downers=collections.Counter(row['DOwners'].split("|"))
        allusers = set(users) | set(downers.keys())
        newusers = allusers - set(users)
        for u in newusers:
            tbites[u]=0
            dbites[u]=0
            age_distribution_count[u]=dict()
            age_distribution_bites[u]=dict()
        users = list(allusers)        
    # if not user in age_distribution_count:
    #     continue
    try:
        age_distribution_count[user][age]+=1
        age_distribution_bites[user][age]+=bites
    except KeyError:	
        age_distribution_count[user][age]=1
        age_distribution_bites[user][age]=bites
	
    # try:
    #     tbites[user] += bites
    # except KeyError:
    #     continue
    tbites[user] += bites
    if dupbites==0:
        continue

    for k,v in downers.items():
        dupbites_per_user = bites * v
        dbites[k] += dupbites_per_user
        tbites[k] += dupbites_per_user
        try:
            age_distribution_count[k][age] += v
            age_distribution_bites[k][age] += dupbites_per_user
        except KeyError:
            age_distribution_count[k][age] = v
            age_distribution_bites[k][age] = dupbites_per_user

        # try:
        #     dbites[k] += bites * v
        #     age_distribution_count[k] += v
        # except KeyError:
        #     continue
        # try:
        #     tbites[k] += bites * v
        # except KeyError:
        #     continue

o2=open(outfile2,'w')
o2.write("%s\t%s\t%s\t%s\n"%("Username","Age","Count","Bytes"))

for u in age_distribution_count.keys():
    ages = age_distribution_count[u]
    ages_list = [int(a) for a in ages.keys()]
    # print(u,ages_list)
    maxage = max(ages_list)+1
    for a in range(0,maxage):
        stra = str(a)
        if stra in ages:
            o2.write("%s\t%s\t%s\t%s\n"%(u,stra,age_distribution_count[u][stra],age_distribution_bites[u][stra]))
        else:
            o2.write("%s\t%s\t0\t0\n"%(u,stra))
o2.close()



o=open(outfile,'w')
o.write("%s\t%s\t%s\n"%("User","Total_Bytes","Duplicate_Bytes"))
tbites = collections.OrderedDict(sorted(tbites.items(),key=lambda item:item[1]))
for u,b in tbites.items():
    tb=b
    db=dbites[u]
    o.write("%s\t%d\t%d\n"%(u,tb,db))
o.close()
