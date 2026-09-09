# -*- coding: utf-8 -*-
"""Step-wise calibration protocol: Evaluate submodel performance and overall model performance.

Created on Tue Mar  3 12:35:24 2026
@author: Way
"""

import pandas as pd
import numpy as np
from observation import Observation
from simulation import Simulation
from plot import plot_et_actual_vs_potential, plot_et_ratio, plot_soil_water_depth_multi
from plot import plot_soil_evaluation, plot_soil_report
from plot import plot_runoff_evaluation, plot_runoff_report
from plot import plot_flow_timeseries, plot_flow_waterbalance

#%% config.py
# Used to filter rows on configuration excels

config_obs = pd.read_excel("observation/config_observations.xlsx")

simulations = pd.read_excel("simulation/config_simulations.xlsx", sheet_name="simulations")
parameters = pd.read_excel("simulation/config_simulations.xlsx", sheet_name="parameters")
config_sim = simulations.merge(parameters, on=["simulation_id", "stage", "calibration_target","evaluation_method", "flow_type"])

config_periods  = pd.read_excel("evaluation/config_periods.xlsx", sheet_name="simulation_periods")
flow_periods = pd.read_excel("evaluation/config_periods.xlsx", sheet_name="flow_periods")

#%% Helper Functions

def _get_simulation_period(catchment, period_id):
    """Look up the start and end date of simulation period in Timestamp format for a given catchment and period_id

    Parameters
    ----------
    catchment : str
        Catchment name associated with the simulation period is to be extracted, 
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    period_id : str
        Unique identifier for the simulation period,
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
        
    Raises
    ------
    ValueError
        If 0 or more than 1 rows in config_periods matches the given catchment and period_id.
        (indicates a typo or duplicate entry in config_periods.xlsx)

    Returns
    -------
    start : pandas.TimeStamp
        Start date of the simulation period.
    end : TYPE
        End date of the simulation period.
    """

    period_rows = config_periods[
        (config_periods["catchment"] == catchment) &
        (config_periods["period_id"] == period_id)
    ]

    if len(period_rows) != 1:
        raise ValueError(
            f"No single match for catchment={catchment} and period_id={period_id}."
            "Make sure the data you entered match exactly what you write in the config_periods.xlsx"
        )
    
    period_row = period_rows.iloc[0]
    start = pd.to_datetime(period_row["start_date"], dayfirst=True)
    end = pd.to_datetime(period_row["end_date"], dayfirst=True)
    
    return start, end

def _get_slowflow_periods(catchment, period_id, df):
    """Build a list of start and end blocks (start, end) for the slow flow periods derived from WETSPRO
    
    Parameters
    ----------
    catchment : str
        Catchment name, must match entry in
        evaluation/config_periods.xlsx (sheet: flow_periods).
    period_id : TYPE
        Unique identifier for the simulation period, must match entry in
        evaluation/config_periods.xlsx (sheet: simulation_periods).
    df : pandas.Series
        Observation time-series for this catchment and simulation period, 
        used only to determine the final timestep as the "end" of the last slow flow period block

    Returns
    -------
    slowflowperiods : list of tuple (int, int)
        DESCRIPTION.

    Notes
    -----
    WETSPRO provide the boundaries of slow flow periods by giving the starts of each timestep counting from 1.
        start_timesteps = [1, 4268, 12490]
    Python index starts from 0.
        start_timesteps = [0, 4267, 12489]
    A block of slow flow period is built by counting from the start until the one timestep before the next start.
         slowflowperiods = [(0, 4266), (4267, 12488), (12489, end)]
    Since WETSPRO did not provide the end for the last slow flow period block, only (start_timesteps) - 1 number of blocks can be built this way    
    the last slow flow block is build using the final timestep determined form the df 
    """

    start_timesteps = flow_periods[
        (flow_periods["catchment"] == catchment) & 
        (flow_periods["period_id"] == period_id) & 
        (flow_periods["flow_period_type"] == "slow")
    ]["start_timestep"].tolist()
    
    slowflow_periods = []

    for i in range(len(start_timesteps) - 1):
        start = start_timesteps[i] - 1
        end   = start_timesteps[i+1] - 2
        slowflow_periods.append((start, end))
    
    # Last block: from the last WETSPRO start to the last index of the observed time-series passed in as df.
    last_index = len(df) - 1
    slowflow_periods.append((start_timesteps[-1] - 1, last_index))
    
    return slowflow_periods
    
