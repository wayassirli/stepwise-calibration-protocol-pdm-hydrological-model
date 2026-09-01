# -*- coding: utf-8 -*-
"""Create output folder and stores their path for the result of catchment calibration and evaluation

Created on Thu Aug 13 14:03:34 2026
@author: Way
"""

import os

# Project's main directory
sourcecode_path = os.path.dirname(__file__)
project_path = os.path.dirname(sourcecode_path)

def output_folder(catchment):
    """Create the output folder and subfolders for a catchment.

    Parameters
    ----------
    catchment : str
        Name of the catchment, used as the output folder name

    Returns
    -------
    catchment_path : str
        Path to the catchment output folder
    """
    
    catchment_path = os.path.join(
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
        os.makedirs(                                    
            os.path.join(catchment_path, subfolder),   # generate path of the subfolder e.g. .../Minderhout/soil/boxcox
            exist_ok=True                              # if the generated path exist, skip silently without rising errors. if it does not exist yet, makedirs
        )                                              
    
    return catchment_path

class Directory:
    """Container of folders of observation and simulation time-series input files 
    and catchment calibration and evaluation output files.
    
    Parameters
    ----------
    project_path : str
        Path to the project's folder
    
    catchment_path : str
        Path to the catchment's output folder, as returned by output_folder().
    
    Attributes
    ----------
    obspath : str
        Path to the folder storing observation files
    simpath : str
        Path to the folder storing simulation files
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
    
    def __init__(self, project_path, catchment_path):
        
        self.obs = os.path.join(project_path, "observation", "observations")
        self.sim = os.path.join(project_path, "simulation", "simulationoutput")

        self.recession = {'BF': os.path.join(catchment_path, "recession", 'baseflow'),
                          'QF': os.path.join(catchment_path, "recession", 'quickflow')
                          }
        
        self.ET = os.path.join(catchment_path, "ET") # No subfolders
        
        self.soil = {'boxcox': os.path.join(catchment_path, "soil", 'boxcox'),
                     'timeseries': os.path.join(catchment_path, "soil", 'timeseries'),
                     'evaluation': os.path.join(catchment_path, "soil", 'evaluation')
                     }
        
        self.runoff = {'boxcox': os.path.join(catchment_path, "runoff", 'boxcox'),
                       'timeseries': os.path.join(catchment_path, "runoff", 'timeseries'),
                       'evaluation': os.path.join(catchment_path, "runoff", 'evaluation')
                       }
        
        self.statistics = {'BF': os.path.join(catchment_path, "statistics", 'baseflow'),
                           'QF': os.path.join(catchment_path, "statistics", 'quickflow'),
                           'TF': os.path.join(catchment_path, "statistics", 'totalflow')
                           }
        
        self.waterbalance = {'BF': os.path.join(catchment_path, "waterbalance", 'baseflow'),
                             'QF': os.path.join(catchment_path, "waterbalance", 'quickflow'),
                             'TF': os.path.join(catchment_path, "waterbalance", 'totalflow')
                           }