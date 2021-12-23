import sys

class Args:
    def __init__(self):
        self.__args = sys.argv
        self.__arg_num = len(self.__args)

    def get_args(self):
        self.__args = sys.argv
        self.__arg_num = len(self.__args)
        return self.__args

    def get_num(self) -> int:
        return self.__arg_num

    def is_arg(self, arg: str) -> bool:
        if self.__arg_num > 0:
            for a in self.__args:
                if a == arg:
                    return True
        return False

    def print(self):
        print("-> There are " + str(self.__arg_num) + " argument(s):")
        print(self.__args)
