import numpy as np
import matplotlib.pyplot as plt
from sklearn.svm import SVC
from apps.utils import plot_decision_regions

def scatter():
    np.random.seed(0)
    X_xor = np.random.randn(200, 2)
    y_xor = np.logical_xor(X_xor[:, 0] > 0, X_xor[:, 1] > 0)
    y_xor = np.where(y_xor, 1, -1)
    plt.scatter(X_xor[y_xor==1, 0], X_xor[y_xor==1, 1],
            c='b', marker='x', label='1')
    plt.scatter(X_xor[y_xor==-1, 0], X_xor[y_xor==-1, 1],
            c='r', marker='o', label='-1')
    plt.ylim(-3.0)
    plt.legend()
    plt.show()
    plt.close()
    return X_xor, y_xor

def kernel(X_xor, y_xor):
    svm = SVC(kernel='rbf', random_state=0, gamma=0.10, C=10.0)
    svm.fit(X_xor, y_xor)
    plot_decision_regions(X_xor, y_xor, classifier=svm)
    plt.legend(loc='upper left')
    plt.show()
    plt.close()

def selftest():
    X_xor, y_xor = scatter()
    kernel(X_xor, y_xor)

if __name__ == '__main__':
    selftest()

