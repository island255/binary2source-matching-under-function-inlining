import copy
import random

import numpy


def get_selected_items(training_data, selected_index):
    train_x = []
    for index, item in enumerate(training_data):
        if index in selected_index:
            train_x.append(item)
    return train_x


def random_select(x, y, m):
    x_sub, y_sub = zip(*random.sample(list(zip(x, y)), m))
    return x_sub, y_sub


# def random_select_samples(training_data, training_label, max_samples):
#     total_length = len(training_data)
#     selected_index = random.sample(list(range(total_length)), k=int(total_length*max_samples))
#     train_x = get_selected_items(training_data, selected_index)
#     train_y = get_selected_items(training_label, selected_index)
#     return numpy.array(train_x), numpy.array(train_y)

def random_select_samples(training_data, training_label, max_samples):
    total_length = len(training_data)
    train_x, train_y = random_select(training_data, training_label, m=int(total_length*max_samples))
    return numpy.array(train_x), numpy.array(train_y)


def train_model(base_model, training_data, training_label, max_samples, n_estimators):
    trained_models = []
    for i in range(n_estimators):
        base_model_sample = copy.deepcopy(base_model)
        train_x, train_y = random_select_samples(training_data, training_label, max_samples)
        base_model_sample.fit(train_x, train_y)
        trained_models.append(base_model_sample)
    return trained_models


def train_model_clang_gcc(base_model_clang, base_model_gcc, training_data, training_label, max_samples, n_estimators):
    trained_models = []
    for i in range(n_estimators):
        base_model_c_sample = copy.deepcopy(base_model_clang)
        base_model_g_sample = copy.deepcopy(base_model_gcc)
        train_x, train_y = random_select_samples(training_data, training_label, max_samples)
        train_y_c, train_y_g = train_y[:, :4], train_y[:, 4:]
        base_model_c_sample.fit(train_x, train_y_c)
        base_model_g_sample.fit(train_x, train_y_g)
        trained_models.append([base_model_c_sample, base_model_g_sample])
    return trained_models


def predict(trained_models, testing_data, return_type="sparse_matrix"):
    predict_labels_list = []
    for trained_model in trained_models:
        predict_labels = trained_model.predict(testing_data)
        predict_labels_list.append(predict_labels)

    if return_type == "sparse_matrix":
        sum_labels = predict_labels_list[0].tocsr()
    else:
        sum_labels = predict_labels_list[0]
    for i in range(1, len(predict_labels_list)):
        if return_type == "sparse_matrix":
            sum_labels = sum_labels + predict_labels_list[i].tocsr()
        else:
            sum_labels = sum_labels + predict_labels_list[i]
    avg_labels = sum_labels / len(predict_labels_list)
    if return_type == "sparse_matrix":
        return numpy.around(avg_labels.toarray())
    else:
        return numpy.around(avg_labels)


def predict_opt(trained_models, testing_data, return_type="sparse_matrix"):
    predict_labels_list = []
    for trained_model in trained_models:
        trained_model_c, trained_model_g = trained_model
        predict_labels_c = trained_model_c.predict(testing_data)
        predict_labels_g = trained_model_g.predict(testing_data)
        predict_labels = numpy.hstack((predict_labels_c.toarray(), predict_labels_g.toarray()))
        predict_labels_list.append(predict_labels)

    if return_type == "sparse_matrix":
        sum_labels = predict_labels_list[0].tocsr()
    else:
        sum_labels = predict_labels_list[0]
    for i in range(1, len(predict_labels_list)):
        if return_type == "sparse_matrix":
            sum_labels = sum_labels + predict_labels_list[i].tocsr()
        else:
            sum_labels = sum_labels + predict_labels_list[i]
    avg_labels = sum_labels / len(predict_labels_list)
    if return_type == "sparse_matrix":
        return numpy.around(avg_labels.toarray())
    else:
        return numpy.around(avg_labels)