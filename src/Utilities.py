import os
import shutil

def prepare_output_directory(output_dir):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)


def sign(x):
    if x < 0:
        return -1
    elif x > 0:
        return 1
    else:
        return 0