def _get_quickflow_periods(catchment, period_id, df):
    """Build a list of start and end blocks (start, end) for the quick flow periods derived from WETSPRO.
    
    Parameters
    ----------
    catchment : str
        Catchment name, must match entry in
        evaluation/config_periods.xlsx (sheet: flow_periods).
    period_id : TYPE
        Unique identifier for the simulation period, must match entry in
        evaluation/config_periods.xlsx (sheet: simulation_periods).
    df : pandas.Series
        Observation time-series for this catchment and simulation period, 
        used only to determine the final timestep as the "end" of the last quick flow period block

    Returns
    -------
    quickflowperiods : list of tuple (int, int)
        DESCRIPTION.

    Notes
    -----
    WETSPRO provide the boundaries of quick flow periods by giving the starts of each timestep counting from 1.
        start_timesteps = [1, 4268, 12490]
    Python index starts from 0.
        start_timesteps = [0, 4267, 12489]
    A block of quick flow period is built by counting from the start until the one timestep before the next start.
         quickflowperiods = [(0, 4266), (4267, 12488), (12489, end)]
    Since WETSPRO did not provide the end for the last quick flow period block, only (start_timesteps) - 1 number of blocks can be built this way    
    the last quick flow block is build using the final timestep determined form the df 
    """    
    
    start_timesteps = flow_periods[
        (flow_periods["catchment"] == catchment) & 
        (flow_periods["period_id"] == period_id) & 
        (flow_periods["flow_period_type"] == "quick")
    ]["start_timestep"].tolist()
    
    quickflow_periods = []
    
    for i in range(len(start_timesteps) - 1):
        start = start_timesteps[i] - 1
        end   = start_timesteps[i+1] - 2
        quickflow_periods.append((start, end))
        
    # Last block: from the last WETSPRO start to the last index of the observed time-series passed in as df.
    last_index = len(df) - 1
    quickflow_periods.append((start_timesteps[-1] - 1, last_index))
    
    return quickflow_periods

def _convert_rate_to_depth(flow, catchment_size, frequency):
    """Convert a flow rate (m3/s) into flow depth per timestep (mm/timestep).
    
    Parameters
    ----------
    flowr : pandas.Series
        Flow rate time-series in m3/s
    catchmentsize : float
        Catchment area in m2
    frequency : str
        pandas frequency alias describing the timestep of flowrate,
        e.g. "H", "D", "15min"

    Returns
    -------
    flowvolume : pandas.Series
        Flow depth per timestep time-series in mm/timestep
    """
    
    # to_offset convert pandas frequency alias (e.g. "15min", "H") to a pandas offset/duration object (e.g. <hour>, 2 * <hour>)
    freq_object = pd.tseries.frequencies.to_offset(frequency) 
    
    # Timedelta convert the offset/duration object to seconds (e.g. <hour> to 3600 seconds)
    freq_seconds = pd.Timedelta(freq_object).total_seconds()
    
    flow_depth = (flow * freq_seconds / catchment_size) * 1000  
    return flow_depth

def _calculate_smax_pareto(cmin, cmax, b):
    """Compute total available storage (Smax) or mean storage capacity of the catchment (c̄), assuming a Pareto distribution.
    of soil storage capacity across the catchment
    
    Parameters
    ----------
    cmin, cmax : float
        Minimum and maximum soil storage capcaity across the catchment.
    b : float
        Pareto disitribution parameter shape.

    Returns
    -------
    Smax : float
        Total available storage (Smax) of the catchment
    """
    Smax = (b * cmin + cmax) / (b + 1)
    return Smax

def _calculate_smax_rectangular(cmin, cmax):
    """Compute total available storage (Smax) or mean storage capacity of the catchment (c̄), assuming a rectangular distribution.
    of soil storage capacity across the catchment
    
    Parameters
    ----------
    cmin, cmax : float
        Minimum and maximum soil storage capcaity across the catchment.

    Returns
    -------
    Smax : float
        Total available storage (Smax) of the catchment
    """
    Smax = ( cmax * ((cmax / 2) - cmin) ) / (cmax - cmin)
    return Smax

