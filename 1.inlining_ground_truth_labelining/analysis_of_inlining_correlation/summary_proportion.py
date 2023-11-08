import json


def read_json(file_path):
    with open(file_path, "r") as f:
        file_content = json.load(f)
        return file_content


def main():
    opt_correlation_file = "opt_correlation_file.json"
    opt_correlation = read_json(opt_correlation_file)
    included = 0
    number = 0
    for compiler in opt_correlation:
        number += opt_correlation[compiler]["O0"][0] * 3
        number += opt_correlation[compiler]["O1"][1] * 2
        number += opt_correlation[compiler]["O2"][2]
        included += sum(opt_correlation[compiler]["O0"][1:])
        included += sum(opt_correlation[compiler]["O1"][2:])
        included += sum(opt_correlation[compiler]["O2"][3:])
    print(included, number, included/number)


if __name__ == '__main__':
    main()