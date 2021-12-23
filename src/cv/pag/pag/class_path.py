import os
import shutil
from typing import Union
from . import static_functions
from enum import Enum


class PathType(Enum):
    UNKNOWN = -1
    FOLDER = 0
    FILE = 1
    rsvd = 2
    HTTP = 3
    SVN = 4


class Path:
    class Errors:
        @staticmethod
        def type_er(good_pathtype: Union[PathType, list]):
            str_pathtype = ""
            if type(good_pathtype) == list and type(good_pathtype[0]) == PathType:
                for type_i in good_pathtype:
                    str_pathtype += str(type_i)
                    str_pathtype += " or "
                str_pathtype = str_pathtype.rstrip(" or ")
            elif type(good_pathtype) == PathType:
                str_pathtype = str(good_pathtype)
            else:
                raise TypeError
            er_str = "Must be " + str_pathtype
            raise TypeError(er_str)

        @staticmethod
        def any(test: str):
            raise BaseException("Some error")

    def __init__(self, string: str = "", in_type: PathType = PathType.UNKNOWN):
        if type(string) == Path:
            string = str(string)
        # fields:
        self._type = self.Type(in_type)  # path type
        self._val = self.Value(string)  # __value
        # self.type = self._type
        # self._val._unformat()
        self._filetype = ""
        self._type.id(self._val.v)  # id
        self._val.reformat_as(self._type)
        self.id_filetype()

    def __eq__(self, other):
        if isinstance(other, self.__class__):  # if has the same class
            res = (other._val.v == self._val.v) and (other._type == self._type)
            return res
        else:
            return self._val.v == other

    def __ne__(self, other):
        if isinstance(other, self.__class__):  # if has the same class
            res = ((self._type.v, self._val.v) != (other._type.v, other._val.v))
            return res
        else:
            return self._val.v != other

    def __repr__(self):
        return str(self.s())

    def __str__(self):
        return str(self.s())

    def __add__(self, other):
        result = Path(self.s())
        if isinstance(other, self.__class__):
            result.add(other.s())
        else:
            result.add(str(other))
        result.id()
        return result

    def __iter__(self):
        return self.s()

    def __next__(self):
        return self.s().__next__()

    def id(self):
        self._type.id(self._val)
        self.id_filetype()

    def id_filetype(self):
        if self._type == PathType.FILE:
            ext_location = self._val.v[-5:]
            dot = ext_location.find(".")
            self._filetype = ext_location[dot + 1:]
        else:
            self._filetype = ""

    def get_filetype(self):
        self.id_filetype()
        return self._filetype

    def add(self, s):
        self._val.add(s, self._type)
        self.id()
        self.id_filetype()

    def set(self, s):
        self._val.set(s)
        self.id()
        self.id_filetype()

    def set_type(self, t: PathType):
        self._val.reformat_as(t)
        self._type.set(t, self._val)

    def s(self) -> str:
        return str(self._val)

    def rem(self):
        self._val.remove()

    def remove_last(self):
        self._val.remove()
        self.id()
        self.id_filetype()

    def get_parent_dir(self):
        p = Path(self.s())
        p.remove_last()
        return p

    def create(self):
        if self.get_type() == PathType.FOLDER:
            if not os.path.exists(self.s()):
                os.makedirs(self.s())
        elif self.get_type() == PathType.FILE:
            if not os.path.exists(self.s()):
                new_f = open(self.s(), "w+")
                new_f.close()
        else:
            raise self.Errors.type_er([PathType.FOLDER, PathType.FILE])

    def write(self, in_str: str):
        self.create()
        if self.get_type() == PathType.FILE:
            f = open(self.s(), "w+")
            f.write(in_str)
            f.close()
        elif self.get_type() == PathType.FOLDER:
            pass
        else:
            raise self.Errors.type_er([PathType.FOLDER, PathType.FILE])

    @staticmethod
    def gwd():
        wd = static_functions.get_py_file_folder()
        working_dir_path = Path(wd)
        return working_dir_path

    def copy_to(self, dest):
        # if (self.get_type() == PathType.FOLDER or self.get_type() == PathType.FILE) \
        #         and (dest.get_type() == PathType.FOLDER or dest.get_type() == PathType.FILE):
        if static_functions.is_file_or_folder(dest.s()) == 1:
            if os.path.exists(self.s()) and (not os.path.exists(dest.s())):
                shutil.copy(self.s(), dest.s())
        elif static_functions.is_file_or_folder(dest.s()) == 2:
            if os.path.exists(self.s()) and (os.path.exists(dest.s())):
                shutil.copy(self.s(), dest.s())
        # else:
        # raise self.Errors.type_er([PathType.FOLDER, PathType.FILE])

    @staticmethod
    def get_script_folder():
        f = os.getcwd()
        p = Path(f)
        p.set_type(PathType.FOLDER)
        return p

    def get_full_path(self):
        self_t = self._type.v
        pstr = self._val.v
        tp = PathType
        if (self_t == tp.FOLDER) or (self_t == tp.FILE):
            if (pstr[1:3] == ":\\") or (pstr[1:2] == ":/"):
                return self
            else:
                loc_fol = self.get_script_folder()
                return loc_fol + self
        else:
            return self

    def last_str(self):
        """
        docs.python.org/2/library/os.path.html -> os.path.html
        :return:
        """
        return os.path.split(str(self._val))[1]

    def dir_str(self):
        return os.path.split(str(self._val))[0]

    def get_type(self):
        return self._type.v

    def file_notexist_used(self):
        if os.path.exists(self.s()):
            try:
                os.rename(self.s(), self.s())
                return 0
            except OSError:
                return 1
        else:
            return -1

    def is_exist(self):
        return os.path.exists(self.s())

    class Type:
        def __init__(self, type_: PathType):
            self.v = type_

        def __repl__(self):
            return self.v

        def __str__(self):
            return str(self.v)

        def __eq__(self, other):
            return self.v == other

        def id(self, path_str: str):
            str2id = str(path_str)
            try:
                # starting part:
                if (str2id[:8] == "https://") or (str2id[:3] == "www"):
                    self.set(PathType.HTTP, str2id)
                    return
                if (str2id[:6] == "svn://"):
                    self.set(PathType.SVN, str2id)
                    return
                if (str2id[1:3] == ":\\") or (str2id[1:3] == ":/"):
                    self.set(PathType.FOLDER, str2id)
                # starting part.
                # ending part:
                if (str2id[-1:] == "/") \
                        or (str2id[-1:][0] == "\\"):
                    self.set(PathType.FOLDER, str2id)
                    return
                # === file?
                extention = str2id[-5:].find(".")
                if extention != -1:  # found dot
                    self.set(PathType.FILE, str2id)
                    # self._filetype =
                    return
                # ending part.
            except IndexError:
                return

        def set(self, t: PathType, p: str):
            self.v = t
            return p

        def get(self):
            print(self.v)
            return self.v

    class Value:
        def __init__(self, string: str):
            self.v = ""
            string = string.strip("\"")
            string = string.strip("\'")
            self.set(string)

        def __repl__(self):
            return self.v

        def __str__(self):
            return self.v

        def set(self, s: str):
            """
            Sets value of Path value
            :param s:
            :return:
            """
            try:
                str(s)
            except TypeError:
                return
            self.v = s

        def _unformat(self):
            p = str(self.v)
            p = p.replace("svn://", '')
            p = p.replace("http://", '')
            p = p.replace("file://", '')
            p = p.strip("/")
            p = p.strip("\\")
            p = p.strip(":")
            p = p.strip("\"")
            p = p.strip("\'")
            self.v = p

        def reformat_as(self, t: PathType):
            """
            Formats path string as path of specific type
            :param t:
            :return:
            """
            self._unformat()
            p = self.v
            p = p.replace("\\", "/")
            p = p.strip("\"")
            if t == PathType.FOLDER:
                p = p.rstrip("/")
                p = p.rstrip("\\")
                p = p.rstrip("/")
                p = p.rstrip("\\")
            if t == PathType.FILE:
                p = p.rstrip("/")
                p = p.rstrip("\\")
                p = p.rstrip("/")
                p = p.rstrip("\\")
                # p = "file://"+ p
            elif t == PathType.HTTP:
                p = p.strip("/")
                p = p.strip("\\")
                p = p.strip("/")
                p = p.strip("\\")
                p = "http://" + p
            elif t == PathType.SVN:
                p = p.strip("/")
                p = p.strip("\\")
                p = p.strip("/")
                p = p.strip("\\")
                p = "svn://" + p
            else:
                p = p.strip("/")
                p = p.strip("\\")
                p = p.strip("/")
                p = p.strip("\\")
            self.v = p

        def add(self, new_p: str, type_: PathType):
            p = str(self.v)  # path
            new_p = str(new_p)
            new_p = new_p.strip("/")
            new_p = new_p.strip("\\")
            t = type_  # type
            if t == PathType.FILE:
                print("Can't ADD path to path with FILE PathType")
                r = p
            elif t == PathType.FOLDER:
                r = os.path.join(p, new_p)
            elif (t == PathType.HTTP) or (t == PathType.SVN):
                p = p.strip("/")
                p = p.strip("\\")
                new_p = new_p.lstrip("/")
                new_p = new_p.lstrip("\\")
                r = p + "/" + new_p
            else:
                r = p + new_p
            self.set(r)
            self.reformat_as(t)

        def remove(self):
            old_p = self.v
            p = os.path.dirname(old_p)
            self.set(p)

    @staticmethod
    # ======================== other:
    def basename(s):
        """good file without / or \ and good for Win"""
        s = s.strip("/")
        s = s.strip("\\")
        for ch in ['<', '>', ':', '/', '\\', '|', '?', '*']:
            if ch in s:
                s = s.replace(ch, '-')
        return s
