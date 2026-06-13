import os
import shutil


def prepare_output_directory(output_dir):
    """Clears output_dir on the hard drive.

    Arguments:
    output_dir -- the directory to be cleared

    Return arguments:
    (none)
    """

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)


def sign(x):
    """Computes the sign of an integer

    Arguments:
    x -- the integer to compute the sign for

    Return arguments:
    y -- the sign, -1 for negative, 1 for positive, and 0 for 0
    """

    if x < 0:
        return -1
    elif x > 0:
        return 1
    else:
        return 0
