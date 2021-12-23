# *************************************************************************
#
# Copyright (c) 2021 Andrei Gramakov. All rights reserved.
#
# This file is licensed under the terms of the MIT license.  
# For a copy, see: https://opensource.org/licenses/MIT
#
# site:    https://agramakov.me
# e-mail:  mail@agramakov.me
#
# *************************************************************************

import os
import ftplib
import datetime
import pag
import pathlib
import shutil


if __name__ == '__main__':
    in_file = "CV.docx"
    out_file = "Andrei_Gramakov_CV"

    d = pag.Docx(in_file)
    d.update_path(f"../../cv/{out_file}.docx")
    d.to_pdf()
    # pag.static_functions.docx2pdf(in_file, out_file_i)
    # Send2Ftp(f"{out_file}.pdf")
    # Send2Ftp(f"{out_file_y}.pdf")
