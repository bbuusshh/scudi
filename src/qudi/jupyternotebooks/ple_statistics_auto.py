#%%
#import the necessary packages
import automatization
from automatization.ple_statistics import PleAuto
import pandas as pd
import os
import time
import json
from importlib import reload
import numpy as np
from automatization.ple_statistics import PleAuto
from matplotlib import pyplot as plt
reload(automatization.ple_statistics)
from automatization.ple_statistics import PleAuto
from scipy.constants import speed_of_light
import pickle
from pathlib import Path

import sys

sys.setrecursionlimit(10000)

pa = PleAuto(
    ple_gui, 
    ple_optimize_logic, 
    laser_scanner_logic,
    poi_manager_logic, 
    scanning_optimize_logic,
    spectrometer, 
    spectrometerlogic,
    cobolt,
    ibeam_smart
)

def ple_is_here(res, center_sigma = 3e3, amplitude = 1000, sigma_stderr_ratio = 4, amplitude_stderr_ratio=3):
    """Check if the ple is still there."""
    it_is = True
    if res["center"].stderr is None or res["sigma"].stderr is None or res["sigma"].value is None:
        return False
    if ( res["center"].stderr > center_sigma or 
    res["sigma"].stderr * sigma_stderr_ratio > res["sigma"].value or 
    res["amplitude"].stderr * amplitude_stderr_ratio > res["amplitude"].value or
    res["amplitude"].value < amplitude): 
        #ple is gone.
        return False

    return it_is
def adjust_eta(pa, poi_name, folder_defect, results_poi, center_v):
    eta_volts = [center_v, center_v + 0.3, center_v - 0.3]#, center_v + 0.6, center_v - 0.6]
    sigma_errs = []
    for eta_v in eta_volts:
        laser_controller_remote.etalon_voltage = eta_v
        time.sleep(0.5)
        res = pa.do_ple_scan(lines = 1)
        time.sleep(1)
        if res["center"] < 5000 or res["center"] > 22000:
            sigma_errs.append(1e15)
        else:
            sigma_errs.append(res["sigma"].stderr/res["sigma"].value if res["sigma"].stderr is not None else 1e15)
    results_poi["eta_voltage"] = eta_volts[sigma_errs.index(min(sigma_errs))]
    laser_controller_remote.etalon_voltage = eta_volts[sigma_errs.index(min(sigma_errs))]
    res = pa.do_ple_scan(lines = 1)
    pa.save_ple(tag = "full_range_eta_adjusted",
                poi_name=poi_name, folder_name=folder_defect)
    return res, results_poi
def ple_refocus(pa, opt_times = 1, 
                scan_frequency=200, 
                scan_resolution=500,
                scan_range = 5000):
    
    seqs = {str(seq): idx for idx, seq in enumerate(ple_gui._osd.settings_widget.available_opt_sequences)}
    ple_gui._osd.settings_widget.optimize_sequence_combobox.setCurrentIndex(seqs["a"])
    ple_gui._osd.change_settings({'scan_frequency': {"a": scan_frequency},
                                    "scan_resolution": {"a":scan_resolution},
                                    "scan_range": {"a": scan_range}}) #GHz

    ple_gui._osd.accept()
    time.sleep(0.8)
    pa.optimize_ple()
    return res
def settings_confocal_refocus_fine():
    seqs = {str(seq): idx for idx, seq in enumerate(scanner_gui._osd.settings_widget.available_opt_sequences)}
    scanner_gui._osd.settings_widget.optimize_sequence_combobox.setCurrentIndex(seqs["xy, z"])
    scanner_gui._osd.change_settings({'scan_frequency': {"x": 25, "y": 25, "z": 25},
                                    "scan_resolution": {"x": 25, "y": 25, "z":80},
                                    "scan_range": {"x": 1e-6, "y": 1e-6, "z": 4e-6}})

    scanner_gui._osd.accept()
    time.sleep(0.5)


def settings_confocal_refocus_coarse():
    seqs = {str(seq): idx for idx, seq in enumerate(scanner_gui._osd.settings_widget.available_opt_sequences)}
    scanner_gui._osd.settings_widget.optimize_sequence_combobox.setCurrentIndex(seqs["x, y, z"])

    scanner_gui._osd.change_settings({'scan_frequency': {"x": 5, "y": 5, "z": 5},
                                    "scan_resolution": {"x": 80, "y": 80, "z":80},
                                    "scan_range": {"x": 2.5e-6, "y": 2.5e-6, "z": 4.5e-6}})
    scanner_gui._osd.accept()
    time.sleep(0.5)

def confocal_refocus(opt_times=2):
    for i in range(opt_times):
        scanning_optimize_logic.start_optimize()
        while scanning_optimize_logic.module_state()=='locked':
            time.sleep(1)
    time.sleep(1)
