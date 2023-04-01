
#import matplotlib.pyplot as plt  
import datetime,os

from matplotlib import pyplot as plt
import numpy as np

from modules.plotting.mpl import FigureCanvasKivyAgg

def render_plot(equation):
    x = np.array(range(-10, 11))  
    y = eval(str(equation))
    plt.plot(x, y)  
    plt.grid(alpha =.6, linestyle ='--')

    #plot_filename = f"{dir_name}/{datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S.png')}"#"sympy_tmp/{}".format()
    
    #plt.savefig(plot_filename)

    result = FigureCanvasKivyAgg(plt.gcf())

    return result