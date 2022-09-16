#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import argparse
from multiprocessing import Pool
from tqdm import tqdm


def prepare_for_running_ida(binary_path):
    for post in [".id0", ".id1", ".id2", ".nam", ".i64"]:
        ida_file_path = binary_path + post
        if os.path.exists(ida_file_path):
            try:
                os.remove(ida_file_path)
            except:
                pass


def run(src_map):
    IDA_path = "D:\\IDA_Pro_v7.0_Portable\\ida64.exe"
    script_path = os.path.join(os.getcwd(), "IDA_extract_fcg.py")

    TIMEOUT = 30000

    try:
        file_path = src_map['path']
        prepare_for_running_ida(file_path)
        # cmd_args = [IDA_path, "-A", "-S\"{}\"".format(script_path), file_path]
        cmd = '"{}" -A -S"{}" {}'.format(IDA_path, script_path, file_path)
        # print(cmd)
        # return
        output_file_path = file_path + ".fcg"
        # if os.path.exists(output_file_path):
        #     return

        p = None
        try:
            # ex = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE)
            p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE)
            # p = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
            #                      start_new_session=True, shell=True)
            p.communicate(timeout=TIMEOUT)
            p.wait()
        except Exception as e:
            print('[except error]', e)
            if p:
                p.kill()
                p.terminate()
                os.killpg(p.pid, 15)
    except Exception as e:
        print('[exception]', e)
        pass


def batch(list_file, process_num, output=None):
    task_list = open(list_file, 'r').readlines()
    task_list = [{'id': i, 'output': output, 'path': os.path.abspath(l.strip())} for i, l in enumerate(task_list)]
    p = Pool(int(process_num))
    with tqdm(total=len(task_list)) as pbar:
        for i, res in tqdm(enumerate(p.imap_unordered(run, task_list))):
            pbar.update()
    p.close()
    p.join()


def parameter_parser():
    parser = argparse.ArgumentParser(description="Run ghidra")
    parser.add_argument("-f", "--file", type=str, help="single file path")
    parser.add_argument("-l", "--list", type=str, help="files path list")
    parser.add_argument("-o", "--output", type=str, help="output directory path")
    parser.add_argument("-c", "--cpu", type=int, default=1, help="multiprocess number")
    parser.add_argument("-g", "--ghidra", type=str, required=True, help="ghidra home directory")
    parser.add_argument("-s", "--script", type=str, default=os.getcwd(), help="ghidra script directory")
    parser.add_argument("-p", "--proj", type=str, default="/tmp", help="ghidra project directory")
    parser.add_argument("-t", "--timeout", type=int, default=30000, help="ghidra process timeout")
    return parser.parse_args()
