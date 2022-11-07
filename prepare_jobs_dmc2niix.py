import shutil
import os
import glob

input_dir = '/network/lustre/iss02/epimicro/patients/raw'
output_dir = '/network/lustre/iss02/cenir/analyse/irm/users/benoit.beranger/epimicro'

# preps out dirs

nifti_dir = os.path.join(output_dir, 'nifti')
jobs_dir  = os.path.join(output_dir, 'jobs' )
logs_dir  = os.path.join(output_dir, 'logs' )

shutil.rmtree(jobs_dir, ignore_errors=True)
shutil.rmtree(logs_dir, ignore_errors=True)
os.makedirs  (jobs_dir, exist_ok=True)
os.makedirs  (logs_dir, exist_ok=True)


# prep jobs

dcm_dir_list = glob.glob(input_dir + '/pat*/neuroimages/dicom')

pat_raw_dir_list = [os.path.dirname(os.path.dirname(p)) for p in dcm_dir_list]
pat_id_list = [os.path.basename(p) for p in pat_raw_dir_list]

pat_nifti_dir = [os.path.join(nifti_dir, pid) for pid in pat_id_list]
[ os.makedirs(pth,exist_ok=True) for pth in pat_nifti_dir]

job_list = []
for idx, dcm_dir in enumerate(dcm_dir_list):
    # pat_all_dcm_dir = [x[0] for x in os.walk(dcm_dir)]
    # job_list.append(pat_all_dcm_dir)

    for dirpath, dirnames, filenames in os.walk(dcm_dir):
        # print(f"{dirpath} {dirnames}")
        if len(dirnames) == 0:
            job_dict = {
                "pat_id" : pat_id_list[idx],
                "dcm_dir" : dirpath,
                "nii_dir" : os.path.join(pat_nifti_dir[idx], dirpath.replace(dcm_dir+"/", '')),
            }
            job_list.append(job_dict)

# write jobs

counter = 0
for job in job_list:
    cmd = f'dcm2niix -ba n -f "v_%n_S%s_%d" -o {job["nii_dir"]} {job["dcm_dir"]}'
    if not os.path.exists(job["nii_dir"]):
        counter += 1
        job_path = os.path.join(jobs_dir, f'job_dcm2niix_{counter}.sh')
        # print(job_path)
        os.makedirs(job["nii_dir"])
        with open(job_path, mode='wt', encoding='utf-8') as fid:
            fid.write(cmd)

