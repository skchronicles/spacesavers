#!/bin/bash
#SBATCH --job-name="spacesavers"
#SBATCH --mem=40g
#SBATCH --partition="ccr,norm"
#SBATCH --time=96:00:00
#SBATCH --cpus-per-task=2

# This is a sbatch script which can be run to submit a cronjob to the sbatch queue
# cronjobs do not source the ~/.bashrc explicitly hence:
source $HOME/.bashrc
bash /data/CCBR/dev/spacesavers/utils/cronjob.sh
