import sys
sys.path.insert(0, "/Users/tr.sakrapee/Documents/GitHub/KaSim/")
import KaSimWrapper as kw

import matplotlib.pyplot as plot

kasim = kw.KaSimKappaSim(None, True)
kasim.load_file("simpleBinding.ka")

kasim.run_until_time(1)
kasim.delete_agent_value("B()", 500)
kasim.delete_agent_value("A()", 500)
kasim.run_until_time(2)
plot_result = kasim.get_all_values_by_time()
if plot_result is not None:
    plot_legend = plot_result[0]
    plot_data = plot_result[1]
    fig, ax = plot.subplots()
    line1, = ax.plot(plot_data[:, 0], plot_data[:,1], '--', linewidth=2,
                     label=plot_legend[1])

    line2, = ax.plot(plot_data[:, 0], plot_data[:, 2], dashes=[30, 5, 10, 5],
                     label=plot_legend[2])

    ax.legend(loc='lower right')
    plot.show()
