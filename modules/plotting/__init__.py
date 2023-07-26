import datetime,os
from matplotlib import pyplot as plt
import numpy as np

def render_plot(equation,dir_name="mpl_tmp",theme="light"):
    try:
        x = np.array(range(-8, 9))  
        y = eval(str(equation))
        fig, ax = plt.subplots()  
        ax.grid(True,linewidth=1)

        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        #plt.scatter(0,0, color = 'black')
        ax.spines[["left","bottom"]].set_position("zero")
        ax.spines[['right', 'top']].set_visible(False)
        
        #ax.spines[["left","bottom"]].set_color("green")

        plot_filename = f"{dir_name}/{datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S.png')}"#"sympy_tmp/{}".format()
        ax.plot(x, y,color="#9F4576") 

        plt.savefig(plot_filename,bbox_inches='tight', transparent=True, pad_inches=0.1)
        plt.clf()

        return plot_filename
    
    except:
        return None
        