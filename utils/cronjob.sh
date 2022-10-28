#!/bin/bash

set -exo pipefail
export PATH=$PATH:/usr/local/bin
export PATH=$PATH:/usr/local/slurm/bin
echo $PATH

dt=$(date "+%m%d%y")
#dt="061322"
spacesaver_dir="/data/CCBR/dev/spacesavers"
spacesaver_exe="${spacesaver_dir}/spacesaver"
outdir="${spacesaver_dir}/log_${dt}"
#outdir="/data/CCBR/dev/spacesavers/log_081622_lsonly"
# copy report to $report
# $report will be attached to the email sent out by a cronjob on helix
# FYI, email cronjob only works out of helix (not biowulf)
report="${spacesaver_dir}/log/duplication_report.html"
if [ -d $outdir ];then
	rm -rf $outdir
fi
mkdir -p $outdir 
cd $outdir

do_ls=1
do_df=1
do_report=1
do_cleanup=1

if [ "$do_ls" == "1" ];then
# do ls
for f in $(find /data/CCBR/projects -maxdepth 1 -mindepth 1 -type d);do 
	g=$(echo $f|awk -F"/" '{print $NF}');
	echo "${spacesaver_exe} ls $f 1>${outdir}/${g}_projects_ls.tsv 2>${outdir}/${g}_projects_ls.err";
done > do_ls_swarm
for f in $(find /data/CCBR/rawdata -maxdepth 1 -mindepth 1 -type d);do 
	g=$(echo $f|awk -F"/" '{print $NF}');
	echo "${spacesaver_exe} ls $f 1>${outdir}/${g}_rawdata_ls.tsv 2>${outdir}/${g}_rawdata_ls.err";
done >> do_ls_swarm
swarm -f do_ls_swarm -t 2 -g 200 --partition=ccr,norm --time=24:00:00 --sbatch "--wait"

n=1
for f in `ls ${outdir}/*_ls.tsv`
do
if [[ "$n" == "1" ]]
then
head -n1 $f
fi
n=$((n+1))
tail -n +2 $f
done | awk -F"\t" '{if (NF==13) {print}}' > ${outdir}/all_lss.tsv
cat > ${outdir}/do_get_bytes_per_user << EOF
#!/bin/bash
#SBATCH --job-name="spacesavers get_bytes"
#SBATCH --mem=200g
#SBATCH --partition="ccr,norm"
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=2
${spacesaver_dir}/utils/get_bytes_per_user.py ${outdir}/all_lss.tsv ${outdir}/bytes_per_user.tsv ${outdir}/large_duplicates.tsv 
EOF 
sbatch --wait ${outdir}/do_get_bytes_per_user
fi


if [ "$do_df" == "1" ];then
# do df
# eg.
# ./cat ccbr123_ls.tsv | spacesaver df /data/CCBR/rawdata/ccbr123/
for f in $(find /data/CCBR/rawdata -maxdepth 1 -type d);do
	g=$(echo $f|awk -F"/" '{print $NF}')
	if [ "$g" != "rawdata" ];then
		echo "cat ${outdir}/${g}_rawdata_ls.tsv | ${spacesaver_exe} df $f 1> ${outdir}/${g}_rawdata_df.tsv 2> ${outdir}/${g}_rawdata_df.err"
	fi
done > do_df_swarm
for f in $(find /data/CCBR/projects -maxdepth 1 -type d);do
	g=$(echo $f|awk -F"/" '{print $NF}')
	if [ "$g" != "projects" ];then
		echo "cat ${outdir}/${g}_projects_ls.tsv | ${spacesaver_exe} df $f 1> ${outdir}/${g}_projects_df.tsv 2> ${outdir}/${g}_projects_df.err"
	fi
done >> do_df_swarm
# these are fast .. no need to swarm
bash do_df_swarm
n=1
for f in `ls ${outdir}/*_df.tsv`
do
if [[ "$n" == "1" ]]
then
head -n1 $f
fi
n=$((n+1))
tail -n +2 $f
done | awk -F"\t" '{if (NF==11) {print}}' > ${outdir}/all_dfs.tsv
fi

if [ "$do_report" == "1" ];then
	cat > ${outdir}/render_report.R << EOF
rmarkdown::render("${spacesaver_dir}/utils/make_ccbr_duplicate_report.Rmd", 
output_file = "${outdir}/duplication_report.html",
encoding = "UTF-8",
params = list(bytes_per_user = "${outdir}/bytes_per_user.tsv", 
		alllsstsv = "${outdir}/all_lss.tsv",
		dupfile = "${outdir}/large_duplicates.tsv",
		alldfstsv = "${outdir}/all_dfs.tsv"))
EOF
	cat > ${outdir}/do_report << EOF
#!/bin/bash
#SBATCH --job-name="spacesavers report"
#SBATCH --mem=40g
#SBATCH --partition="ccr,norm"
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=2
module load R
Rscript ${outdir}/render_report.R
if [ -f "${outdir}/duplication_report.html" ];then
cp ${outdir}/duplication_report.html $report
fi
chmod -R a+rX $report
EOF
sbatch --wait ${outdir}/do_report
fi

if [ "$do_cleanup" == "1" ];then
cd $outdir
rm -rf *_ls.tsv
rm -rf *_ls.err
rm -rf *_df.tsv
rm -rf *_df.err
gzip -n all_lss.tsv
gzip -n all_dfs.tsv
rm -rf swarm*
rm -f do_*
fi

