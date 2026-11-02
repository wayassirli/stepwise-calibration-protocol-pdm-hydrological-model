# -*- coding: utf-8 -*-
"""Command-line entry point for executing submodel calibration and performance evaluation

Usage
-----
    python main.py <catchment> <period_id> <stage> <calibration_target/evaluation_method> [flow_type]

Arguments
---------
catchment : str
    Name of the catchment to be calibrated or evaluated.
period_id : str
    Unique identifier of the simulation period to be calibrated or evaluated.
commands : str
    calibrate_to, evaluate, or plot_observed
selection : str
    recession/ET/soil/runoff/ for calibrate_to, statistics/waterbalance for evaluate, rainfallflow/ET/flows for plot_observed.
flow_type: str
    "BF", "TF", "QF" to only calibrate or evaluate a specific type of flow. All flows will be calibrated or evaluated when not specified

Created on Sat Jul 11 23:55:34 2026
@author: Way
"""

import sys

from directory import project_path
from directory import generate_observation_plot_folder, generate_evaluation_plot_folder
from directory import Directory

from config import check_command, check_plot_observatio_command
from config import check_catchment_period_id_match, check_command_config_matches

from commands import _get_simulation_period
from commands import plot_observed_rainfall_flow, plot_observed_flows
from commands import evaluate_recession, evaluate_et, evaluate_soil, evaluate_runoff
from commands import evaluate_statistics, evaluate_waterbalance


if __name__ == "__main__":

    if len(sys.argv) == 5: # flow_type is not specified
        
        catchment = sys.argv[1]          
        period_id = sys.argv[2]
        command = sys.argv[3]
        option = sys.argv[4]
        flow_type = None

        start, end = _get_simulation_period(catchment, period_id)
        
        check_command(catchment, period_id, command)
        check_command_config_matches(command, option, catchment, period_id)
        check_catchment_period_id_match(catchment, period_id)
        check_command_config_matches(command, option, catchment, period_id)
        
        catchment_observation_plot_path = generate_observation_plot_folder(catchment)
        catchment_evaluation_plot_path = generate_evaluation_plot_folder(catchment)
        directories = Directory(project_path, catchment_observation_plot_path, catchment_evaluation_plot_path)
        
        if command == "plot_observation":
            if option == "rainfallflow":
                plot_observed_rainfall_flow(catchment, period_id, start, end, directories)
            elif option == "flows":
                plot_observed_flows(catchment, period_id, start, end, directories)
            
        elif command == "calibrate_to":
            
            if option == "ET":
                evaluate_et(catchment, period_id, start, end, directories)
            elif option == "soil":
                evaluate_soil(catchment, period_id, start, end, directories)
            
            elif option == "runoff":
                evaluate_runoff(catchment, period_id, start, end, directories)
          
            elif option == "recession":
                # when flow_type is not specified, evaluate all flow_type 
                for flow_type in ["QF", "BF"]:
                    evaluate_recession(catchment, period_id, start, end, flow_type, directories)
        
        elif command == "evaluate": 
            if option == "statistics":
                # when flow_type is not specified, evaluate all flow_type
                for flow_type in ["QF", "BF", "TF"]:
                    evaluate_statistics(catchment, period_id, start, end, flow_type, directories)
            
            elif option == "waterbalance":
                # when flow_type is not specified, evaluate all flow_type
                for flow_type in ["QF", "BF", "TF"]:
                    evaluate_waterbalance(catchment, period_id, start, end, flow_type, directories)
        
    elif len(sys.argv) == 6: # flow_type is specified
        
        catchment = sys.argv[1]          
        period_id = sys.argv[2]
        command = sys.argv[3]
        option = sys.argv[4]
        flow_type = sys.argv[5]
        
        start, end = _get_simulation_period(catchment, period_id)

        check_command(catchment, period_id, command)
        check_command_config_matches(command, option, catchment, period_id)        
        check_catchment_period_id_match(catchment, period_id)
        check_command_config_matches(command, option, catchment, period_id)
        
        catchment_observation_plot_path = generate_observation_plot_folder(catchment)
        catchment_evaluation_plot_path = generate_evaluation_plot_folder(catchment)
        directories = Directory(project_path, catchment_observation_plot_path, catchment_evaluation_plot_path)
        
        if command == "plot_observation":
            if option == "flows":
                plot_observed_flows(catchment, period_id, start, end, directories, flow_type = flow_type)
        
        elif command == "calibration_target":
            if option == "recession":
                evaluate_recession(catchment, period_id, start, end, flow_type, directories)
        
        elif command == "evalution_method":
            if option == "statistics":
                evaluate_statistics(catchment, period_id, start, end, flow_type, directories)
            elif option == "waterbalance":
                evaluate_waterbalance(catchment, period_id, start, end, flow_type, directories)  

    else:
        print("Invalid number of argument.\n"
              "Usage:\n"
              "   python main.py catchment period_id stage calibration_target/evaluation_method\n"
              "   python main.py catchment period_id stage calibration_target/evaluation_method flow_type"
        )
        sys.exit(1)