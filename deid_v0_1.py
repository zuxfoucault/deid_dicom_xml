"""
De-identification

Prerequisite: Python 3.6+, pandas, pydicom

Usage:
    python deid_v0_1.py --source ${source_directory} --dest ${destination_directory}
"""

__author__ = "zuxfoucault"
__version__ = "0.1.0"
__license__ = "MIT"

import sys
import os
import random
import xml.etree.ElementTree as ET
import re
import argparse
import pydicom
from pathlib import Path
from pathlib import PurePath
import pandas as pd

ET.register_namespace("", "gme://caCORE.caCORE/4.4/edu.northwestern.radiology.AIM")
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")
ET.register_namespace("iso", "uri:iso.org:21090")

# xml search patters
pattern1 = re.compile("uniqueIdentifier")
pattern2 = re.compile("comment")
pattern3 = re.compile("templateUid")
pattern4 = re.compile("instanceUid")
pattern5 = re.compile("birthDate")
pattern6 = re.compile("sopClassUid")
pattern7 = re.compile("sopInstanceUid")

# modified dicom pattern
"""
SOPInstanceUid
"""


def get_file_name_list(root=None):
    p = Path(root)
    f_list = list(p.glob('**/ct'))
    return f_list


def get_dicom_file_name_list(_f):
    p = Path(_f)
    f_list = list(p.glob('**/*.dcm'))
    return f_list


def get_xml_file_name_list(_f):
    p = Path(_f)
    f_list = list(p.glob('**/*.XML'))
    return f_list


def get_dicom_SOPInstanceUid(f_dicom_list):
    """ Return Pandas DataFrame """
    _dict = dict()
    dicom_SOPInstanceUID_list = list()
    dicom_fname = list()
    for file_name in f_dicom_list:
        ds = pydicom.dcmread(str(file_name))
        dicom_SOPInstanceUID_list.append(ds.SOPInstanceUID)
        dicom_fname.append(str(file_name))
    _dict["dicom_file"] = dicom_fname
    _dict["SOPInstanceUid"] = dicom_SOPInstanceUID_list
    _dict["sopinstanceuid"] = dicom_SOPInstanceUID_list
    df = pd.DataFrame(data=_dict)
    return df


def get_xml_sopInstanceUid(file_name):
    """ Return Pandas DataFrame """
    _list = list()
    _list_f = list()
    _dict = dict()
    for _file_name in file_name:
        tree = ET.parse(_file_name)
        root = tree.getroot()
        for elem in root.iter():
            if pattern7.search(elem.tag):
                attrib = 'root'
                if elem.attrib[attrib] not in _list:
                    _list.append(elem.attrib[attrib])
                    _list_f.append(str(_file_name))

    _dict["xml_file"] = _list_f
    _dict["sopInstanceUid"] = _list
    _dict["sopinstanceuid"] = _list
    df = pd.DataFrame(data=_dict)
    return df


def mutate_uid(string_list):
    new_list = list()
    for i in string_list:
        _len = len(i)
        if _len >= 2:
            new_i = ''.join(random.sample(i, _len))
            new_list.append(new_i)
        else:
            new_list.append(i)
    return '.'.join(new_list)


def get_mutated_uid_df(df):
    new_list = list()
    for seq in df['sopinstanceuid']:
        string_list = seq.split('.')
        mutated = mutate_uid(string_list)
        new_list.append(mutated)
        def compare_mutation():
            print("pre")
            print(seq)
            print("after")
            print(mutated)
    #compare_mutation()
    df["m_sopinstanceuid"] = new_list
    return df


def add_deid_dicom_file(df, dest_file):
    dest_file = Path(dest_file)
    if not Path(dest_file).is_dir():
        dest_file.mkdir(parents=True, exist_ok=True)
    new_list = list()
    for f in df['dicom_file']:
        f = Path(f).parts[-7:]
        new_f = dest_file.joinpath(f[0])
        for i in f[1:]:
            new_f = new_f.joinpath(i)
        new_list.append(new_f)
    df['m_dicom_file'] = new_list
    return df


def add_deid_xml_file(df, dest_file):
    dest_file = Path(dest_file)
    if not dest_file.is_dir():
        dest_file.mkdir(parents=True, exist_ok=True)
    new_list = list()
    for f in df['xml_file']:
        f = Path(f).parts[-7:]
        new_f = dest_file.joinpath(f[0])
        for i in f[1:]:
            new_f = new_f.joinpath(i)
        new_list.append(new_f)
    df['m_xml_file'] = new_list
    return df


