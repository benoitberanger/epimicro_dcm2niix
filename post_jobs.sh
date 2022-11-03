#!/bin/bash
#SBATCH --partition=normal,bigmem
#SBATCH --time=04:00:00
#SBATCH --mem=2G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --error=logs/err_%a.txt
#SBATCH --output=logs/log_%a.txt
#SBATCH --job-name=dcm2niix_epimicro
#SBATCH --array=1-604
 
echo "SLURM_JOBID: " $SLURM_JOBID
echo "SLURM_ARRAY_JOB_ID: " $SLURM_ARRAY_JOB_ID
echo "SLURM_ARRAY_TASK_ID: " $SLURM_ARRAY_TASK_ID
 
module load dcm2niix/v1.0.20220720

bash jobs/job_dcm2niix_${SLURM_ARRAY_TASK_ID}.sh

