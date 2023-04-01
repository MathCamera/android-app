
#import matplotlib.pyplot as plt  
import datetime,os

from matplotlib import pyplot as plt
import numpy as np

def render_plot(equation,dir_name="mpl_tmp"):
    try:
        x = np.array(range(-10, 11))  
        y = eval(str(equation))
        plt.plot(x, y)  
        plt.grid(alpha =.6, linestyle ='--')

        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        plot_filename = f"{dir_name}/{datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S.png')}"#"sympy_tmp/{}".format()
        
        plt.savefig(plot_filename)

        plt.clf()

        return plot_filename
    
    except:
        return None