#find the defect:
def find_the_defect(pa, poi_name, folder_defect):
    switchlogic.set_state("ScanningMode", 'Wavemeter')
    pa.set_resonant_power(power = 300)
    cobolt.enable_modulated()
    cobolt.set_laser_modulated_power(2)
    time.sleep(1)
    settings_confocal_refocus_coarse()
    confocal_refocus(opt_times=2)

    
    switchlogic.set_state("ScanningMode", 'NI')
    time.sleep(0.5)
    #Check how the PLE look like
    res = pa.do_ple_scan(lines = 1)

    #configure slow scanning for the wavemeter scanning optimizations
    for kk in range(3):
        if not ple_is_here(res, amplitude = 3000):
            switchlogic.set_state("ScanningMode", 'Wavemeter')
            time.sleep(0.5)
            settings_confocal_refocus_coarse()
            confocal_refocus(opt_times=1)
            #Check how the PLE look like
            time.sleep(0.5)
            switchlogic.set_state("ScanningMode", 'NI')
            res = pa.do_ple_scan(lines = 1)
            time.sleep(0.5)
            pa.save_ple(tag = "full_range_iter_{kk}",
                    poi_name=poi_name, folder_name=folder_defect)
            time.sleep(0.5)
        else:
            break

    pa.save_ple(tag = "full_range",
            poi_name=poi_name, 
            folder_name=folder_defect)
    time.sleep(1)
    return res

def take_spectrum(pa, poi_name, folder_defect, results_poi):
    # take spectrum to estimate SOC
    pa.set_resonant_power(power = 0)
    time.sleep(2)
    ibeam_smart.enable()
    cobolt.enable_modulated()
    cobolt.set_laser_modulated_power(power = 100)
    pa.set_resonant_power(power = 0)
    time.sleep(1)
    pa.take_spectrum()

    pa.save_spectrum(name_tag=f"{poi_name}_blueNgreen", folder_path=folder_defect)
    results_poi["spectrum_data"] = spectrometerlogic.last_saved_path

    spectrometer._mw.data_widget.fit_widget.sigDoFit.emit("DoubleLorentzian")
    time.sleep(0.2)
    # spectrometer.fit_results.params["center_1"].value
    if spectrometer.fit_results is not None:
        params = spectrometer.fit_results.params
        results_poi["SOC, GHz"] = float(speed_of_light / params["center_2"].value - speed_of_light / params["center_1"].value)

    ibeam_smart.disable()
    #cobolt.disable_modulated()
    cobolt.enable_modulated()
    cobolt.set_laser_modulated_power(power = 5)

    return results_poi
# Perform the saturation measurement

def fine_optimize(pa, poi_name, folder_defect, results_poi):
    res = pa.do_ple_scan(lines = 1)
    pa.go_to_ple_target(res["center"].value)
    ple_refocus(pa, scan_range=4000, scan_frequency=100)
    settings_confocal_refocus_fine()
    confocal_refocus(opt_times=1)
    ple_refocus(pa, scan_range=4000, scan_frequency=100)
    confocal_refocus(opt_times=1)
    res = pa.do_ple_scan(lines = 1)
    pa.go_to_ple_target(res["center"].value)
    results_poi["center"] = res["center"].value
    
    results_poi["center_λ"] = high_finesse_wavemeter_remote.get_current_wavelength()
    pa.save_ple(tag = "full_range_optimized",
            poi_name=poi_name, 
            folder_name=folder_defect)
    return res, results_poi

