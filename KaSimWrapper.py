
import sys
import os
import getopt
import time
import uuid
import numpy as np

sys.path.insert(0, "/Users/tr.sakrapee/Documents/GitHub/KaSim/python")
import kappa_std
import kappa_common


class SimulationStatus():
    NotStart = 1
    Paused = 2
    Running = 3


class KaSimKappaSim():
    simulator_status = SimulationStatus.NotStart

    __debug_flag = False
    __runtime = None
    __progress_time = 0
    __url = "/Users/tr.sakrapee/Documents/GitHub/KaSim/bin/KaSimAgent"
    #__url = "../KaSim/_build/term/agent.byte"
    __plot_period = 0.1
    __seed = None
    __simulation_id = None

    __temp_files = "temp.ka"

    def __init__(self, url=None, debug_flag=False):
        self.set_debug_mode(debug_flag)
        self.simulator_status = SimulationStatus.NotStart
        self.__simulation_id = str(uuid.uuid1())

        self.__temp_files = "{0}.ka".format(self.__simulation_id)   # re-define a name of the temp file
        # if no url, use a default value
        if url is not None:
            self.__url = url
            self._debug("use the default url: {0}".format(url))

        self.__runtime = kappa_std.KappaStd(self.__url)
        self._debug("created a KaSim runtime with a url: {0} ".format(self.__url))

    # set the flag to enable/disable the debug mode
    # Params:   bool param
    def set_debug_mode(self, param):
        # when param is not bool type
        if type(param) is not bool:
            return
        self.__debug_flag = param

    # print a log via the terminal
    # Params:   string str
    def _debug(self, str):
        if self.__debug_flag:
            print "Debug: {0}".format(str)

    # load Kasim file
    # Params:   string input_file
    def load_file(self, input_file):
        # when the input file is null
        if input_file is None:
            return

        # when runtime could not be initiated
        if self.__runtime is None:
            return

        with open(input_file) as f:
            code = f.read()
            file_content = str(code)
            file_metadata = kappa_common.FileMetadata(input_file, 0)

            self._debug("file : {0}".format(file_metadata.toJSON()))

            file_object = kappa_common.File(file_metadata, file_content)
            self.__runtime.file_create(file_object)
            self.__runtime.project_parse()

    # return the current progression time of the simulator
    def get_time(self):
        return self.__progress_time

    # simulate the model from the current to a particular time
    # Params:   integer time
    def run_until_time(self, time):
        if time <= 0:
            return
        if time <= self.__progress_time:
            return

        self._run(time)

    # simulate the model with a specific time
    # Params:   integer time
    def run_for_time(self, time):
        if time <= 0:
            return

        expected_time = self.__progress_time + time

        self._run(expected_time)

    # run the simulator with a particular time
    # Params:   integer time
    def _run(self, pause_time):
        pause_condition = "[T] > {0}".format(str(pause_time))
        simulation_parameter = kappa_common.SimulationParameter(self.__plot_period,
                                                                self.__simulation_id,
                                                                pause_condition,
                                                                self.__seed)

        # if simulator is not started yet
        if self.simulator_status is SimulationStatus.NotStart:
            code = ""
            try:
                with open(self.__temp_files) as f:
                    code = f.read()
            except Exception:
                self._debug("")

            if code is not "":
                file_content = str(code)
                file_metadata = kappa_common.FileMetadata(self.__temp_files, 0)

                self._debug("file : {0}".format(file_metadata.toJSON()))

                file_object = kappa_common.File(file_metadata, file_content)
                self.__runtime.file_create(file_object)
                self.__runtime.project_parse()

            self.__runtime.simulation_start(simulation_parameter)
            self._debug("")
        # if simulator has been paused then start it again
        elif self.simulator_status is SimulationStatus.Paused:
            self.__runtime.simulation_continue(simulation_parameter)
            self._debug("")

        self.simulator_status = SimulationStatus.Running
        simulation_info = self.__runtime.simulation_info()

        while simulation_info["simulation_info_progress"]["simulation_progress_is_running"]:
            time.sleep(1)

            percentage = ""
            time_percentage = simulation_info["simulation_info_progress"]["simulation_progress_time_percentage"]
            event_percentage = simulation_info["simulation_info_progress"]["simulation_progress_event_percentage"]

            if time_percentage or time_percentage == 0:
                percentage = time_percentage
            if event_percentage or event_percentage == 0:
                percentage = event_percentage

            sys.stdout.write("..{0}.. ".format(percentage))
            sys.stdout.flush()
            simulation_info = self.__runtime.simulation_info()

        self.simulator_status = SimulationStatus.Paused

        simulation_progress_time = simulation_info["simulation_info_progress"]["simulation_progress_time"]
        self.__progress_time = round(simulation_progress_time, 2)

        print("progression time: {0}".format(self.__progress_time))


    def _set_perturbation(self, str):
        self.__runtime.simulation_perturbation(str)
        sim_info = self.__runtime.simulation_info()
        sim_info_line = self.__runtime.simulation_info_file_line()
        return

    # update a variable in the simulation
    # Params:   string var_name
    #           string var_value
    def update_variable_value(self, var_name, var_value):
        input_str = "$UPDATE \"{0}\" {1}".format(var_name, var_value)

        self._debug(input_str)
        self._set_perturbation(input_str)

    # get a variable value in the simulation
    # Params: string var_name
    def _get_observable_value_by_time(self, time_sec=None):
        if time_sec is None:
            plot_data = self.__runtime.simulation_detail_plot()
            plot_legend = plot_data['plot_detail_plot']['plot_legend']
            plot_time_series = plot_data['plot_detail_plot']['plot_time_series']
            return plot_legend, plot_time_series

        plot_limit_offset = time_sec * 10
        plot_limit_points = 1

        limit = kappa_common.PlotLimit(plot_limit_offset, plot_limit_points)

        plot_data = self.__runtime.simulation_detail_plot(kappa_common.PlotParameter(limit))
        plot_legend = plot_data['plot_detail_plot']['plot_legend']
        plot_time_series = plot_data['plot_detail_plot']['plot_time_series']
        return plot_legend, plot_time_series

    # get observable values by a specific time in second
    # Params:   integer time_sec
    # Return:   type <tuple of numpy_array>
    def get_all_values_by_time(self, time_sec=None):
        plot_data = self._get_observable_value_by_time(time_sec)

        if plot_data is None:
            self._debug("get_all_values_by_time: there is no data")
            return None

        np_plot_time_series = None
        np_plot_legend = None
        try:
            np_plot_legend = np.asarray(plot_data[0])
            np_plot_time_series = np.asarray(plot_data[1])
        except Exception as err:
            self._debug("get_all_values_by_time: catched an exception {0}".format(err.message))

        return np_plot_legend, np_plot_time_series

    # get a particular variable value by its name and a specific time
    # Params:   integer time_sec
    #           integer var_name
    # Return:   type numpy_array
    def get_value_by_time(self, time_sec, var_name):
        plot_data = self.get_all_values_by_time(time_sec)

        if plot_data is None:
            self._debug("get_value_by_time: there is no data")
            return None

        plot_legend = plot_data[0]
        plot_time_series = plot_data[1]

        if not (var_name in plot_legend):
            return plot_legend, plot_time_series

        time_index = np.where('[T]' == plot_legend)
        var_index = np.where(var_name == plot_legend)
        plot_legend = np.append(plot_legend[time_index[0][0]], plot_legend[var_index[0][0]])
        plot_time_series = plot_time_series[:, [time_index[0][0], var_index[0][0]]]
        return plot_legend, plot_time_series

    # adding agents during a simulation
    # Params:   string var_name
    #           string var_value
    def add_agent_value(self, var_name, var_value):
        input_str = '$ADD {0} {1}'.format(var_value, var_name)

        self._debug(input_str)
        self._set_perturbation(input_str)

    # deleting agents during a simulation
    # Params:   string var_name
    #           string var_value
    def delete_agent_value(self, var_name, var_value):
        input_str = '$DELETE {0} {1}'.format(var_value, var_name)

        self._debug(input_str)
        self._set_perturbation(input_str)

    #def get_transition(self):

    # add a transition equation before the simulation start
    # Params:   string trans_name
    #           string trans_exp
    #           string trans_rate
    def add_transition(self, trans_name, trans_exp, trans_rate):
        if self.simulator_status is not SimulationStatus.NotStart:
            return

        input_str = "\'{0}\' {1} @ \'{2}\'".format(trans_name, trans_exp, trans_rate)

        self._debug("Add a transition: {0}".format(input_str))
        self._write_file_line(input_str)
        return

    # add a map between a variable and its expression before the simulation start
    # Params:   string var_name
    #           string var_exp
    def add_variable_map(self, var_name, var_exp):
        if self.simulator_status is not SimulationStatus.NotStart:
            return

        input_str = "%var: {0} {1}".format(var_name, var_exp)

        self._debug("Add a variable map: {0}".format(input_str))
        self._write_file_line(input_str)
        return

    # for writing the temp file with an input string
    # Params:   string str
    def _write_file_line(self, str):
        try:
            file = open(self.__temp_files, "a")
        except IOError:
            file = open(self.__temp_files, "w")

        file.write(str+ "\n")
        file.close()
        return

    # for clean up a temp file
    def __del__(self):
        self._debug("Deconstruct the object")
        try:
            self._debug("remove the file: {0}".format(self.__temp_files))
            os.remove(self.__temp_files)
        except OSError:
            self._debug("there is no the file name: {0}".format(self.__temp_files))

        self._debug("delete the simulator")
        self.__runtime.simulation_delete()
        return


def main():
    kasim = KaSimKappaSim(None, True)
    kasim.load_file("simpleBinding.ka")

    kasim.run_until_time(1)
    print kasim.get_all_values_by_time()
    print kasim.get_value_by_time(1, 'Monomer_A')

    kasim.run_for_time(1)

if __name__ == "__main__":
    main()