def _calculate_smax_triangular(cmin, cmax):
    """Compute total available storage (Smax) or mean storage capacity of the catchment (c̄), assuming a triangular distribution.
    of soil storage capacity across the catchment
    
    Parameters
    ----------
    cmin, cmax : float
        Minimum and maximum soil storage capcaity across the catchment.

    Returns
    -------
    Smax : float
        Total available storage (Smax) of the catchment
    """
    Smax = cmin + ((cmax - cmin) / 2)
    return Smax

def _extract_maximum_values(flow_periods, obs_series, sim_series):
    """Extract maximum observed value i.e. runoff/soil water depth and the simulated value at that timestamp, 
    for each flow period block. 

    Parameters
    ----------
    flow_periods : list of tuples (int, int)
        (start, end) pairs returned by _slowflowperiod or _quickflowperiod
    obs_series, sim_series : pandas.Series
        Observed and simulated time-series from which the peak value is extracted from

    Returns
    -------
    df : pandas.DataFrame
        Columns: peak_time, obs, sim - one row per each flow period block.
    """
    
    result = [] 
    
    for start, end in flow_periods:
        obs_period    = obs_series.iloc[start:end+1] # .iloc[] is a method for integers (datatype of start, end)
        max_timestamp = obs_period.idxmax()          # in pandas.Timestamp format
        obs_max       = obs_period.max()

        sim_max = sim_series.loc[max_timestamp]      # .loc[] is a method for pandas.Timestamp or pandas.Datetime (dataype of max_timestamp)
        
        result.append({
            "max_timestamp": max_timestamp,
            "obs": obs_max,
            "sim": sim_max
            })

    df = pd.DataFrame(result)
    return df
        
def _extract_minimum_values(flow_periods, obs_series, sim_series):
    """ Extract the minimum observed and simulated value  at the end of each flow period block (the smallest value/low point). 

    Parameters
    ----------
    flow_periods : list of tuples (int, int)
        (start, end) pairs returned by _slowflowperiod or _quickflowperiod
    obs_series, sim_series : pandas.Series
        Observed and simulated time-series from which the peak value is extracted from

    Returns
    -------
    df : pandas.DataFrame
        Columns: low_time, obs, sim - one row per each flow period block.
    """
    result = []
    
    for start, end in flow_periods:
        
        min_timestamp = obs_series.index[end]   # in pandas.Timestamp format
        obs_min = obs_series.iloc[end]
        sim_min = sim_series.iloc[end]
        
        result.append({
            "min_timestamp": min_timestamp,
            "obs": obs_min,
            "sim": sim_min
            })

    df = pd.DataFrame(result)
    return df

def _calculate_cumulative_values(flow_periods, obs_series, sim_series):
    """Calculate the cumulative values i.e. runoff/recharge of simulated and observed time-series for each flow period block,
    along with the midpoint timestamp for plotting    

    Parameters
    ----------
    flow_periods : list of tuples (int, int)
        (start, end) pairs returned by _slowflowperiod or _quickflowperiod
    obs_series, sim_series : pandas.Series
        Observed and simulated time-series from which the cumulative value is calculated from

    Returns
    -------
    df : pandas.DataFrame
        Columns: mid_flow_period, obs, sim - one row per each flow period block.
    """
    result = []
    
    for start, end in flow_periods:
        
        obs_cumulative_value = obs_series.iloc[start:end+1].sum() # end+1 because .iloc[] slicing excludes the end value
        sim_cumulative_value = sim_series.iloc[start:end+1].sum()
        
        # midpoint is used as the x-coordinate (midpoint of each flow period block) when plotting the volume on the graph 
        midpoint = int(start + (end - start) / 2) # int() because midpoint value requires integer and division can produce float
        position = obs_series.index[midpoint]
        
        result.append({
            "mid_flow_period": position,
            "obs": obs_cumulative_value,
            "sim": sim_cumulative_value
            })
        
    df = pd.DataFrame(result)
    return df

def _transform_boxcox(obs_df, sim_df, λ):
    """ Apply a Box-cox transformation to the observed and simulated data.
    
    Parameters
    ----------
    obs_df, sim_df: pandas.DataFrame
        Observed and simulated data to transform.
    λ : float
        Box-cox transformation parameter. Value ranges between 0 to 1 and must not be 0

    Returns
    -------
    BC_obs_df, BC_sim_df : pandas.DataFrame
        Box-cox transformed observed and simulated data.
    """
    BC_obs_df = ((obs_df ** λ) - 1) / λ
    BC_sim_df = ((sim_df ** λ) - 1) / λ
    
    return BC_obs_df, BC_sim_df

