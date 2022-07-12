"""
dlg_oskar_components appComponent module.

This is the module of dlg_oskar_components containing DALiuGE application components.
Here you put your main application classes and objects.

Typically a component project will contain multiple components and will
then result in a single EAGLE palette.

Be creative! do whatever you need to do!
"""
import logging
import pickle
import numpy
import oskar

from dlg.drop import BarrierAppDROP, BranchAppDrop
from dlg.meta import (
    dlg_batch_input,
    dlg_batch_output,
    dlg_bool_param,
    dlg_component,
    dlg_streaming_input,
    dlg_string_param,
)
from dlg.droputils import replace_path_placeholders, load_npy

logger = logging.getLogger(__name__)

##
# @brief OSKARInterferometer
# @details A wrapper around the OSKAR interferometer simulator
#
# @par EAGLE_START
# @param category PythonApp
# @param[in] cparam/appclass Application Class/dlg_oskar_components.OSKARInterferometer/String/readonly/
#     \~English Import direction for application class
# @param[in] cparam/execution_time Execution Time/5/Float/readonly/False//False/
#     \~English Estimated execution time
# @param[in] cparam/num_cpus No. of CPUs/1/Integer/readonly/False//False/
#     \~English Number of cores used
# @param[in] aparam/doubleprecision Double Precision/true/Boolean/readwrite/
#     \~English Whether to use double (true) or float (false) precision.
# @param[in] aparam/usegpu Use GPU/false/Boolean/readwrite/
#     \~English Whether to use gpu capabilities (true) or CPU only (false).
# @param[in] port/settings Settings Tree String/Json/
#     \~English String representation of OSKAR settings tree
# @param[in] port/skymodel Sky Model/String/
#     \~English Pickled numpy array of sky data
# @param[in] port/telescopemodel Telescope Model/String/
#     \~English Location of telescope model data
# @param[out] port/visibilities Visibilities/Complex/
#     \~English Output Visibilities
# @par EAGLE_END
class OSKARInterferometer(BarrierAppDROP):
    """Configures and runs an OSKAR interferometer simulation
    """

    compontent_meta = dlg_component(
        "MyApp",
        "My Application",
        [dlg_batch_input("binary/*", [])],
        [dlg_batch_output("binary/*", [])],
        [dlg_streaming_input("binary/*")],
    )

    doubleprecision = dlg_bool_param("doubleprecision", True)
    usegpu = dlg_bool_param("usegpu", False)

    def initialize(self, **kwargs):
        super(OSKARInterferometer, self).initialize(**kwargs)

    def run(self):
        """
        The run method is mandatory for DALiuGE application components.
        """
        if len(self.outputs) < 1:
            raise Exception("No where for the visibilities to go")
        if len(self.inputs) < 3:
            raise Exception("Make sure to connect a skymodel and telescope model")
        # Basic settings. (Note that the sky model is set up later.)
        params = {
            "simulator": {
                "use_gpus": self.usegpu
            },
            "observation": {
                "num_channels": 3,
                "start_frequency_hz": 100e6,
                "frequency_inc_hz": 20e6,
                "phase_centre_ra_deg": 20,
                "phase_centre_dec_deg": -30,
                "num_time_steps": 24,
                "start_time_utc": "01-01-2000 12:00:00.000",
                "length": "12:00:00.000"
            },
            "telescope": {
                "input_directory": self.inputs[0].path  # TODO: support named ports
            },
            "interferometer": {
                "oskar_vis_filename": self.outputs[0].path,
                "ms_filename": "",
                "channel_bandwidth_hz": 1e6,
                "time_average_sec": 10
            }
        }
        settings = oskar.SettingsTree("oskar_sim_interferometer")
        settings.from_dict(params)

        # Set the numerical precision to use.
        settings["simulator/double_precision"] = self.doubleprecision

        # Create a sky model containing three sources from a numpy array.
        sky_data = load_npy(self.inputs[1])
        """  # Below kept for example
        sky_data = numpy.array([
            [20.0, -30.0, 1, 0, 0, 0, 100.0e6, -0.7, 0.0, 0, 0, 0],
            [20.0, -30.5, 3, 2, 2, 0, 100.0e6, -0.7, 0.0, 600, 50, 45],
            [20.5, -30.5, 3, 0, 0, 2, 100.0e6, -0.7, 0.0, 700, 10, -10]])
        """
        if self.doubleprecision:
            temp_precision = "double"
        else:
            temp_precision = "single"
        sky = oskar.Sky.from_array(sky_data, temp_precision)  # Pass precision here.

        # Set the sky model and run the simulation.
        sim = oskar.Interferometer(settings=settings)
        sim.set_sky_model(sky)
        sim.run()
