#!/bin/bash
# This cronjob script does the following steps:
# 1. spacesavers ls
# 	"spacesavers ls" is run in parallel using a swarm job for each folder under
#   a. /data/CCBR/rawdata and
#   b. /data/CCBR/projects
#   This is the most time consuming part of the entire exercise and need to spawn
#   biowulf jobs
# 2. spacesavers df
#   Utilizing the outputs from the previous step, "spacesavers df" command is used
#   on each of the "spacesavers ls" outputs and then those subsequent outputs are
#   concatenated. Earlier this job was also submitted to the sbatch queue but since
#   it running fairly quickly, it is now run directly (under the master job).
# 3. create report
#	R script is run to ingest the concatenated output from the previous steps to
#   generate a HTML report. The report is then placed at a location where it can be
#   picked up by the cronjob on helix.
# 4. cleanup
# 	Delete unnecessary/intermediate files and reduce the digital footprint on the
# 	/data/CCBR/dev/spacesavers/log_${dt} folders

set -exo pipefail
export PATH=$PATH:/usr/local/bin
export PATH=$PATH:/usr/local/slurm/bin
echo $PATH


# configure run
debug=0
# debug=0 ... actual run
# debug=1 ... debugging mode
if [ "$debug" == "0" ];then
    folders="/data/CCBR/projects /data/CCBR/rawdata"
else
    folders="/data/CCBR/dev/spacesavers"
fi

# set input/output and other locations
dt=$(date "+%m%d%y")
#dt="061322"
spacesaver_dir="/data/CCBR/dev/spacesavers"
spacesaver_exe="${spacesaver_dir}/spacesaver"
if [ "$debug" == "0" ];then
    outdir="${spacesaver_dir}/log_${dt}"
else
    outdir="${spacesaver_dir}/log_debug_${dt}"
fi
# copy report to $report
# $report will be attached to the email sent out by a cronjob on helix
# FYI, email cronjob only works out of helix (not biowulf)
report="${spacesaver_dir}/log/duplication_report.html"
if [ "$debug" == "0" ];then
    if [ -d $outdir ];then
        rm -rf $outdir
    fi
    mkdir -p $outdir 
fi
cd $outdir

# decide what to run
do_ls=1
do_df=1
do_report=1
do_cleanup=1


# actual runs
# generally you will not be needed to edit below this line
if [ "$do_ls" == "1" ]; then
# do ls
    # create a swarm job and submit it to sbatch... wait till it ends
    for folder in $folders;do
        for f in $(find $folder -maxdepth 1 -mindepth 1 -type d);do 
            g=$(echo $f|tr '/' '_')
            echo "${spacesaver_exe} ls $f 1>${outdir}/${g}_ls.tsv 2>${outdir}/${g}_ls.err"
        done
    done > do_ls_swarm
    njobs=$(wc -l do_ls_swarm|awk '{print $1}')
    echo $njobs
    if [ "$njobs" != "0" ];then
        echo "RUNNING: swarm -f do_ls_swarm -t 2 -g 200 --partition=ccr,norm --time=48:00:00 --sbatch \"--wait\""
        swarm -f do_ls_swarm -t 2 -g 200 --partition=ccr,norm --time=48:00:00 --sbatch "--wait"

# # after swarm job has ended ... concatenate the "ls.tsv" files into a single file named "all_lss.tsv"

cat <<EOF > ${outdir}/do_ls_concat
#!/bin/bash
#SBATCH --job-name="spacesavers ls_concat"
#SBATCH --mem=200g
#SBATCH --partition="ccr,norm"
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=2

n=1
for f in \$(find $outdir -maxdepth 1 -name "*_ls.tsv")
do
if [[ "\$n" == "1" ]]
then
head -n1 \$f
fi
n=\$((n+1))
tail -n +2 \$f
done | awk -F"\t" '{if (NF==14) {print}}' > ${outdir}/all_lss.tsv
EOF
        echo "RUNNING: sbatch --wait ${outdir}/do_ls_concat"
        sbatch --wait ${outdir}/do_ls_concat

# # after all_lss.tsv has been created ... get per user stats

cat <<EOF > ${outdir}/do_get_stats_per_user
#!/bin/bash
#SBATCH --job-name="spacesavers get_stats"
#SBATCH --mem=200g
#SBATCH --partition="ccr,norm"
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=2
${spacesaver_dir}/utils/get_stats_per_user.py \\
 --ls ${outdir}/all_lss.tsv \\
 --peruserbytes ${outdir}/bytes_per_user.tsv \\
 --largedups ${outdir}/large_duplicates.tsv \\
 --dist ${outdir}/age_distribution_per_user.tsv
EOF

        echo "RUNNING: sbatch --wait ${outdir}/do_get_stats_per_user"
        sbatch --wait ${outdir}/do_get_stats_per_user
    fi
fi

if [ "$do_df" == "1" ]
then
# do df
# eg.
# ./cat ccbr123_ls.tsv | spacesaver df /data/CCBR/rawdata/ccbr123/
    for folder in $folders;do
        for f in $(find $folder -maxdepth 1 -type d);do
            g=$(echo $f|tr '/' '_')
            if [ -f "${outdir}/${g}_ls.tsv" ];then
                echo "cat ${outdir}/${g}_ls.tsv | ${spacesaver_exe} df $f 1> ${outdir}/${g}_df.tsv 2> ${outdir}/${g}_df.err"
            fi
        done
    done > do_df_swarm
    njobs=$(wc -l do_df_swarm|awk '{print $1}')
    if [ "$njobs" != "0" ];then
        # these are fast .. no need to swarm
        bash do_df_swarm
        # now concatenate
        n=1
        for f in $(find $outdir -maxdepth 1 -name "*_df.tsv")
        do
        if [[ "$n" == "1" ]]
        then
        head -n1 $f
        fi
        n=$((n+1))
        tail -n +2 $f
        done | awk -F"\t" '{if (NF==12) {print}}' > ${outdir}/all_dfs.tsv
    fi
fi

# ls and df are done ... now create report

if [ "$do_report" == "1" ];then
# create the R script
cat <<EOF > ${outdir}/render_report.R
rmarkdown::render("${spacesaver_dir}/utils/make_report.Rmd", 
output_file = "${outdir}/duplication_report.html",
encoding = "UTF-8",
params = list(bytes_per_user = "${outdir}/bytes_per_user.tsv", 
        alllsstsv = "${outdir}/all_lss.tsv",
        dupfile = "${outdir}/large_duplicates.tsv",
        alldfstsv = "${outdir}/all_dfs.tsv"))
EOF

# submit the R script to sbatch
cat << EOF > ${outdir}/do_report
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
    chmod -R a+rX $report
fi
EOF
    echo "RUNNING: sbatch --wait ${outdir}/do_report"
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
    # rm -rf swarm*
    # rm -f do_*
fi

