"""
IDA Python plugin for exporting features from IDA databases. Part of the Pigaios
Project.

Copyright (c) 2018, Joxean Koret

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

# from __future__ import print_function

import re
import os
import imp
import sys
import json
import time

from idc import *
from idaapi import *
from idautils import *

import idaapi
import idautils
import idc
from sets import Set


def function_extract(func, function_name_to_address, callee_address):
    caller_callee_pairs = []

    for ref_ea in CodeRefsTo(func, 0):
        caller_name = GetFunctionName(ref_ea)
        print("caller_name: {}".format(caller_name))
        if caller_name not in function_name_to_address:
            continue
        caller_address = function_name_to_address[caller_name]
        # caller_callee_pairs.append({"caller_name": caller_name, "caller_address": ref_ea})
        caller_callee_pairs.append([caller_address, callee_address, ref_ea])
    return caller_callee_pairs


def controller():
    # basename = idc.GetInputFile()
    basename = idaapi.get_input_file_path()
    function_name_to_address = {}
    function_range = {}

    funcs = idautils.Functions()

    for f in funcs:
        func_name = GetFunctionName(f)
        function_name_to_address[func_name] = f
        start_address = f
        end_address = FindFuncEnd(f)
        function_range[func_name] = {"start_address": start_address, "end_address":end_address}
    # scan all functions to extract number of functions and add them to the funcs_id
    # print(function_name_to_address)
    all_caller_callee_pairs = []
    funcs = idautils.Functions()
    for f in funcs:
        func_name = GetFunctionName(f)
        print(func_name)
        callee_address = function_name_to_address[func_name]
        print(callee_address)
        caller_callee_pairs = function_extract(f, function_name_to_address, callee_address)  # extract functions data
        print(caller_callee_pairs)
        all_caller_callee_pairs += caller_callee_pairs

    # all_caller_callee_pairs = list(set(all_caller_callee_pairs))
    # print(all_caller_callee_pairs)
    caller_callee_dict_json_file = basename + ".fcg"
    print(caller_callee_dict_json_file)
    json_str = json.dumps(all_caller_callee_pairs, indent=2)
    with open(caller_callee_dict_json_file, "w") as fw:
        fw.write(json_str)

    function_range_file = basename + ".json"
    json_str = json.dumps(function_range, indent=2)
    with open(function_range_file, "w") as fw:
        fw.write(json_str)


# -------------------------------------------------------------------------------
def json_dump(x):
    return json.dumps(x, ensure_ascii=False)


if __name__ == "__main__":
    idaapi.autoWait()
    string_list = []
    controller()
    idaapi.qexit(0)
