# -*- coding: utf-8 -*-
"""Load and validate configuration files independently and against requested execution through command-lines

Created on Sun Oct 11 22:29:31 2026
@author: Way
"""

import os
import pandas as pd
from directory import project_path

config_obs = pd.read_excel(os.path.join(project_path, "observation", "config_observations.xlsx"))

simulations = pd.read_excel(os.path.join(project_path, "simulation", "config_simulations.xlsx"), sheet_name="simulations")
parameters = pd.read_excel(os.path.join(project_path, "simulation", "config_simulations.xlsx"), sheet_name="parameters")

config_sim = simulations.merge(parameters, 
             on=["simulation_id", "catchment", "period_id", "calibration_target","evaluation_method", "flow_type"])

config_periods  = pd.read_excel(os.path.join(project_path, "evaluation", "config_periods.xlsx"), sheet_name="simulation_periods")
flow_periods = pd.read_excel(os.path.join(project_path, "evaluation", "config_periods.xlsx"), sheet_name="flow_periods")

#%% The check on configuration files, independent/not considering what command-line execution user requested

def check_categorical_values(config, config_df, sheet, allowed_values_dict):
    """Check categorical values in configuration files against their allowed values.
    
    Parameters
    ----------
    config_df : pandas.DataFrame
        One of three configuration excels in DataFrame format to be checked.
    sheet : str
        Name of the sheet inside the configuration excels.
    allowed_values_dict : dict
        Dictionary containing column names as key and their corresponding allowable values, 
        i.e. "recession", "ET", "soil", "runoff" for "calibration_target".

    Returns
    -------
    errors : list of str

    """
    
    errors = []
    
    for column, allowed_values in allowed_values_dict.items(): # i.e. loop the 4 columns to check
        if column not in config_df.columns:              # i.e. check if 1 of 4 columns i.e. "calibration_target" in config excel
            continue                                     # if no, continue
        
        # if there is 1 of 4 column inside config excel
        column_values = config_df[column].astype("string") # create pd.Series containing the string of the column value i.e. "ET", "et"
        invalid_values = (                                 # create pd.Series of boolean, True or False if the value is invalid
            column_values.notna()                          # if value is not empty
            & ~column_values.isin(allowed_values)           # and if value is not according to allowed_value
        )                                                  # they are True in invalid_values
        
        for index, value in column_values[invalid_values].items():
            errors.append(
                f"Config excel: {config}, Sheet: {sheet}, \n"
                f"Column: {column}, Row: {index + 2}: \n"
                f"Invalid value: {value}\n"
                f"Allowed values for {column}: {sorted(allowed_values)}"
            )
    
    return errors

def check_conditional_values():
    """Check that required configuration cells are not empty for each commands and option execution.
    """
    errors = []
    
    checked_columns = ["calibration_target", "evaluation_method"]

    for column, column_values in config_sim.items():
        
        if column not in checked_columns:
            continue
        
        for index, value in column_values.items():
            if pd.isna(value):
                continue
            
            elif value in ["ET", "soil"]:
                required_fields = ["ETa_soilmoisture_filename", "λSWd"]
            
            elif value == "runoff":
                required_fields = ["baseflow_quickflow_filename", "λQF"]
            
            elif value in ["recession", "statistics", "waterbalance"]:
                required_fields = ["baseflow_quickflow_filename"]
                
            for field in required_fields:
                
                if pd.isna(config_sim[field][index]):
                    errors.append(
                        f"Config excel: config_simulation.xlsx, Sheet: simulations, Row: {index + 2}:\n"                        
                        f"Required field {field} is empty for {column}: {value}"
                    )   
    
    return errors

def check_parameter_values():
    """Check that required parameters values are not empty for each simulation scenario.
    """
    
    errors = []
    
    for index, sim_id in config_sim["simulation_id"].items():
        
        if pd.isna(sim_id):
            continue
        
        option = config_sim["calibration_target"][index]
        
        if pd.isna(option) or option not in ["ET", "soil"]:
            continue
        
        command = "Calibration Target"
        
        if option == "ET":
            columns_to_check = ["ET_params1", "soil_function", "soil_params1", "soil_params2", "soil_params3"]
            
        elif option == "soil":
            columns_to_check = ["soil_function", "soil_params1", "soil_params2", "soil_params3"]
            

        for column in columns_to_check:
                    
            if pd.isna(config_sim[column][index]):
                errors.append(f": Column '{column}' for simulation {sim_id} and execution '{command}' '{option}' is empty")
    
    return errors

