import datetime,os

from matplotlib import pyplot as plt
import numpy as np

def render_plot(equation,dir_name="mpl_tmp"):
    try:
        x = np.array(range(-10, 11))  
        y = eval(str(equation))
        fig, ax = plt.subplots()  
        ax.grid(True)

        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        #plt.scatter(0,0, color = 'blue')
        ax.spines[["left","bottom"]].set_position("zero")
        ax.spines[['right', 'top']].set_visible(False)

        plot_filename = f"{dir_name}/{datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S.png')}"#"sympy_tmp/{}".format()
        ax.plot(x, y) 

        plt.savefig(plot_filename)

        plt.clf()

        return plot_filename
    
    except:
        return None
    