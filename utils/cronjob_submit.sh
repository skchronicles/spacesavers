#!/bin/bash
#SBATCH --job-name="spacesavers"
#SBATCH --mem=40g
#SBATCH --partition="ccr,norm"
#SBATCH --time=96:00:00
#SBATCH --cpus-per-task=2
source $HOME/.bashrc
bash /data/CCBR/dev/spacesavers/utils/cronjob.sh