def check_configuration():
    
    errors = []
    
    ## 1 Check categorical values
    # Dictionary 1, categorical values in "simulation" sheet
    allowed_values_simulation_sheet_dict = {
        "calibration_target": {"recession", "ET", "soil", "runoff"},
        "evaluation_method": {"statistics", "waterbalance"},
        "flow_type": {"BF", "QF", "TF"}    
        }
    
    # Dictionary 2, categorical values in "flow_period" sheet
    allowed_flow_period_type_dict = {
        "flow_period_type": {"slow", "quick"}
        }
        
    # Dictionary 3, categorical values in "parameters" sheet
    allowed_soil_function_dict = {
            "soil_function": {"pareto", "rectangular", "triangular"}
        }
    
    # Check categorical values error in "simulations" sheet in config_simulation.xlsx
    errors.extend(check_categorical_values("config_simulation.xlsx", config_sim, "simulations", allowed_values_simulation_sheet_dict))
    # Check categorical values error in "flow_periods" sheet
    errors.extend(check_categorical_values("config_periods.xlsx", config_periods, "flow_periods", allowed_flow_period_type_dict))
    # Check categorical values error in "parameters" sheet in config_simulation.xlsx
    errors.extend(check_categorical_values("config_simulation.xlsx", config_sim, "parameters", allowed_soil_function_dict))
    
    ## 2 Check conditional values
    errors.extend(check_conditional_values())
    
    ## 3 Check parameter values
    errors.extend(check_parameter_values())
    
    if errors:
        raise ValueError("\n\n".join(errors))
    

#%% The check on configuration files according to what command-line execution user requested

def check_catchment_period_id_match(catchment, period_id):
    """Validate the consistency of catchment and period id between the three configuration files.
    Only for specific catchment and period_id requested through command-line execution 
    """
    
    errors = []
    
    # Boolean pd.Series
    config_sim_matches = (
        (config_sim["catchment"] == catchment) & 
        (config_sim["period_id"] == period_id)
    ) 
    
    if not config_sim_matches.any():
        errors.append(
            f"No matching catchment {catchment} and period {period_id} found in config_simulations.xlsx"
        )
    
    config_periods_matches = (
        (config_periods["catchment"] == catchment) & 
        (config_periods["period_id"] == period_id)
    )
                              
    if not config_periods_matches.any():
        errors.append(
            f"Catchment '{catchment}' and period '{period_id}' configuration found in config_simulations.xlsx, "
            f"but no matching combination found in config_periods.xlsx."
        )
    
    config_obs_matches = config_obs["catchment"] == catchment
    
    if not config_obs_matches.any():
        errors.append(
            f"Catchment '{catchment}' and period '{period_id}' configuration found in config_simulations.xlsx and config_period.xlsx, "
            f"but no matching catchment found in config_observation.xlsx"
        )
    
    if errors:
        raise ValueError("\n\n".join(errors))

def check_command(catchment, period_id, command):
    """Validate the command provided through command-line arguments.
    """
    
    allowable_commands = ["plot_observation", "calibrate_to", "evaluate"]
        
    if command not in allowable_commands:
        raise ValueError(
            f"Cannot execute {command} for catchment '{catchment}' during '{period_id}' period: \n"
            f"Available commands are 'plot_observation', 'calibrate_to', and 'evaluate'"
        )

def check_command_config_matches(command, option, catchment, period_id, flow_type = None):
    """If the command exist, check if the option requested through command-line arguments is configured
    """
    
    errors = []
    
    if command == "calibrate_to":
        column_to_check = "calibration_target"
                    
    elif command == "evaluate":
        column_to_check = "evaluation_method"
        
    config_sim_catchment_period_id = config_sim[
        (config_sim["catchment"] == catchment) & 
        (config_sim["period_id"] == period_id)
    ]
    
    if flow_type is not None:
        config_sim_catchment_period_id = config_sim_catchment_period_id[
            (config_sim_catchment_period_id["flow_type"] == flow_type)
        ] 
        
    if option not in config_sim_catchment_period_id[column_to_check].values:
        
        if flow_type is not None:
            flow_type_errors = f"for flow type: {flow_type}"
        else:
            flow_type_errors = ""
        
        errors.append(
            f"Cannot execute '{command} {option} {flow_type_errors}' for catchment '{catchment}' during '{period_id}' period: \n"
            f"No matching configuration found in config_simulations.xlsx."
        )
        
    if errors:
        raise ValueError("\n\n".join(errors))

def check_plot_observation_command(catchment, period_id, command, option):
    """Validate the options of plot_observation command provided through command-line arguments.
    """
    
    if command == "plot_observation":
        
        allowable_options = ["rainfallflow", "flows"]
        
        if option not in allowable_options:
            raise ValueError(
                f"Cannot execute {command} {option} for catchment '{catchment}' during '{period_id}' period: \n"
                f"Available options for observation plots are 'rainfallflow' or 'flows'"
            )