def _get_flow(source, flow_type, start, end):
    """Select a flow type for their time-series to be exported and slice between the start and end

    Parameters
    ----------
    source : Simulation or Observation
        The observed or simulated object the flow is extracted from.
    flowtype : {"QF", "BF", "TF"}
        The flow type selected to be returned (baseflow, quick flow or total flow).
    start, end : pandas.Timestamp
        Start and end of the simulation period used to slice the time-series.
        
    Returns
    -------
    pandas.Series
        Flow in m3/s for the requested flow type between start and end.
        
    Raises
    ------
    ValueError
        If flowtype is not one of "QF", "BF", "TF".
    """
    
    if flow_type == "QF":
        return source.QF_m3s.loc[start:end]
    elif flow_type == "BF":
        return source.BF_m3s.loc[start:end]
    elif flow_type == "TF":
        return (
            source.QF_m3s.loc[start:end] + 
            source.BF_m3s.loc[start:end]
            )
    else:
        raise ValueError(f"Unknown flow type: {flow_type!r}. Expected 'QF', 'BF', or 'TF'.")

def _get_obs_label(flow_type):
    """Return the plot-legend label for the observed series, based on flow type.

    Parameters
    ----------
    flow_type : {"QF", "BF", "TF"}
        Which flow component the label is for.

    Returns
    -------
    str
        "filtered Observation" for QF/BF, "Observation" for TF.
    """
    labels = {
        "QF": "filtered Observation",
        "BF": "filtered Observation",
        "TF": "Observation",
    }
    return labels[flow_type]

#%% Public Functions

def evaluate_recession(catchment, period_id, start, end, flow_type, directories):
    """Evaluate routing submodels' performance using flow recession characteristics in flow time-series as a calibration target.
    
    Parameters
    ----------
    catchment : str
        Catchment name associated with the simulation to be evaluated.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    period_id : str
        Unique identifier for the simulated period to evaluate.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    start, end : pandas.TimeStamp
        Start and end of period where simulation is evaluated.
    flow_type : {"QF", "BF"}
        The flow type selected to be evaluated (baseflow or quick flow).
    directories : Directories
        Object containing paths for input data and output plots, used here via
        directories.obs, directories.sim, and directories.recession[flow_type].

    Returns
    -------
    None
        Generate recession plots for routing submodel evaluation.
    """
    ## 1 Observation
    obs_row = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs    = Observation(obs_row, directories.obs)
    obs_F_m3s = _get_flow(obs, flow_type, start, end)
    
    ## 2 Simulation
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &            # passed in from main.py's command line argument
        (config_sim["period_id"] == period_id) &            # idem
        (config_sim["stage"] == "submodel") &               
        (config_sim["calibration_target"] == "recession") & 
        (config_sim["flow_type"] == flow_type)              # When flow_type is not specified as argument in the command-line->
    ]                                                       # -> functions are looped for all flowtypes (hard-coded) in main.py 
         
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        sim_id = sim.id
        sim_F_m3s = _get_flow(sim, flow_type, start, end)
        
        ## 3 Plot
        plot_flow_timeseries(obs_F_m3s = obs_F_m3s, sim_F_m3s = sim_F_m3s, 
                             years_per_figure = 3, 
                             flow_type = flow_type, obs_label = _get_obs_label(flow_type), 
                             catchment = catchment, sim_id = sim_id, period_id = period_id, 
                             output_path = directories.recession[flow_type], 
                             show_statistics=False)

