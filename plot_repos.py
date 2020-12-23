# library and dataset
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np


def plot_test():
    # Create data
    df = pd.DataFrame({'x': range(1, 101), 'y': np.random.randn(100) * 15 + range(1, 101),
                       'z': (np.random.randn(100) * 15 + range(1, 101)) * 2})

    # plot with matplotlib
    plt.plot('x', 'y', data=df, marker='o', color='mediumvioletred')
    #plt.show()

def plot_line(x_data, y_data_dict, x_label, y_label,  title):

    fig, ax = plt.subplots()
    for k,v in y_data_dict.items():
        ax.plot(x_data, v, label = k)
    ax.set(xlabel = x_label, ylabel=y_label, title = title)
    ax.legend()
    #fig.savefig('test')
    plt.show()