def write_deid_dicom(df):
    for file_in, file_out, new_id in zip(df['dicom_file'],
                                        df['m_dicom_file'],
                                        df["m_sopinstanceuid"]):
        ds = pydicom.dcmread(file_in)
        ds.SOPInstanceUID = new_id
        if not file_out.parent.is_dir():
            file_out.parent.mkdir(parents=True, exist_ok=True)
        ds.save_as(file_out.as_posix())
        def check():
            _ds = pydicom.dcmread(file_out.as_posix())
            print("check:")
            print(_ds.SOPInstanceUID)
        #check()


def write_deid_xml(df):
    file_in = df['xml_file'][0]
    file_out = df['m_xml_file'][0]
    if not file_out.parent.is_dir():
        file_out.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.parse(file_in)
    root = tree.getroot()

    def sopinstanceuid():
        i = 0
        for elem in root.iter():
            if pattern7.search(elem.tag):
                attrib = 'root'
                elem.attrib[attrib] = df["m_sopinstanceuid"][i]
                i += 1

    def replace_attrib():
        for elem in root.iter():
            if pattern1.search(elem.tag):
                #debug_print_attrib(attrib)
                attrib = 'root'
                elem.attrib[attrib] = "9999"

            if pattern2.search(elem.tag):
                attrib = 'value'
                elem.attrib[attrib] = "9999"

            if pattern3.search(elem.tag):
                attrib = 'root'
                elem.attrib[attrib] = "9999"

            if pattern4.search(elem.tag):
                attrib = 'root'
                elem.attrib[attrib] = "9999"

            if pattern5.search(elem.tag):
                attrib = 'value'
                elem.attrib[attrib] = "9999"

            if pattern6.search(elem.tag):
                attrib = 'root'
                elem.attrib[attrib] = "1.2.999.10008.5.1.4.3.2.7"

    sopinstanceuid()
    replace_attrib()
    tree.write(file_out)

def main_deid(source_file, dest_file):
    p_file_list = get_file_name_list(source_file)
    """ p_file_list is the uppest level directory """
    n_file = len(p_file_list)
    #jump = 75
    jump = 0 # for debug
    for i in range(n_file-jump):
        i += jump
        print(f"processing file: count {i}")
        print(f"{p_file_list[i]}")
        f_dicom_list = get_dicom_file_name_list(p_file_list[i])
        f_xml_list = get_xml_file_name_list(p_file_list[i])
        xml_sopInstanceUID_df = get_xml_sopInstanceUid(f_xml_list)
        xml_empyt = 0
        if xml_sopInstanceUID_df['xml_file'].empty:
            print('XML file not found')
            xml_empyt = 1
        dicom_SOPInstanceUID_df = get_dicom_SOPInstanceUid(f_dicom_list)
        merged_df = pd.merge(xml_sopInstanceUID_df, dicom_SOPInstanceUID_df, how='inner', on='sopinstanceuid')
        mutated_dicom_SOPInstanceUID_df = get_mutated_uid_df(dicom_SOPInstanceUID_df)
        mutated_dicom_SOPInstanceUID_df = add_deid_dicom_file(mutated_dicom_SOPInstanceUID_df, dest_file)
        write_deid_dicom(mutated_dicom_SOPInstanceUID_df)
        mutated_df = get_mutated_uid_df(merged_df)
        df = add_deid_dicom_file(mutated_df, dest_file)
        df = add_deid_xml_file(df, dest_file)
        write_deid_dicom(df)
        if not xml_empyt:
            write_deid_xml(df)


def main(args):
    """ Main entry point of the app """
    if args.source == None:
        args.source = "/home/foucault/projects/data/ForTMULung_DeID/root/"
        #args.source = "/media/foucault/TOSHIBA/去識別化/"
    if args.dest == None:
        args.dest = "/home/foucault/projects/data/ForTMULung_DeID/root_deid/"
        #args.dest = "/media/foucault/TOSHIBA/去識別化_deid/"
    main_deid(args.source, args.dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source")
    parser.add_argument("-d", "--dest")
    version = '%(prog)s ' + __version__
    parser.add_argument("-v", "--version", action="version", version=version)
    args = parser.parse_args()
    main(args)
