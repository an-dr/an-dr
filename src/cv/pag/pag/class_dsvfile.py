from . import PathType, Path


class DsvFile:
    def __init__(self):
        self.file_path = Path()
        self._data = []
        self.rows = -1
        self.cols = -1

    def set_data_from_file(self, file_path: Path):

        f = open(file_path.s(), 'r')
        f_data = f.read()
        f.close()
        self._parse_string(f_data)
        self._normalize_and_get_dimentions()

    def set_data_from_string(self, in_str: str):
        self._parse_string(in_str)
        self._normalize_and_get_dimentions()

    def set_data_from_list_of_lists(self, in_list: list):
        self._data = in_list
        self._normalize_and_get_dimentions()

    def set_path_to_read_n_write(self, path: Path):
        if path.get_type() == PathType.FILE:
            self.file_path = path
        else:
            print("this is not a file type if path")

    def _parse_string(self, in_string: str, d=';', n_line='\n') -> list:
        parsed_content = []
        line = []
        cell = ""
        for symb in in_string:
            if symb == d:
                line.append(cell)
                cell = ""
            elif symb == n_line:
                line.append(cell)
                parsed_content.append(line)
                line = []
                cell = ""
            else:
                cell += symb
        parsed_content.append(line)  # last_str line
        last = len(parsed_content)
        el = parsed_content[last - 1]
        if len(el) == 0:  # if the last_str line was empty
            parsed_content.pop()
        self._data = parsed_content
        return parsed_content

    def _normalize_and_get_dimentions(self):
        # finding out max
        max_col = 0
        for row in self._data:
            if max_col < len(row):
                max_col = len(row)
        # normalalisation
        for row in self._data:
            while len(row) < max_col:
                row.append(';')
        self.cols = max_col
        self.rows = len(self._data)

    def get_data_dimensions(self):
        return [self.cols, self.rows]

    def print_data(self):
        for row in self._data:
            print(row)

    def write(self):
        data2w = ""
        for row in self._data:
            for cell in row:
                data2w += (cell + ';')
            data2w += '\n'
        f = open(self.file_path.s(), 'w+')
        f.write(data2w)
        f.close()

    def append_column(self):
        for row in self._data:
            row.append("")

    def append_row_2bottom(self):
        row_size = self.cols
        new_raw = "" * row_size
        self._data.append(new_raw)

    def append_row_2top(self):
        row_size = self.cols
        new_raw = [""] * row_size
        self._data.insert(0, new_raw)

    def get_all_data(self):
        return self._data

    def get_row(self, row):
        return self._data[row]

    def get_data_column(self, col):
        col_vals = []
        for row in self._data:
            col_vals.append(row[col])
            return col_vals

    def get_data_cell(self, col, row):
        return self._data[row][col]

    def set_cell(self, col, row, text):
        while 1:
            try:
                self._data[row - 1][col] = text
                return text
            except IndexError:
                self._data[row - 1].append("")
