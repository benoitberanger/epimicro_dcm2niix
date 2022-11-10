import os       # files & dirs operations
import glob     # to walk in dirs
import json     # to load json files
import nibabel  # to load nifti headers
import re       # regular expressions
import logging  # to print
import pandas   # for DataFrame
import numpy as np

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

# THE END / write file
logging.info('writing file')
df.to_csv('dataset.tsv',sep='\t')

0