def evaluate_et(catchment, period_id, start, end, directories):
    """Evaluate ET submodel performance using seasonal ET ratio as a calibration target, 
    with soil water depth as a supporting calibration target.
    
    Parameters
    ----------
    catchment : str
        Catchment name associated with the simulation to be evaluated.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    period_id : str
        Unique identifier for the simulated period to evaluate.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    start, end : pandas.TimeStamp
        Start and end of period where simulation is evaluated.
    directories : Directories
        Object containing paths for input data and output plots, used here via
        directories.obs, directories.sim, and directories.ET.

    Returns
    -------
    None
        Save three ET-related plots for ET submodel evaluation.
    
    Notes
    -----
    smd = Soil Moisture Deficit (no unit, value range: 0 < smd < 1)
    SWd = Soil Water Depth (unit: mm, 0 < SWd < Smax)
    """
    ETa_dict = {}
    ET_ratio_dict    = {}
    SWd_dict  = {}
    
    ## 1 Observation
    obs_row = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs     = Observation(obs_row, directories.obs)

    obs_ETp_mmdt = obs.ETp_mmdt.loc[start:end]
    obs_P_mmdt   = obs.P_mmdt.loc[start:end]   
    obs_Q_m3s    = obs.Q_m3s.loc[start:end]      
    
    obs_Q_mmdt = _convert_rate_to_depth(obs_Q_m3s, obs.catchment_size, obs.Q_freq)
    
    # Monthly accumulated values
    obs_ETp_mmmonth = obs_ETp_mmdt.resample("M").sum()
    obs_P_mmmonth   = obs_P_mmdt.resample("M").sum()          
    obs_Q_mmmonth   = obs_Q_mmdt.resample("M").sum()          
    
    ## 2 Simulation 
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &     # passed in from main.py's command line argument
        (config_sim["period_id"] == period_id) &     # idem
        (config_sim["stage"] == "submodel") &
        (config_sim["calibration_target"] == "ETa")
    ]
    
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        sim_id = sim.parameters["ET_params1"]        # ET exponent is used as scenario identifier 
        
        ## 2.1 ETa
        sim_smd = sim.smd.loc[start:end]
        sim_ETa_mmday   = sim.ETa_mmday.loc[start:end]
        sim_ETa_mmmonth = sim_ETa_mmday.resample("M").sum()
        ETa_dict[sim_id] = sim_ETa_mmmonth      
        
        ## 2.2 Actual to potential evapotranspiration ratio (ET ratio)
        ET_ratio = sim_ETa_mmmonth / obs_ETp_mmmonth
        ET_ratio_dict[sim_id] = ET_ratio
        
        ## 2.3 Total storage capacity (Smax) or Mean storage capacity over the catchment (c̄) 
        soil_function = sim.parameters["soil_function"]
        if soil_function == "pareto":        
            Smax = _calculate_smax_pareto(sim.parameters["soil_params1"], sim.parameters["soil_params2"], sim.parameters["soil_params3"])
        elif soil_function == "rectangular":
            Smax = _calculate_smax_rectangular(sim.parameters["soil_params1"], sim.parameters["soil_params2"])
        elif soil_function == "triangular":
            Smax = _calculate_smax_triangular(sim.parameters["soil_params1"], sim.parameters["soil_params2"])
        
        ## 2.4 Soil water depth (SWd)
        initial_smd = sim_smd.loc[start:end].iloc[0]
        initial_SWd = Smax * (1 - initial_smd)
        SWd = initial_SWd + (obs_P_mmmonth - obs_Q_mmmonth - sim_ETa_mmmonth).cumsum()
        SWd_dict[sim_id] = SWd
    
    ## 3 Plot
    plot_et_actual_vs_potential(ETp_series = obs_ETp_mmmonth, 
                                ETa_dict = ETa_dict, 
                                catchment = obs.catchment, 
                                period_id = period_id,
                                output_path = directories.ET)
    plot_et_ratio(ET_ratio_dict = ET_ratio_dict,
                  catchment = obs.catchment, 
                  start = start, end = end, 
                  period_id = period_id, 
                  output_path = directories.ET)
    plot_soil_water_depth_multi(SWd_dict = SWd_dict, 
                                catchment = obs.catchment, 
                                start = start, end = end, 
                                period_id = period_id, 
                                output_path = directories.ET)

