import os
import glob


def create_folder(directory: str) -> int:
    if not os.path.exists(directory):
        return 0
    else:
        return 1

def is_file_or_folder(p: str) -> int:
    if os.path.isfile(p):
        return 1
    elif os.path.isdir(p):
        return 2
    else:
        return 0


def get_py_file_folder() -> str:
    return str(os.path.realpath(__file__))


def get_py_file_drive() -> str:
    p = get_py_file_folder()
    return os.path.splitdrive(p)[0]


def set_working_dir_to(work_dir=''):
    if work_dir is '':
        work_dir = str(os.path.realpath(__file__))
    os.chdir(work_dir)

def get_file_list(path_mask: str):
    return glob.glob(path_mask)


def path_disassemple(in_path: str):
    path_abs = os.path.abspath(in_path)

    win_drive, tail = os.path.splitdrive(path_abs)
    path, f_ext = os.path.split(tail)
    name, extension = os.path.splitext(f_ext)
    exists = os.path.exists(path_abs)
    return win_drive, path, name, extension, exists


if __name__ == '__main__':
    d, p, n, e, exists = path_disassemple("../readme.md")
    print(os.path.join(d, p, n + e))
