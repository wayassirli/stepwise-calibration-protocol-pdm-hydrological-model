# -*- coding: utf-8 -*-
"""Command-line entry point for executing submodel calibration and performance evaluation

Usage
-----
    python main.py <catchment> <period_id> <stage> <calibration_target/evaluation_method> [flowtype]

Arguments
---------
catchment : str
    Name of the catchment to be calibrated or evaluated.
period_id : str
    Unique identifier of the simulation period to be calibrated or evaluated.
stage : str    
    "submodel" to calibrate submodel against a calibration target, "overall" to evaluate overall model performance.
calibration_target : str
    when stage = "submodel", one of "recession", "ET", "soil", "runoff".
evaluation_method : str
    when stage = "overall", one of "statistics", "waterbalance".
flowtype: str
    "BF", "TF", "QF" to only calibrate or evaluate a specific type of flow. All flows will be calibrated or evaluated when not specified

Created on Sat Jul 11 23:55:34 2026
@author: Way
"""

import sys
from directory import project_path
from directory import output_folder
from directory import Directory
from calibration import simulation_period
from calibration import evaluate_recession
from calibration import evaluate_statistics, evaluate_waterbalance
from calibration import evaluate_eta, evaluate_soil
from calibration import evaluate_runoff

if __name__ == "__main__":

    if len(sys.argv) == 6: # flowtype is not specified
        
        catchment = sys.argv[1]          
        period_id = sys.argv[2]
        stage = sys.argv[3]
        calibration_target =sys.argv[4]
        evaluation_method = sys.argv[5]
        
        start, end = simulation_period(catchment, period_id)
        catchment_path = output_folder(catchment)
        directories = Directory(project_path, catchment_path)
        
        if stage == "submodel":
            
            if calibration_target == "ETa":
                evaluate_eta(catchment, period_id, start, end, directories)
            elif calibration_target == "soil":
                evaluate_soil(catchment, period_id, start, end, directories)
            
            elif calibration_target == "runoff":
                evaluate_runoff(catchment, period_id, start, end, directories)
          
            elif calibration_target == "recession":
                # when flowtype is not specified, evaluate all flowtype 
                for flowtype in ["QF", "BF"]:
                    evaluate_recession(catchment, period_id, start, end, flowtype, directories)
        
        else: 
            if evaluation_method == "statistics":
                # when flowtype is not specified, evaluate all flowtype
                for flowtype in ["QF", "BF", "TF"]:
                    evaluate_statistics(catchment, period_id, start, end, flowtype, directories)
            
            elif evaluation_method == "waterbalance":
                # when flowtype is not specified, evaluate all flowtype
                for flowtype in ["QF", "BF", "TF"]:
                    evaluate_waterbalance(catchment, period_id, start, end, flowtype, directories)
        
    elif len(sys.argv) == 7: # flowtype is specified
        
        catchment = sys.argv[1]          
        period_id = sys.argv[2]
        stage = sys.argv[3]
        calibration_target =sys.argv[4]
        evaluation_method = sys.argv[5]
        flowtype = sys.argv[6]
        
        start, end = simulation_period(catchment, period_id)
        catchment_path = output_folder(catchment)
        directories = Directory(project_path, catchment_path)
        
        if stage == "submodel":
            if calibration_target == "recession":
                evaluate_recession(catchment, period_id, start, end, flowtype, directories)
        
        else:
            if evaluation_method == "statistics":
                evaluate_statistics(catchment, period_id, start, end, flowtype, directories)
            elif evaluation_method == "waterbalance":
                evaluate_waterbalance(catchment, period_id, start, end, flowtype, directories)  

    else:
        print("Invalid number of argument.\n"
              "Usage:\n"
              "   python main.py catchment period_id stage calibration_target/evaluation_method\n"
              "   python main.py catchment period_id stage calibration_target/evaluation_method flowtype"
        )
        sys.exit(1)