def evaluate_soil(catchment, period_id, start, end, directories):
    """Evaluate submodel(s) related to soil moisture dynamics using event-based soil water depth as a calibration target.
    When standard/demand-based method is selected, soil water depth is a calibration target for soil storage and recharge submodels.
    When splitting method is selected, soil water depth is primarily the calibration target for soil storage model.
    
    Parameters
    ----------
    catchment : str
        Catchment name associated with the simulation to be evaluated.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    period_id : str
        Unique identifier for the simulated period to evaluate.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    start, end : pandas.TimeStamp
        Start and end of period where simulation is evaluated.
    directories : Directories
        Object containing paths for input data and output plots, used here via
        directories.obs, directories.sim, and directories.soil.

    Returns
    -------
    None.
        Generate 
    """
    ## 1 Observation
    obs_row = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs     = Observation(obs_row, directories.obs)
    
    obs_P_mmdt = obs.P_mmdt.loc[start:end]    
    obs_Q_m3s  = obs.Q_m3s.loc[start:end]     
  
    obs_Q_mmdt = _convert_rate_to_depth(obs_Q_m3s, obs.catchment_size, obs.Q_freq) 
    
    obs_P_mmhr       = obs_P_mmdt.resample("H").sum()          
    obs_Q_mmhr       = obs_Q_mmdt.resample("H").sum()  
    obs_PminQ_mmhr   = obs_P_mmhr - obs_Q_mmhr
    
    ## 2 Simulation 
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &
        (config_sim["period_id"] == period_id) &
        (config_sim["stage"] == "submodel") &
        (config_sim["calibration_target"] == "soil") 
    ]
    
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        
        sim_id = sim.id
        sim_λSWd = sim.λSWd
        sim_ETa_mmhr = sim.ETa_mmday.loc[start:end] / 24
        sim_smd = sim.smd.loc[start:end]
        
        ## 2.1 Total storage capacity (Smax) or mean storage capacity over the catchment (c̄) 
        soil_function = sim.parameters["soil_function"]
        if soil_function == "pareto":        
            Smax = _calculate_smax_pareto(sim.parameters["soil_params1"], sim.parameters["soil_params2"], sim.parameters["soil_params3"])
        elif soil_function == "rectangular":
            Smax = _calculate_smax_rectangular(sim.parameters["soil_params1"], sim.parameters["soil_params2"])
        elif soil_function == "triangular":
            Smax = _calculate_smax_triangular(sim.parameters["soil_params1"], sim.parameters["soil_params2"])
        
        ## 2.2 Observed soil water depth (SWd)
        initial_smd = sim_smd.iloc[0]
        initial_SWd = Smax * (1 - initial_smd)
        obs_SWd = initial_SWd + (obs_P_mmhr - obs_Q_mmhr - sim_ETa_mmhr).cumsum()
        
        ## 2.2 Simulated soil water depth (SWd)
        sim_SWd = Smax * (1-sim_smd)
        
        ## 2.3 Event-based (slow flow event) soil water depth
        slowflow_periods = _get_slowflow_periods(catchment, period_id, obs_PminQ_mmhr) # use any related timeseries to count index
        SWd_maxima = _extract_maximum_values(slowflow_periods, obs_SWd, sim_SWd)
        SWd_minima = _extract_minimum_values(slowflow_periods, obs_SWd, sim_SWd)
        
        ## 2.4 Box-cox transformed, event-based soil water depth
        BC_obs, BC_sim = _transform_boxcox(SWd_maxima["obs"], SWd_maxima["sim"], sim_λSWd)
        SWd_maxima["BC_obs"] = BC_obs
        SWd_maxima["BC_sim"] = BC_sim
        
        BC_obs, BC_sim = _transform_boxcox(SWd_minima["obs"], SWd_minima["sim"], sim_λSWd)
        SWd_minima["BC_obs"] = BC_obs
        SWd_minima["BC_sim"] = BC_sim
        
        ## 2.5 RMSE
        SWd_maxima["BC_residuals"] = SWd_maxima["BC_obs"] - SWd_maxima["BC_sim"]
        RMSE_BC_maxima = np.sqrt( np.mean(SWd_maxima["BC_residuals"] ** 2) )
        
        SWd_minima["BC_residuals"] = SWd_minima["BC_obs"] - SWd_minima["BC_sim"]
        RMSE_BC_minima = np.sqrt( np.mean(SWd_minima["BC_residuals"] ** 2) )
        
        ## 3 Plot
        plot_soil_evaluation(obs_SWd = obs_SWd, sim_SWd = sim_SWd, 
                             flow_periods = slowflow_periods, 
                             SWd_maxima = SWd_maxima, SWd_minima = SWd_minima, 
                             λ = sim_λSWd, RMSE_maxima = RMSE_BC_maxima, RMSE_minima = RMSE_BC_minima, 
                             catchment = catchment, sim_id = sim_id, period_id = period_id, 
                             output_path = directories.soil['evaluation'])
        
        plot_soil_report(obs_SWd = obs_SWd, sim_SWd = sim_SWd, 
                         flow_periods = slowflow_periods, 
                         SWd_maxima = SWd_maxima, SWd_minima= SWd_minima, 
                         λ = sim_λSWd, RMSE_maxima = RMSE_BC_maxima, RMSE_minima = RMSE_BC_minima, 
                         catchment = catchment, sim_id = sim_id, period_id = period_id, 
                         timeseries_output_path = directories.soil['timeseries'], boxcox_output_path = directories.soil['boxcox'])

