import numpy as np
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.metrics import multilabel_confusion_matrix
from sklearn.tree import DecisionTreeClassifier
from skmultilearn.problem_transform import ClassifierChain
from skmultilearn.problem_transform import BinaryRelevance
import spyct
import bagging
import random



class RFPCT:
    def __init__(self, n_estimators=300):
        self.name = "RFPCT"
        self.RFPCT = spyct.Model(num_trees=n_estimators)
        # self.RFPCT = random_forest.RandomForest(self.PCT_model, n_estimators)

    def train(self, training_data, training_label):
        self.RFPCT.fit(training_data, training_label)

    def predict(self, testing_data):
        predicted_labels = self.RFPCT.predict(testing_data)
        predicted_labels = np.round(predicted_labels)
        return predicted_labels

    def get_name(self):
        return self.name


class RFDTBR:
    def __init__(self, n_estimators=300):
        self.name = "RFDTBR"
        self.RFDTBR = BinaryRelevance(
            classifier=RandomForestClassifier(n_estimators),
            require_dense=[False, True]
        )

    def train(self, training_data, training_label):
        self.RFDTBR.fit(training_data, training_label)

    def predict(self, testing_data):
        predicted_labels = self.RFDTBR.predict(testing_data)
        return predicted_labels

    def get_name(self):
        return self.name


class ECCJ48:
    def __init__(self, n_estimators=300):
        self.name = "ECCJ48"
        self.ECCJ48 = None
        self.random_order = list(range(0, 8))
        random.shuffle(self.random_order)
        self.ECCJ48_base = ClassifierChain(
            classifier=DecisionTreeClassifier(),
            require_dense=[False, True],
            order=self.random_order
        )
        self.n_estimators = n_estimators

    def train(self, training_data, training_label):
        self.ECCJ48 = bagging.train_model(self.ECCJ48_base, training_data, training_label, 0.5, self.n_estimators)

    def predict(self, testing_data):
        predicted_labels = bagging.predict(self.ECCJ48, testing_data)
        return predicted_labels

    def get_name(self):
        return self.name


class EBRJ48:
    def __init__(self, n_estimators=300):
        self.name = "EBRJ48"
        self.EBRJ48 = None
        self.EBRJ48_base = BinaryRelevance(
            classifier=DecisionTreeClassifier(),
            require_dense=[False, True]
        )
        self.n_estimators = n_estimators

    def train(self, training_data, training_label):
        self.EBRJ48 = bagging.train_model(self.EBRJ48_base, training_data, training_label, 0.5, self.n_estimators)

    def predict(self, testing_data):
        predicted_labels = bagging.predict(self.EBRJ48, testing_data)
        return predicted_labels

    def get_name(self):
        return self.name


class adaboost:
    def __init__(self, n_estimators=50):
        self.name = "adaboost"
        self.adaboost_mh = BinaryRelevance(
            classifier=AdaBoostClassifier(n_estimators=n_estimators),
            require_dense=[False, True]
        )

    def train(self, training_data, training_label):
        self.adaboost_mh.fit(training_data, training_label)

    def predict(self, testing_data):
        predicted_labels = self.adaboost_mh.predict(testing_data)
        return predicted_labels

    def get_name(self):
        return self.name


class ECOCCJ48:
    "use binary relevence to split gcc and clang, use classifier chain to sequence O0 to O3"

    def __init__(self, n_estimators=300):
        self.name = "ECOCCJ48"
        self.ECCJ48_clang = ClassifierChain(
            classifier=DecisionTreeClassifier(),
            require_dense=[False, True],
            order=[0, 1, 2, 3]
        )
        self.ECCJ48_gcc = ClassifierChain(
            classifier=DecisionTreeClassifier(),
            require_dense=[False, True],
            order=[0, 1, 2, 3]
        )
        self.ECOCCJ48 = None
        self.n_estimators = n_estimators

    def train(self, training_data, training_label):
        self.ECOCCJ48 = bagging.train_model_clang_gcc(self.ECCJ48_clang, self.ECCJ48_gcc,
                                                      training_data, training_label, 0.5, self.n_estimators)

    def predict(self, testing_data):
        predicted_labels = bagging.predict_opt(self.ECOCCJ48, testing_data, return_type="ndarray")
        return predicted_labels

    def get_name(self):
        return self.name