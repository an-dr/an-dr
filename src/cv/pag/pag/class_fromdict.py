"""
Source: https://www.blog.pythonlibrary.org/2014/02/14/python-101-how-to-change-a-dict-into-a-class/
"""


class FromDict(object):
    """
    Turns a dictionary into a class
    """

    def __init__(self, dictionary):
        """Constructor"""
        for key in dictionary:
            setattr(self, key, dictionary[key])

    def __repr__(self):
        """"""
        attrs = str([x for x in self.__dict__])
        return "<FromDict: %s>" % attrs


# ----------------------------------------------------------------------
if __name__ == "__main__":
    ball_dict = {"color": "blue",
                 "size": "8 inches",
                 "material": "rubber"}
    ball = FromDict(ball_dict)
    print(ball)