def evaluate_runoff(catchment, period_id, start, end, directories):
    """Evaluate runoff-related submodel(s) using event-based accumulated runoff depth as a calibration target.
    When standard/demand-based method is selected, the accumulated runoff depth is a calibration target for soil storage and recharge submodels.
    When splitting method is selected, the accumulated runoff depth is primarily the calibration target for recharge/runoff model.
    
    Parameters
    ----------
    catchment : str
        Catchment name associated with the simulation to be evaluated.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    period_id : str
        Unique identifier for the simulated period to evaluate.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    start, end : pandas.TimeStamp
        Start and end of period where simulation is evaluated.
    directories : Directories
        Object containing paths for input data and output plots, used here via
        directories.obs, directories.sim, and directories.runoff

    Returns
    -------
    None.

    """
    
    ## 1 Observation
    obs_row = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs     = Observation(obs_row, directories.obs)

    obs_QF_m3s  = obs.QF_m3s.loc[start:end]
    obs_QF_mmdt = _convert_rate_to_depth(obs_QF_m3s, obs.catchment_size, obs.QF_freq)    
    
    ## 2 Simulation
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &
        (config_sim["period_id"] == period_id) &
        (config_sim["stage"] == "submodel") &
        (config_sim["calibration_target"] == "runoff") 
    ]    
    
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        sim_id = sim.id
        
        sim_λQF = sim.λQF
        sim_QF_m3s = sim.QF_m3s.loc[start:end]
        sim_QF_freq = pd.infer_freq(sim_QF_m3s.index)
        sim_QF_mmdt = _convert_rate_to_depth(sim_QF_m3s, obs.catchment_size, sim_QF_freq)
        
        ## 2.1 Event-based (quick flow event) cumulative runoff depth
        quickflow_periods = _get_quickflow_periods(catchment, period_id, obs_QF_m3s) # use any timeseries to count index
        QF_depth_cumulative = _calculate_cumulative_values(quickflow_periods, obs_QF_mmdt, sim_QF_mmdt)
        
        ## 2.2 Box-cox transformed, event-based cumulative runoff depth
        BC_obs, BC_sim = _transform_boxcox(QF_depth_cumulative["obs"], QF_depth_cumulative["sim"], sim_λQF)
        QF_depth_cumulative["BC_obs"] = BC_obs
        QF_depth_cumulative["BC_sim"] = BC_sim
        
        ## 2.3 RMSE
        QF_depth_cumulative["BC_residuals"] = QF_depth_cumulative["BC_obs"] - QF_depth_cumulative["BC_sim"]
        RMSE_BC = np.sqrt( np.mean(QF_depth_cumulative["BC_residuals"] ** 2) )
                        
        ## 3 Plot        
        plot_runoff_evaluation(obs_QF_mmdt = obs_QF_mmdt, sim_QF_mmdt = sim_QF_mmdt, 
                               flow_periods = quickflow_periods, 
                               QFdepth_cumulative = QF_depth_cumulative, 
                               λ = sim_λQF, RMSE = RMSE_BC, 
                               catchment = catchment, sim_id = sim_id, period_id = period_id, 
                               output_path = directories.runoff['evaluation'])

        plot_runoff_report(obs_QF_mmdt = obs_QF_mmdt, sim_QF_mmdt = sim_QF_mmdt, 
                           flow_periods = quickflow_periods, 
                           QF_depth_cumulative = QF_depth_cumulative, 
                           λ = sim_λQF, RMSE= RMSE_BC, 
                           catchment = catchment, sim_id = sim_id, period_id = period_id, 
                           timeseries_output_path = directories.runoff['timeseries'], boxcox_output_path = directories.runoff['boxcox'])

