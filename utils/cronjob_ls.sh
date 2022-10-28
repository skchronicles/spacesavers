#!/bin/bash

set -exo pipefail
export PATH=$PATH:/usr/local/bin
export PATH=$PATH:/usr/local/slurm/bin
echo $PATH

dt=$(date "+%m%d%y")
dt=$(echo "${dt}_lsonly")
#dt="061322"
spacesaver_dir="/data/CCBR/dev/spacesavers"
spacesaver_exe="${spacesaver_dir}/spacesaver"
outdir="${spacesaver_dir}/log_${dt}"
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
do_report=0
do_cleanup=0

if [ "$do_ls" == "1" ];then
# do ls
for f in $(find /data/CCBR/projects -maxdepth 1 -type d);do 
	g=$(echo $f|awk -F"/" '{print $NF}');
	echo "${spacesaver_exe} ls $f 1>${outdir}/${g}_projects_ls.tsv 2>${outdir}/${g}_projects_ls.err";
done > do_ls_swarm
for f in $(find /data/CCBR/rawdata -maxdepth 1 -type d);do 
	g=$(echo $f|awk -F"/" '{print $NF}');
	echo "${spacesaver_exe} ls $f 1>${outdir}/${g}_rawdata_ls.tsv 2>${outdir}/${g}_rawdata_ls.err";
done >> do_ls_swarm
swarm -f do_ls_swarm -t 2 -g 200 --partition=ccr,norm --time=24:00:00 
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
fi

exit

if [ "$do_report" == "1" ];then
	cat > ${outdir}/render_report.R << EOF
rmarkdown::render("${spacesaver_dir}/utils/make_ccbr_duplicate_report.Rmd", 
output_file = "${outdir}/duplication_report.html",
encoding = "UTF-8",
params = list(directory = "${outdir}"))
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
rm -rf all_lss.tsv all_dfs.tsv
rm -rf swarm*
rm -f do_*
fi

