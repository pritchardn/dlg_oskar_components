"""
dlg_oskar_components appComponent module.

This is the module of dlg_oskar_components containing DALiuGE application components.
Here you put your main application classes and objects.

Typically a component project will contain multiple components and will
then result in a single EAGLE palette.

Be creative! do whatever you need to do!
"""
import logging
import io
import numpy as np
import oskar
import matplotlib.pyplot as plt

from dlg.drop import BarrierAppDROP, BranchAppDrop
from dlg.meta import (
    dlg_batch_input,
    dlg_batch_output,
    dlg_bool_param,
    dlg_float_param,
    dlg_int_param,
    dlg_component,
    dlg_streaming_input,
    dlg_string_param,
)
from dlg.droputils import load_npy

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
# @param[in] aparam/channel_bandwidth_hz Channel bandwith/0/Double/readwrite/
#     \~English The channel width, in Hz, used to simulate bandwidth smearing.
#     (Note that this can be different to the frequency increment if channels do not cover
#     a contiguous frequency range.)
# @param[in] aparam/time_average_sec Time average/0/Double/readwrite/
#     \~English The correlator time-average duration, in seconds,
#     used to simulate time averaging smearing.
# @param[in] aparam/force_polarised_ms Force polarisation/false/Boolean/readwrite/
#     \~English If True, always write the Measurment Set in polarised format even if the simulation
#     was run in the single polarisation ‘Scalar’ (or Stokes-I) mode.
#     If False, the size of the polarisation dimension in the the
#     Measurement Set will be determined by the simulation mode.
# @param[in] aparam/ignore_w_components Ignore w components/false/Boolean/readwrite/
#     \~English If enabled, baseline W-coordinate component values will be set to 0.
#     This will disable W-smearing. Use only if you know what you’re doing!
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
        "OSKARInterferometer",
        "OSKAR Interferometer",
        [dlg_batch_input("binary/*", [])],
        [dlg_batch_output("binary/*", [])],
        [dlg_streaming_input("binary/*")],
    )

    doubleprecision = dlg_bool_param("doubleprecision", True)
    usegpu = dlg_bool_param("usegpu", False)
    channel_bandwidth_hz = dlg_float_param("channel_bandwidth_hz", 0.0)
    time_average_sec = dlg_float_param("time_average_sec", 0.0)
    force_polarised_ms = dlg_bool_param("force_polarised_ms", False)
    ignore_w_components = dlg_bool_param("ignore_w_components", False)

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
                "channel_bandwidth_hz": self.channel_bandwidth_hz,
                "time_average_sec": self.time_average_sec,
                "force_polarised_ms": self.force_polarised_ms,
                "ignore_w_components": self.ignore_w_components
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

