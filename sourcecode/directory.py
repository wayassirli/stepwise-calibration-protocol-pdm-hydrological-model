# -*- coding: utf-8 -*-
"""Create output folder and stores their path for the result of catchment calibration and evaluation

Created on Thu Aug 13 14:03:34 2026
@author: Way
"""

import os

# Project's main directory
sourcecode_path = os.path.dirname(__file__)     # directory of directory.py   = .../sourcecode
project_path = os.path.dirname(sourcecode_path) # directory of .../sourcecode = .../calibration.py

def generate_evaluation_plot_folder(catchment):
    """Create a folder and subfolders containing evaluation plots for each catchment.

    Parameters
    ----------
    catchment : str
        Name of the catchment, used as the output folder name

    Returns
    -------
    catchment_evaluation_path : str
        Path to the catchment evaluation folder
    """
    
    catchment_evaluation_plot_path = os.path.join(
        project_path, 'evaluation', 'plot', catchment
    )
    
    subfolders = [
        "recession/baseflow",
        "recession/quickflow",
        "ET",
        "soil/boxcox",
        "soil/timeseries",
        "soil/evaluation",
        "runoff/boxcox",
        "runoff/timeseries",
        "runoff/evaluation",
        "statistics/baseflow",
        "statistics/quickflow",
        "statistics/totalflow",
        "waterbalance/baseflow",
        "waterbalance/quickflow",
        "waterbalance/totalflow"
    ]
    
    for subfolder in subfolders:                       
        os.makedirs(                                                 # make directory
            os.path.join(catchment_evaluation_plot_path, subfolder), # generate path of the subfolder e.g. .../Minderhout/soil/boxcox
            exist_ok=True                                            # if the generated path exist, skip silently without rising errors. if it does not exist yet, makedirs
        )                                              
    
    return catchment_evaluation_plot_path

def generate_observation_plot_folder(catchment):
    """Create a folder containing different observation plots for each catchment.

    Parameters
    ----------
    catchment : str
        Name of the catchment, used as the output folder name

    Returns
    -------
    catchment_observation_plot_path : str
        Path to the catchment observation plot folder
    """

    catchment_observation_plot_path = os.path.join(
        project_path, 'observation', 'plot', catchment
    )
    
    os.makedirs(catchment_observation_plot_path, exist_ok=True)
    
    return catchment_observation_plot_path

class Directory:
    """Container of folders of observation and simulation time-series input files 
    and catchment calibration and evaluation output files.
    
    Parameters
    ----------
    project_path : str
        Path to the project's folder.
    catchment_observation_plot_path : str
        Path to the catchment observation plot folder, as returned by generate_observation_plot_folder()
    catchment_evaluation_plot_path : str
        Path to the catchment evaluation plot folder, as returned by generate_evaluation_plot_folder().
    
    Attributes
    ----------
    obspath : str
        Path to the folder storing observation files
    simpath : str
        Path to the folder storing simulation files
    observation_plots : str
        Path to observation plots folders
    recession : dict
        Paths to baseflow ('BF') and quickflow ('QF') recession plot folders.
    ET : str
        Path to the evapotranspiration plot folder.
    soil : dict
        Paths to soil boxcox, timeseries, and evaluation plot folders.
    runoff : dict
        Paths to runoff boxcox, timeseries, and evaluation plot folders.
    statistics : dict
        Paths to baseflow/quickflow/totalflow statistics plot folders.
    waterbalance : dict
        Paths to baseflow/quickflow/totalflow water balance plot folders.
    """
    
    def __init__(self, project_path, catchment_observation_plot_path, catchment_evaluation_plot_path):
        
        self.obs = os.path.join(project_path, "observation", "observations")
        self.sim = os.path.join(project_path, "simulation", "simulationoutput")
        
        self.observation_plots = catchment_observation_plot_path

        self.recession = {'BF': os.path.join(catchment_evaluation_plot_path, "recession", 'baseflow'),
                          'QF': os.path.join(catchment_evaluation_plot_path, "recession", 'quickflow')
                          }
        
        self.ET = os.path.join(catchment_evaluation_plot_path, "ET") # No subfolders
        
        self.soil = {'boxcox': os.path.join(catchment_evaluation_plot_path, "soil", 'boxcox'),
                     'timeseries': os.path.join(catchment_evaluation_plot_path, "soil", 'timeseries'),
                     'evaluation': os.path.join(catchment_evaluation_plot_path, "soil", 'evaluation')
                     }
        
        self.runoff = {'boxcox': os.path.join(catchment_evaluation_plot_path, "runoff", 'boxcox'),
                       'timeseries': os.path.join(catchment_evaluation_plot_path, "runoff", 'timeseries'),
                       'evaluation': os.path.join(catchment_evaluation_plot_path, "runoff", 'evaluation')
                       }
        
        self.statistics = {'BF': os.path.join(catchment_evaluation_plot_path, "statistics", 'baseflow'),
                           'QF': os.path.join(catchment_evaluation_plot_path, "statistics", 'quickflow'),
                           'TF': os.path.join(catchment_evaluation_plot_path, "statistics", 'totalflow')
                           }
        
        self.waterbalance = {'BF': os.path.join(catchment_evaluation_plot_path, "waterbalance", 'baseflow'),
                             'QF': os.path.join(catchment_evaluation_plot_path, "waterbalance", 'quickflow'),
                             'TF': os.path.join(catchment_evaluation_plot_path, "waterbalance", 'totalflow')
                           }