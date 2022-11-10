import os       # files & dirs operations
import glob     # to walk in dirs
import json     # to load json files
import nibabel  # to load nifti headers
import re       # regular expressions
import logging  # to print
import pandas   # for DataFrame
import numpy as np
import io       # ?
import datetime # for timestamp

logging.basicConfig(level=logging.DEBUG)

main_dir = '/network/lustre/iss02/cenir/analyse/irm/users/benoit.beranger/epimicro/nifti'

logging.info(f'main dir : {main_dir}')

# get all files recursively
file_list = []
for root, dirs, files in os.walk(main_dir):
    for file in files:
        file_list.append(os.path.join(root, file))
logging.info(f'N files = {len(file_list)}')


# get only nifti files
r = re.compile(r"(.*nii$)|(.*nii.gz$)$")
file_list_nii = list(filter(r.match, file_list))
logging.info(f'N files nii = {len(file_list_nii)}')


# check is 1 nifti = 1 json
file_list_json = []
for file in file_list_nii:

    root, ext = os.path.splitext(file)
    if ext == ".gz":
        jsonfile = os.path.splitext(root)[0] + ".json"
    else:
        jsonfile = os.path.splitext(file)[0] + ".json"

    if not os.path.exists(jsonfile):
        logging.warning(f"this file has no .json associated : {file}")
        file_list_nii.remove(file)
    else:
        file_list_json.append(jsonfile)

logging.info(f'N files json = {len(file_list_json)}')


# read all json
seq = []
for json_file in file_list_json:
    try:
        with open(json_file, "r") as file:
            content = file.read()
            clean = content.replace(r'\\', r'_')  # in ~2021, dcm2iix escaping character changed from _ to \\
            seq.append(json.loads(clean))  # load the .json content as dict
    except json.decoder.JSONDecodeError:
        logging.error(f'{json_file}')

df = pandas.DataFrame(seq)

# add path
df['path'] = file_list_json


# this function will convert scalar
def int_or_round3__scalar(scalar):
    if (type(scalar) is np.float64 or type(scalar) is float) and np.isnan(scalar):
        return scalar
    scalar = float(scalar)  # conversion to the builtin float to avoid numpy.float64
    scalar = round(scalar) if round(scalar) == round(scalar,3) else round(scalar,3)
    return scalar


# this function will 'apply int_or_round3__scalar' on each element or sub-element
def int_or_round3(input):
    if type(input) == np.float64:  # this is a scalar
        return int_or_round3__scalar(input)
    else:  # tuple ? list[tuple] ?
        output_list = []
        for elem in input:
            if type(elem) is tuple:  # tuple
                output_list.append( tuple(map(int_or_round3__scalar,elem)) )
            else:
                output_list.append( int_or_round3__scalar(elem) )
        return output_list


# add info from nifti header
Matrix     = []
Resolution = []
FoV        = []

for row in df.index:

    # shortcut
    pth = df.loc[row,'path']

    # load header
    nii = nibabel.load(os.path.splitext(pth)[0] + '.nii')

    # fetch raw parameters
    matrix = nii.header.get_data_shape()
    resolution = nii.header.get_zooms()
    fov = tuple([ mx*res for mx,res in zip(matrix, resolution)])

    df.loc[row,'Mx'] = int_or_round3__scalar(matrix[0])
    df.loc[row,'My'] = int_or_round3__scalar(matrix[1])
    df.loc[row,'Mz'] = int_or_round3__scalar(matrix[2])
    if len(matrix) == 4:
        df.loc[row,'Mt'] = int_or_round3__scalar(matrix[3])
    df.loc[row,'Rx'] = int_or_round3__scalar(resolution[0])
    df.loc[row,'Ry'] = int_or_round3__scalar(resolution[1])
    df.loc[row,'Rz'] = int_or_round3__scalar(resolution[2])
    if len(resolution) == 4:
        df.loc[row,'Rt'] = int_or_round3__scalar(resolution[3])
    df.loc[row,'Fx'] = int_or_round3__scalar(fov[0])
    df.loc[row,'Fy'] = int_or_round3__scalar(fov[1])
    df.loc[row,'Fz'] = int_or_round3__scalar(fov[2])
    if len(fov) == 4:
        df.loc[row,'Ft'] = int_or_round3__scalar(fov[3])

    Matrix.append(int_or_round3(matrix))
    Resolution.append(int_or_round3(resolution))
    FoV.append(int_or_round3(fov))

