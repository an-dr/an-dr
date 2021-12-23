import os
from .path import get_file_list, path_disassemple
import cv2


def addlogo(back, logo, size, offset=20):
    # working
    logo_new_y = back.shape[0] * size
    logo_new_x = logo_new_y * (logo.shape[1] / logo.shape[0])

    logo = cv2.resize(logo, (int(logo_new_x), int(logo_new_y)))
    x_offset = y_offset = offset

    # y1, y2 = y_offset, y_offset + logo.shape[0]
    # x1, x2 = x_offset, x_offset + logo.shape[1]
    y2, y1 = back.shape[0] - y_offset, back.shape[0] - y_offset - logo.shape[0]
    x2, x1 = back.shape[1] - x_offset, back.shape[1] - x_offset - logo.shape[1]

    alpha_s = logo[:, :, 3] / 255.0
    alpha_l = 1.0 - alpha_s

    for c in range(0, 3):
        back[y1:y2, x1:x2, c] = (alpha_s * logo[:, :, c] + alpha_l * back[y1:y2, x1:x2, c])

    return back


def add_logo_foreach(path_mask: str, logo_path: str, scale: float = 0.1, offset: int = 10):
    files = get_file_list(path_mask)
    logo = cv2.imread(logo_path, -1)
    for f in files:
        back = cv2.imread(f, -1)
        new = addlogo(back, logo, scale, offset)
        d, p, n, e, exists = path_disassemple(f)
        to_write = os.path.join(d, p, n + "_logo" + e)
        cv2.imwrite(to_write, new)


if __name__ == '__main__':

    add_logo_foreach("../tests/*.jpg", "../tests/ZakharLogo.png", offset=40)