##
# @brief OSKARImager
# @details A wrapper around the OSKAR imaging simulator
#
# @par EAGLE_START
# @param category PythonApp
# @param[in] cparam/appclass Application Class/dlg_oskar_components.OSKARImager/String/readonly/
#     \~English Import direction for application class
# @param[in] cparam/execution_time Execution Time/5/Float/readonly/False//False/
#     \~English Estimated execution time
# @param[in] cparam/num_cpus No. of CPUs/1/Integer/readonly/False//False/
#     \~English Number of cores used
# @param[in] aparam/doubleprecision Double Precision/true/Boolean/readwrite/
#     \~English Whether to use double (true) or float (false) precision.
# @param[in] aparam/usegpu Use GPU/false/Boolean/readwrite/
#     \~English Whether to use gpu capabilities (true) or CPU only (false).
# @param[in] aparam/specify_cellsize Specify Cellsize/false/Boolean/readwrite/
#     \~English If set, specify cellsize; otherwise, specify field of view
# @param[in] aparam/fov_deg FOV degrees/2/Double/readwrite/
#     \~English Total field of view in degrees
# @param[in] aparam/cellsize_arcsec Cellsize Arcsec/1/Double/readwrite/
#     \~English The cell (pixel) size in arcseconds
# @param[in] aparam/size Size/256/Integer/readwrite/
#     \~English Image width in one dimension (e.g. a value of 256 would give a 256 by 256 image).
#     This must be even.
# @param[in] aparam/image_type Image type/I/String/readwrite/
#     \~English Type of image to form. Should be one of the following:
#     Linear, XX, XY, YX, YY, Stokes, I, Q, U, V, PSF
# @param[in] aparam/channel_snapshots Channel Snapshots/false/Boolean/readwrite/
#     \~English If true, then produce an image cube containing snapshots for each frequency channel.
#     If false, then use frequency-synthesis to stack the channels in the final image.
# @param[in] aparam/freq_min_hz Freq Min Hz/0/Double/readwrite/
#     \~English The minimum visibility channel centre frequency
#     to include in the image or image cube, in Hz.
# @param[in] aparam/freq_max_hz Freq Max Hz/max/String/readwrite/
#     \~English The maximum visibility channel centre frequency
#     to include in the image or image cube, in Hz. Allowed >= 0, ‘min’ or ‘max'
# @param[in] aparam/time_min_utc Time Min UTC/0/String/readwrite/
#     \~English The minimum visibility time centroid to include in the image.
#     This can be either a MJD value or a string
# @param[in] aparam/time_max_utcz Time Max UTC/0/String/readwrite/
#     \~English The maximum visibility time centroid to include in the image.
#     This can be either a MJD value or a string
# @param[in] aparam/uv_filter_min UV Filter Min/0/Double/readwrite/
#     \~English The minimum UV baseline length to image, in wavelengths.
#     Allowed to be >=0, ‘min’ or ‘max'
# @param[in] aparam/uv_filter_max UV Filter Max/max/String  /readwrite/
#     \~English The maximum UV baseline length to image, in wavelengths.
#     Allowed to be >=0, ‘min’ or ‘max'
# @param[in] aparam/algorithm Algorithm/FFT/String/readwrite/
#     \~English The type of transform used to generate the image.
#     Allowed to be one of: FFT, DFT 2D, DFT 3D, W-Projection
# @param[in] aparam/weighting Weighting/Natural/String/readwrite/
#     \~English The type of visibility weighting scheme to use.
#     Allowed to be one of ‘Natural’ ‘Radial’ or ‘Uniform'
# @param[in] aparam/u_wavelengths U Wavelengths/0/Double/readwrite/
#     \~English The scale of tapering in U to apply to the weights, in wavelengths.
#     If nonzero, weights will be multiplied by a factor
#     exp(log(0.3) * [(u / scale_u)^2 + (v / scale_v)^2]).
# @param[in] aparam/v_wavelengths V Wavelengths/0/Double/readwrite/
#     \~English The scale of tapering in V to apply to the weights, in wavelengths.
#     If nonzero, weights will be multiplied by a factor
#     exp(log(0.3) * [(u / scale_u)^2 + (v / scale_v)^2]).
# @param[in] port/visibilities Input Visibility Data/Complex/
#     \~English Input visibilities.
# @param[out] port/image_png Image Png/File/
#     \~English Output Image saved as a figure
# @par EAGLE_END
class OSKARImager(BarrierAppDROP):
    """Configures and runs an OSKAR imager simulation
    """
    compontent_meta = dlg_component(
        "OSKARImager",
        "OSKAR Imager",
        [dlg_batch_input("binary/*", [])],
        [dlg_batch_output("binary/*", [])],
        [dlg_streaming_input("binary/*")],
    )

    doubleprecision = dlg_bool_param("doubleprecision", True)
    usegpu = dlg_bool_param("usegpu", False)
    specify_cellsize = dlg_bool_param("specify_cellsize", False)
    fov_deg = dlg_float_param("fov_deg", 2.0)
    cellsize_arcsec = dlg_float_param("cellsize_arcsec", 1.0)
    size = dlg_int_param("size", 256)
    image_type = dlg_string_param("image_type", "I")
    channel_snapshots = dlg_bool_param("channel_snapshots", False)
    freq_min_hz = dlg_float_param("freq_min_hz", 0.0)
    freq_max_hz = dlg_string_param("freq_max_hz", "max")
    time_min_utc = dlg_string_param("time_min_utc", "0")
    time_max_utc = dlg_string_param("time_max_utc", "0")
    uv_filter_min = dlg_float_param("uv_filter_min", 0.0)
    uv_filter_max = dlg_string_param("uv_filter_max", "max")
    algorithm = dlg_string_param("algorithm", "FFT")
    weighting = dlg_string_param("weighting", "Natural")
    u_wavelengths = dlg_float_param("u_wavelengths", 0.0)
    v_wavelengths = dlg_float_param("v_wavelengths", 0.0)

    def initialize(self, **kwargs):
        super(OSKARImager, self).initialize(**kwargs)

    def run(self):
        """
        The run method is mandatory for DALiuGE application components.
        """
        import os.path
        params = {
            "image": {
                "double_precision": 'true' if self.doubleprecision else 'false',
                "use_gpus": 'true' if self.usegpu else 'false',
                "specify_cellsize": self.specify_cellsize,
                "fov_deg": self.fov_deg,
                "cellsize_arcsec": self.cellsize_arcsec,
                "size": self.size,
                "image_type": self.image_type,
                "channel_snapshots": self.channel_snapshots,
                "freq_min_hz": self.freq_min_hz,
                "freq_max_hz": self.freq_max_hz,
                "time_min_utc": self.time_min_utc,
                "time_max_utc": self.time_max_utc,
                "uv_filter_min": self.uv_filter_min,
                "uv_filter_max": self.uv_filter_max,
                "algorithm": self.algorithm,
                "weighting": self.weighting,
                #"u_wavelengths": self.u_wavelengths,
                #"v_wavelengths": self.v_wavelengths,
                "input_vis_data": self.inputs[0].path
            }
        }

        settings = oskar.SettingsTree("oskar_imager")
        settings.from_dict(params)
        imager = oskar.Imager(settings=settings)
        image = imager.run(return_images=1)["images"][0]

        im = plt.imshow(image, cmap="jet")
        plt.gca().invert_yaxis()
        plt.colorbar(im)

        out_io = io.BytesIO()
        plt.savefig(out_io)
        out_io.seek(0)
        self.outputs[0].write(out_io.getbuffer())
