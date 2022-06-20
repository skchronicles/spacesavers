#!/usr/bin/env bash
# this script should be called from crontab to submit the cronjob.sh
# script to the slurm queue
source $HOME/.bashrc
sbatch /data/CCBR/dev/spacesavers/utils/cronjob_submit.sh
