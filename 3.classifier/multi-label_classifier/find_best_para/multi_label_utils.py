import csv
import json
import os
import pickle
import random

import numpy


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def write_json(file_path, obj):
    with open(file_path, "w") as f:
        json_str = json.dumps(obj, indent=2)
        f.write(json_str)


def read_pickle(pickle_file):
    with open(pickle_file, "rb") as f:
        return pickle.load(f)


def write_pickle(pickle_file, obj):
    with open(pickle_file, "wb") as f:
        pickle.dump(obj, f)


def read_csv(call_site_csv_file):
    csv_reader = csv.reader(open(call_site_csv_file, "r"))
    csv_content = []
    for line in csv_reader:
        csv_content.append(line)
    return csv_content


def extract_datas_and_target(call_site_csv_content, type="all"):
    data = []
    label = []
    for line in call_site_csv_content[1:]:
        if type == "all":
            data.append(list(map(int, line[1:-8])))
        else:
            data.append(list(map(int, line[:-8])))
        labels = list(map(int, line[-8:]))
        label.append(labels)
        # label.append(line[-1])
    return numpy.array(data), numpy.array(label)


def split_dataset_by_projects(call_site_feature_and_labels, train_percent=0.9):
    all_project_name = []
    for line in call_site_feature_and_labels[1:]:
        if line[0] not in all_project_name:
            all_project_name.append(line[0])
    train_csv_content = [call_site_feature_and_labels[0][1:]]
    test_csv_content = [call_site_feature_and_labels[0][1:]]
    train_project_length = int(len(all_project_name) * train_percent)
    train_projects = random.sample(all_project_name, train_project_length)
    for line in call_site_feature_and_labels[1:]:
        if line[0] in train_projects:
            train_csv_content.append(line[1:])
        else:
            test_csv_content.append(line[1:])
    test_projects = list(set(all_project_name).difference(set(train_projects)))
    return train_csv_content, test_csv_content, train_projects, test_projects


def split_dataset_by_selecting_two_project(call_site_feature_and_labels):
    all_project_name = []
    for line in call_site_feature_and_labels[1:]:
        if line[0] not in all_project_name:
            all_project_name.append(line[0])
    train_csv_content = [call_site_feature_and_labels[0][1:]]
    test_csv_content = [call_site_feature_and_labels[0][1:]]
    train_projects = ["coreutils", "binutils"]
    for line in call_site_feature_and_labels[1:]:
        if line[0] in train_projects:
            train_csv_content.append(line[1:])
        else:
            test_csv_content.append(line[1:])
    return train_csv_content, test_csv_content