def run_saturation_measurement(pa, res, poi_name, folder_defect, results_poi):
    os.mkdir(saturation_folder := os.path.join(folder_defect, "saturation"))
    results_poi["saturation"] = {}
    idx_no_ple = None
    res_old = res
    power_steps = 3 * np.logspace(1.5, 2, 10, endpoint=True).astype(int)[::-1]
    low_power_steps = np.array([85, 78, 70, 65, 60])
    power_steps = np.append(power_steps,low_power_steps)

    for idx, power in enumerate(power_steps):
        os.mkdir(power_folder := os.path.join(saturation_folder, f"{power}"))
        
        if power > 90: 
            cobolt.enable_modulated()
            pa.set_resonant_power(power = power)
            time.sleep(1)
            #align twice
            # for i in range(2):
            if abs(res_old["center"].value - res["center"].value) > res_old["sigma"].value*2:
                res = res_old
            
            fine_range = (
                res["center"].value - res["sigma"].value*6,
                res["center"].value + res["sigma"].value*6
            )
            if res["center"].value is None or res["sigma"].value is None:
                continue
            res = pa.do_ple_scan(lines = 1, in_range=fine_range)
            if abs(res_old["center"].value - res["center"].value) > res_old["sigma"].value*2:
                res = res_old
            else:
                res_old = res
            pa.save_ple(tag = f"{power}",
                poi_name=poi_name, folder_name=power_folder)

            results_poi.update({"saturation": 
                            {f"{power}_repump":
                                {"scan_data": ple_data_logic.last_saved_files_paths,
                                "sigma": res["sigma"].value,
                                "sigma_stderr": res["sigma"].stderr,
                                "center": res["center"].value
                                }
                                }})
        if (power < 150):
            os.mkdir(power_folder_norepump := os.path.join(power_folder, f"no_repump"))
            # check with initioalization
            cobolt.disable_modulated()
            pa.one_pulse_repump("violet")
            res_ = pa.do_ple_scan(lines = 1, in_range=fine_range)
            if not ple_is_here(res_, amplitude=800):
                continue
            res_ = pa.do_ple_scan(lines = 5, in_range=fine_range)

            pa.save_ple(tag = f"{power}_norepump",
                poi_name=poi_name, folder_name=power_folder_norepump)
            results_poi.update({"saturation": 
                            {f"{power}_norepump":
                                {"scan_data": ple_data_logic.last_saved_files_paths,
                                "sigma": res_["sigma"].value,
                                "sigma_stderr": res_["sigma"].stderr,
                                "center": res_["center"].value
                                }
                                }})
        if power <= 40:
            break

            #save_plots
    return results_poi
# constraints
scan_range_constr = laser_scanner_logic.scanner_constraints.axes["a"].value_range
scanning_optimize_logic._backwards_line_resolution = 20


#%%
poi_name = "def3"
folder = r"C:\Users\yy3\Documents\data\Vlad\26-03-2023\158\#1_D\ROI3\auto"
folder = os.path.join(folder, r"attempt_2")
if not os.path.exists(folder):
    os.mkdir(folder) 
high_finesse_wavemeter_remote.start_acquisition()
# run throught the defects:
results_poi = {}
os.mkdir(folder_defect := os.path.join(folder, poi_name))
#

# %%
res = find_the_defect(pa, poi_name, folder_defect)
#%%
res, results_poi = adjust_eta(pa, poi_name, folder_defect, results_poi, center_v=-7)
#%%
res, results_poi = fine_optimize(pa, poi_name, folder_defect, results_poi)
# %%
results_poi = run_saturation_measurement(pa, res, poi_name, folder_defect, results_poi)
#%%
results_poi = take_spectrum(pa, poi_name, folder_defect, results_poi)
# %%
res = pa.do_ple_scan(lines = 1)
# %%
#cobolt.enable_modulated()
# %%

#NOW all together:

folder = r"C:\Users\yy3\Documents\data\Vlad\5-04-2023_90NA_4_5K\158\#1A\auto"
folder = os.path.join(folder, r"auto_spectras2")
center_v = -7
if not os.path.exists(folder):
    os.mkdir(folder) 
high_finesse_wavemeter_remote.start_acquisition()
# run throught the defects:

for poi_name in poi_manager_logic.poi_names:
    if poi_name == "ref":
        continue
    results_poi = {}
    os.mkdir(folder_defect := os.path.join(folder, poi_name))
    #Go to the defect:
    pa.go_to_poi(poi_name, opt_times=1, ref_poi=None) 
    #
    print("Find the defect ", poi_name)
    res = find_the_defect(pa, poi_name, folder_defect)
    fine_range = (
            res["center"].value - res["sigma"].value*6,
            res["center"].value + res["sigma"].value*6
        )
    pa.set_resonant_power(power = 200)
    time.sleep(1)
    res = pa.do_ple_scan(lines = 4, in_range=fine_range)
    
    pa.save_ple(tag = f"200power",
        poi_name=poi_name, folder_name=folder_defect)
    # print("Adjusting the eta")
    # res, results_poi = adjust_eta(pa, poi_name, folder_defect, results_poi, center_v)
    # if not ple_is_here(res):
    #     # return the center eta
    #     laser_controller_remote.etalon_voltage = center_v
    #     continue
    # print("Fine optimization of the ple and confocal")
    # res, results_poi = fine_optimize(pa, poi_name, folder_defect, results_poi)
    # print("Run the saturation measurements")
    # results_poi = run_saturation_measurement(pa, res, poi_name, folder_defect, results_poi)
    print("Run spectrum")
    results_poi = take_spectrum(pa, poi_name, folder_defect, results_poi)
    with open(os.path.join(folder_defect, f'results_{poi_name}'), 'wb') as handle:
        pickle.dump(results_poi, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
# %%