df['Matrix'    ] = Matrix
df['Resolution'] = Resolution
df['FoV'       ] = FoV


# multi-line -> single-line
def clean_address(input):
    if type(input) is str:
        return re.sub('[^a-zA-Z0-9_]+', ' ', input)
    else:
        return input
df['InstitutionAddress'] = df['InstitutionAddress'].apply(clean_address)


# is DWI ?
# df['ImageTypeStr'] = df['ImageType'].apply(lambda s: '_'.join(s))

def read_bvals_bvecs(fbvals, fbvecs):
    """Read b-values and b-vectors from disk.
    Parameters
    ----------
    fbvals : str
       Full path to file with b-values. None to not read bvals.
    fbvecs : str
       Full path of file with b-vectors. None to not read bvecs.
    Returns
    -------
    bvals : array, (N,) or None
    bvecs : array, (N, 3) or None
    Notes
    -----
    Files can be either '.bvals'/'.bvecs' or '.txt' or '.npy' (containing
    arrays stored with the appropriate values).
    """
    # Loop over the provided inputs, reading each one in turn and adding them
    # to this list:
    vals = []
    for this_fname in [fbvals, fbvecs]:
        # If the input was None or empty string, we don't read anything and
        # move on:
        if this_fname is None or not this_fname:
            vals.append(None)
            continue

        if not isinstance(this_fname, str):
            raise ValueError('String with full path to file is required')

        base, ext = os.path.splitext(this_fname)
        if ext in ['.bvals', '.bval', '.bvecs', '.bvec', '.txt',
                   '.eddy_rotated_bvecs', '']:
            with open(this_fname, 'r') as f:
                content = f.read()

            munged_content = io.StringIO(re.sub(r'(\t|,)', ' ', content))
            vals.append(np.squeeze(np.loadtxt(munged_content)))
        elif ext == '.npy':
            vals.append(np.squeeze(np.load(this_fname)))
        else:
            e_s = "File type %s is not recognized" % ext
            raise ValueError(e_s)

    # Once out of the loop, unpack them:
    bvals, bvecs = vals[0], vals[1]

    # If bvecs is None, you can just return now w/o making more checks:
    if bvecs is None:
        return bvals, bvecs

    if 3 not in bvecs.shape:
        raise IOError('bvec file should have three rows')
    if bvecs.ndim != 2:
        bvecs = bvecs[None, ...]
        bvals = bvals[None, ...]
        msg = "Detected only 1 direction on your bvec file. For diffusion "
        msg += "dataset, it is recommended to have at least 3 directions."
        msg += "You may have problems during the reconstruction step."
        logging.warning(msg)
    if bvecs.shape[1] != 3:
        bvecs = bvecs.T

    # If bvals is None, you don't need to check that they have the same shape:
    if bvals is None:
        return bvals, bvecs

    if len(bvals.shape) > 1:
        raise IOError('bval file should have one row')

    if bvals.shape[0] != bvecs.shape[0]:
        raise IOError('b-values and b-vectors shapes do not correspond')

    return bvals, bvecs

df['isDWI'] = df['ImageType'].apply(lambda s: 'DIFFUSION' in s)

bval_unique = []
bval_count = []
for row in df.index:
    if df.loc[row,'isDWI']:
        file_bval = os.path.splitext(df.loc[row, 'path'])[0] + '.bval'
        file_bvec = os.path.splitext(df.loc[row, 'path'])[0] + '.bvec'
        if os.path.exists(file_bval) and os.path.exists(file_bvec):
            bval, bvec = read_bvals_bvecs(file_bval, file_bvec)
            bval_rounded = [int(np.round(val/100)*100) for val in bval]
            u, n = np.unique(bval_rounded, return_counts=True)
            bval_unique.append(u)
            bval_count.append(n)
        else:
            bval_unique.append(None)
            bval_count.append(None)
    else:
        bval_unique.append(None)
        bval_count.append(None)
df['bval_unique'] = bval_unique
df['bval_count'] = bval_count


# THE END / write file
logging.info('writing file')
timestamp = datetime.datetime.now().strftime('%Y_%m_%d')
df.to_csv(f'{timestamp}_epimicro.tsv',sep='\t')

