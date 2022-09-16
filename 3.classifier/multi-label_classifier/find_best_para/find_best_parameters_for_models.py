import os.path

from multi_label_utils import extract_datas_and_target, read_csv, split_dataset_by_projects, write_json, write_pickle

from tqdm import tqdm
import numpy as np
from multiprocessing import Pool
from models import ECCJ48, ECOCCJ48x, ECOCCJ48, RFPCT, RFDTBR, EBRJ48, adaboost



def write_evaluate_results(result_folder, model_name, n_estimators, labels, x):
    if os.path.exists(result_folder) is False:
        os.mkdir(result_folder)
    model_folder = os.path.join(result_folder, model_name)
    if os.path.exists(model_folder) is False:
        os.mkdir(model_folder)
    result_file_name = "n_estimators-" + str(n_estimators) + "-" + str(x) + ".pkl"
    result_file_path = os.path.join(model_folder, result_file_name)
    # np.savetxt(result_file_path, confusion_matrix)
    write_pickle(result_file_path, labels)


def train_and_test_model(para_list):
    model, n_estimators, x, result_folder, training_data, training_label, testing_data, testing_label = para_list
    model_with_specific_para = model(n_estimators)
    model_name = model_with_specific_para.get_name()
    dest_file_path = os.path.join(result_folder, model_name,
                                  "n_estimators-" + str(n_estimators) + "-" + str(x) + ".pkl")
    if os.path.exists(dest_file_path):
        return
    model_with_specific_para.train(training_data, training_label)
    predicted_labels = model_with_specific_para.predict(testing_data)
    # confusion_matrix = multilabel_confusion_matrix(testing_label, predicted_labels)
    write_evaluate_results(result_folder, model_name, n_estimators, [testing_label, predicted_labels], x)


def evaluate_single_model(iter_times, n_estimators_list, call_site_feature_and_labels, model, result_folder):
    parameter_list = []
    for x in range(iter_times):
        train_csv_content, test_csv_content, train_projects, test_projects = \
            split_dataset_by_projects(call_site_feature_and_labels)

        training_data, training_label = extract_datas_and_target(train_csv_content, type="train")
        testing_data, testing_label = extract_datas_and_target(test_csv_content, type="test")
        for n_estimators in n_estimators_list:
            para_list = [model, n_estimators, x, result_folder,
                         training_data, training_label, testing_data, testing_label]
            parameter_list.append(para_list)

    process_num = 1
    p = Pool(int(process_num))
    with tqdm(total=len(parameter_list)) as pbar:
        for i, res in tqdm(enumerate(p.imap_unordered(train_and_test_model, parameter_list))):
            pbar.update()
    p.close()
    p.join()


def evaluate_models():
    call_site_csv_file = "call_site_feature_and_labels.csv"
    call_site_feature_and_labels = read_csv(call_site_csv_file)
    result_folder = "results"
    iter_times = 10
    n_estimators_list = list(range(10, 310, 10))
    for model in [ECCJ48, ECOCCJ48x, ECOCCJ48, RFPCT, RFDTBR, EBRJ48, adaboost]:
        print("evaluating model {}".format(model))
        evaluate_single_model(iter_times, n_estimators_list, call_site_feature_and_labels, model, result_folder)


if __name__ == '__main__':
    evaluate_models()