def evaluate_statistics(catchment, period_id, start, end, flow_type, directories):
    """Evaluate overall model performance using provided statistics, 
    alongside the shape of flow hydrograph and the hydrograph's peak provided in the time-series plot as evaluation target.

    Parameters
    ----------
    catchment : str
        Catchment name associated with the simulation to be evaluated.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    period_id : str
        Unique identifier for the simulated period to evaluate.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    start, end : pandas.TimeStamp
        Start and end of period where simulation is evaluated.
    directories : Directories
        Object containing paths for input data and output plots, used here via
        directories.obs, directories.sim, directories.statistics.

    Returns
    -------
    None.

    """
    
    ## 1 Observation
    obs_row   = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs       = Observation(obs_row, directories.obs)
    obs_F_m3s = _get_flow(obs, flow_type, start, end)
    
    ## 2 Simulation
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &            
        (config_sim["period_id"] == period_id) &            
        (config_sim["stage"] == "overall") &
        (config_sim["evaluation_method"] == "timeseries") & 
        (config_sim["flow_type"] == flow_type) 
    ]                                       
    
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        sim_id = sim.id
        sim_F_m3s = _get_flow(sim, flow_type, start, end)
        
        ## 2.1 Statistics
        F_residuals = obs_F_m3s - sim_F_m3s
        F_deviation = obs_F_m3s - np.mean(obs_F_m3s)
        
        ## 2.2 Performance Indices
        ME = np.mean(F_residuals)        
        RMSE = np.sqrt(np.mean(F_residuals ** 2))
        NSE = 1 - ( np.mean(F_residuals ** 2) / np.mean(F_deviation ** 2))
        
        ## 3 Plot
        plot_flow_timeseries(obs_F_m3s = obs_F_m3s, sim_F_m3s = sim_F_m3s, 
                             years_per_figure = 3, 
                             flow_type = flow_type, obs_label = _get_obs_label(flow_type), 
                             catchment = catchment, sim_id = sim_id, period_id = period_id, 
                             output_path = directories.statistics[flow_type], 
                             show_statistics = True,
                             ME = ME, RMSE = RMSE, NSE = NSE)

def evaluate_waterbalance(catchment, period_id, start, end, flow_type, directories):
    """Evaluate overall model performance using water balance deficit and the cumulative plot as evaluation target.
    
    Parameters
    ----------
    catchment : str
        Catchment name associated with the simulation to be evaluated.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    period_id : str
        Unique identifier for the simulated period to evaluate.
        must match entry in evaluation/config_periods.xlsx (sheet: simulation_periods).
    start, end : pandas.TimeStamp
        Start and end of period where simulation is evaluated.
    directories : Directories
        Object containing paths for input data and output plots, used here via
        directories.obs, directories.sim, directories.waterbalance.

    Returns
    -------
    None.

    """
    ## 1 Observation
    obs_row = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs    = Observation(obs_row, directories.obs)
    
    obs_F_m3s = _get_flow(obs, flow_type, start, end)
    
    if flow_type == "QF":
        obs_F_freq = obs.QF_freq
    elif flow_type == "BF":
        obs_F_freq = obs.BF_freq
    elif flow_type == "TF":
        obs_F_freq = obs.QF_freq
    obs_F_mmdt = _convert_rate_to_depth(obs_F_m3s, obs.catchment_size, obs_F_freq)
    obs_F_wb = obs_F_mmdt.cumsum()
    
    ## 2 Simulation
    sim_F_wb_dict = {}
    
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &            
        (config_sim["period_id"] == period_id) &            
        (config_sim["stage"] == "overall") &
        (config_sim["evaluation_method"] == "waterbalance") & 
        (config_sim["flow_type"] == flow_type) 
    ]                                       
    
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        sim_id = sim.id
        
        sim_F_m3s = _get_flow(sim, flow_type, start, end)
        sim_F_freq = pd.infer_freq(sim_F_m3s.index)
        sim_F_mmdt = _convert_rate_to_depth(sim_F_m3s, obs.catchment_size, sim_F_freq)
        sim_F_wb = sim_F_mmdt.cumsum()

        sim_F_wb_dict[sim_id] = sim_F_wb
        
        # deficit = (sim - obs) / obs
        wb_deficit = float((sim_F_wb.iloc[-1] - obs_F_wb.iloc[-1]) / obs_F_wb.iloc[-1] * 100) 
    
    ## 3 Plot     
    plot_flow_waterbalance(obs_F_wb = obs_F_wb, 
                           sim_F_wb_dict = sim_F_wb_dict, 
                           wb_deficit = wb_deficit, 
                           flow_type = flow_type, obs_label = _get_obs_label(flow_type), 
                           catchment = catchment, sim_id = sim_id, period_id = period_id, 
                           output_path = directories.waterbalance[flow_type])
