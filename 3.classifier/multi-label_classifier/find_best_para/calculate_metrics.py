import os
import pickle

import numpy as np
import sklearn.metrics as metrics
from multi_label_utils import read_pickle
from multi_label_utils import write_json, read_json
import matplotlib.pyplot as plt


def calculate_metrics_from_file(para_file_path):
    testing_label, predicted_labels = read_pickle(para_file_path)
    hl = metrics.hamming_loss(testing_label, predicted_labels)
    ac = metrics.accuracy_score(testing_label, predicted_labels)
    ja = metrics.jaccard_score(testing_label, predicted_labels, average='weighted')
    pr = metrics.precision_score(testing_label, predicted_labels, average='weighted')
    rec = metrics.recall_score(testing_label, predicted_labels, average='weighted')
    f1 = metrics.f1_score(testing_label, predicted_labels, average='weighted')
    metric = {"hamming_loss": hl, "accuracy_score": ac, "jaccard_score": ja, "precision_score": pr,
              "recall_score": rec, "f1_score": f1}
    return metric


def draw_metric_to_para_for_method(method, para_list, y_list, metrics_list):
    figure_folder = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
                    "3.classifier\\multi_label_classifier\\find_best_para\\figures"
    for index, metric in enumerate(metrics_list):
        plt.cla()
        plt.plot(para_list, y_list[index])
        # plt.xlabel("n_estimators")
        # plt.ylabel(metric)
        figure_name = method + "-" + metric
        figure_path = os.path.join(figure_folder, figure_name)
        plt.yticks(size=18)
        plt.xticks(size=18)

        plt.savefig(figure_path)
        # plt.show()


def draw_metrics_for_methods(all_metrics):
    metrics_list = ["hamming_loss", "accuracy_score", "jaccard_score", "precision_score", "recall_score", "f1_score"]
    for method in all_metrics:
        para_list = list(range(10, 300, 10))
        y_list = []

        for index, metric_name in enumerate(metrics_list):
            single_y = []
            for para in para_list:
                metric_results = all_metrics[method][str(para)]

                single_y.append(metric_results[metric_name])
            y_list.append(single_y)
        draw_metric_to_para_for_method(method, para_list, y_list, metrics_list)



def summary_metrics():
    results_folder = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
                     "3.classifier\\multi_label_classifier\\find_best_para\\results"
    metrics_file = "all_metrics.json"
    random_times = 10
    if not os.path.exists(metrics_file):
        method_list = os.listdir(results_folder)
        all_metrics = {}
        for method_name in method_list:
            if method_name not in all_metrics:
                all_metrics[method_name] = {}
            method_folder = os.path.join(results_folder, method_name)
            results_per_para_list = os.listdir(method_folder)
            for para_file_name in results_per_para_list:
                n_estimators = para_file_name.split("-")[1]
                para_file_path = os.path.join(method_folder, para_file_name)
                metrics_per_para = calculate_metrics_from_file(para_file_path)
                if n_estimators not in all_metrics[method_name]:
                    all_metrics[method_name][n_estimators] = metrics_per_para
                else:
                    for key in metrics_per_para:
                        all_metrics[method_name][n_estimators][key] += metrics_per_para[key]

            for n_estimators in all_metrics[method_name]:
                for key in all_metrics[method_name][n_estimators]:
                    all_metrics[method_name][n_estimators][key] = \
                        all_metrics[method_name][n_estimators][key] / random_times
        write_json(metrics_file, all_metrics)
    else:
        all_metrics = read_json(metrics_file)

    draw_metrics_for_methods(all_metrics)


def add_non_zero_label(testing_label):
    new_labels = []
    for row in testing_label:
        if (row == 1).any():
            row = np.append(row, 0)
            new_labels.append(row)
        else:
            row = np.append(row, 1)
            new_labels.append(row)
    new_labels = np.array(new_labels)
    return new_labels


def test_read_pickle():
    pickle_file_path = "D:\\tencent_works\\function_inlining_prediction\\designing_classifier_for_inlining\\" \
                       "3.classifier\\multi_label_classifier\\find_best_para\\results\\RFDTBR\\n_estimators-10-0.pkl"
    testing_label, predicted_labels = read_pickle(pickle_file_path)
    testing_label = add_non_zero_label(testing_label)
    predicted_labels = predicted_labels.toarray()
    predicted_labels = add_non_zero_label(predicted_labels)
    # print(testing_label, predicted_labels)
    # print(metrics.hamming_loss(testing_label, predicted_labels))
    print(metrics.accuracy_score(testing_label, predicted_labels))
    # print(metrics.accuracy_score(testing_label, predicted_labels, average="samples"))
    # print(metrics.jaccard_score(testing_label, predicted_labels, average=None))
    print(metrics.jaccard_score(testing_label, predicted_labels, average="micro"))
    print(metrics.jaccard_score(testing_label, predicted_labels, average="macro"))
    print(metrics.jaccard_score(testing_label, predicted_labels, average="samples"))
    print(metrics.jaccard_score(testing_label, predicted_labels, average='weighted'))
    # print(metrics.precision_score(testing_label, predicted_labels, average=None))
    # print(metrics.precision_score(testing_label, predicted_labels, average='weighted'))
    # print(metrics.recall_score(testing_label, predicted_labels, average=None))
    # print(metrics.f1_score(testing_label, predicted_labels, average=None))


if __name__ == '__main__':
    # test_read_pickle()
    summary_metrics()