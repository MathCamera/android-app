from sympy import sympify
from sympy.plotting import plot
import os,datetime

class Plotting:
    def generate_plot(self,equation):
        if not os.path.exists("sympy_tmp"):
            os.makedirs("sympy_tmp")

        graph = plot(sympify(str(equation)), show=False)
        filename = "sympy_tmp/{}".format(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S.png'))
        graph.save(filename)

        return filename