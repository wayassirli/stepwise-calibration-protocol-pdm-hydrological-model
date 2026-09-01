# -*- coding: utf-8 -*-
""" 

Created on Tue Mar  3 12:35:24 2026
@author: Way
"""

import pandas as pd
import numpy as np
from observation import Observation
from simulation import Simulation
from plot import plotET_ActualvsPotential, plotET_ratio, plotET_soilwatervariation
from plot import plotsoil_evaluation, plotsoil_report
from plot import plotrunoff_evaluation, plotrunoff_report
from plot import plotflow_timeseries, plotflow_waterbalance

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
    flowrate : pandas.Series
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

def _extract_peak_values(flow_periods, df_obs, df_sim):
    """Extract the peak (maximum) observed value and the simulated value at that timestamp, for each flow period block. 

    Parameters
    ----------
    flowperiods : list of tuples (int, int)
        (start, end) pairs returned by _slowflowperiod or _quickflowperiod
    df_obs, df_sim : pandas.Series
        Observed and simulated time-series from which the peak value is extracted from

    Returns
    -------
    df : pandas.DataFrame
        Columns: peak_time, obs_peak, sim_peak - one row per each flow period block.
    """
    
    result = [] 
    
    for start, end in flow_periods:
        obs_period = df_obs.iloc[start:end+1] # .iloc[] is a method for integers (datatype of start, end)
        peak_time  = obs_period.idxmax()      # in pandas.Timestamp format
        obs_peak   = obs_period.max()

        sim_peak = df_sim.loc[peak_time]      # .loc[] is a method for pandas.Timestamp or pandas.Datetime (dataype of peak_time)
        
        result.append({
            "peak_time": peak_time,
            "obs_peak": obs_peak,
            "sim_peak": sim_peak
            })

    df = pd.DataFrame(result)
    return df
        
def _extract_low_values(flow_periods, df_obs, df_sim):
    """ Extract the observed and simulated value at the end of each flow period block (the smallest value/low point). 

    Parameters
    ----------
    flowperiods : list of tuples (int, int)
        (start, end) pairs returned by _slowflowperiod or _quickflowperiod
    df_obs, df_sim : pandas.Series
        Observed and simulated time-series from which the peak value is extracted from

    Returns
    -------
    df : pandas.DataFrame
        Columns: low_time, obs_low, sim_low - one row per each flow period block.
    """
    result = []
    
    for start, end in flow_periods:
        
        low_time = df_obs.index[end]   # in pandas.Timestamp format
        obs_low = df_obs.iloc[end]
        sim_low = df_sim.iloc[end]
        
        result.append({
            "low_time": low_time,
            "obs_low": obs_low,
            "sim_low": sim_low
            })

    df = pd.DataFrame(result)
    return df

def _calculate_volume_values(flow_periods, df_obs, df_sim):
    """Calculate the accumulated volume of simulated and observed time-series for each flow period block,
    along with the midpoint timestamp for plotting    

    Parameters
    ----------
    flowperiods : list of tuples (int, int)
        (start, end) pairs returned by _slowflowperiod or _quickflowperiod
    df_obs, df_sim : pandas.Series
        Observed and simulated time-series from which the accumulated value is calculated from

    Returns
    -------
    df : pandas.DataFrame
        Columns: mid_flowperiod, obs_volume, sim_volume - one row per each flow period block.
    """
    result = []
    
    for start, end in flow_periods:
        
        obs_volume = df_obs.iloc[start:end+1].sum() # end+1 because .iloc[] slicing excludes the end value
        sim_volume = df_sim.iloc[start:end+1].sum()
        
        # midpoint is used as the x-coordinate (midpoint of each flow period block) when plotting the volume on the graph 
        midpoint = int(start + (end - start) / 2) # int() because midpoint value requires integer and division can produce float
        position = df_obs.index[midpoint]
        
        result.append({
            "mid_flowperiod": position,
            "obs_volume": obs_volume,
            "sim_volume": sim_volume
            })
        
    df = pd.DataFrame(result)
    return df

def _transform_boxcox(df_obs, df_sim, λ):
    """ Apply a Box-cox transformation to the observed and simulated data.
    
    Parameters
    ----------
    df_obs, df_sim: pandas.DataFrame
        Observed and simulated data to transform.
    λ : float
        Box-cox transformation parameter. Value ranges between 0 to 1 and must not be 0

    Returns
    -------
    BC_obs_df, BC_sim_df : pandas.DataFrame
        Box-cox transformed observed and simulated data.
    """
    BC_obs_df = ((df_obs ** λ) - 1) / λ
    BC_sim_df = ((df_sim ** λ) - 1) / λ
    
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
    """Evaluate simulated flow recession behavior against WETSPRO-filtered flow
    
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
        Generate recession plots, and does not return a value
    """
    # 1 Observation
    obs_row = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs    = Observation(obs_row, directories.obs)
    obs_F_m3s = _get_flow(obs, flow_type, start, end)
    
    # 2 Simulation
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &            # passed in from main.py's command line argument
        (config_sim["period_id"] == period_id) &            # idem
        (config_sim["stage"] == "submodel") &               
        (config_sim["calibration_target"] == "recession") & 
        (config_sim["flow_type"] == flow_type)              # When flow_type is not specified as argument in the command-line->
    ]                                                       # -> functions are looped for all flowtypes (hard-coded) in main.py 
         
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        sim_name = sim.name
        sim_F_m3s = _get_flow(sim, flow_type, start, end)
        
        obs_label = _get_obs_label(flow_type)
        
        plotflow_timeseries(obs_F_m3s = obs_F_m3s, 
                            sim_F_m3s = sim_F_m3s, 
                            obslabel = obs_label,
                            years_per_figure=3,
                            flowtype=flow_type, 
                            catchment = catchment, simname = sim_name, period_id = period_id, 
                            plotflow_timeseries_path = directories.recession[flow_type],
                            plot_statistics=False)

def evaluate_eta(catchment, period_id, start, end, directories):
    """Evaluate 
    
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
    directories : TYPE
    Directories
        Object containing paths for input data and output plots, used here via
        directories.obs, directories.sim, and directories.ET.

    Returns
    -------
    None
        Generate three ET-related plots, and does not return a value
    
    Notes
    -----
    smd = Soil Moisture Deficit (no unit, value range: 0 < smd < 1)
    SWd = Soil Water Depth (unit: mm, 0 < SWd < Smax)
    """
    ETa_dict = {}
    ET_ratio_dict    = {}
    SWd_dict  = {}
    
    # 1 Observation
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
    
    # 2 Simulation 
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &     # passed in from main.py's command line argument
        (config_sim["period_id"] == period_id) &     # idem
        (config_sim["stage"] == "submodel") &
        (config_sim["calibration_target"] == "ETa")
    ]
    
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        sim_id = sim.parameters["ET_params1"]        # ET exponent is used as scenario identifier 
        
        # 2.1 ETa
        sim_smd = sim.smd.loc[start:end]
        sim_ETa_mmday   = sim.ETa_mmday.loc[start:end]
        sim_ETa_mmmonth = sim_ETa_mmday.resample("M").sum()
        ETa_dict[sim_id] = sim_ETa_mmmonth      
        
        # 2.2 Actual to Potential Evapotranspiration Ratio (ET ratio)
        ET_ratio = sim_ETa_mmmonth / obs_ETp_mmmonth
        ET_ratio_dict[sim_id] = ET_ratio
        
        # 2.3 Soil Water Depth (SWd) Variation
        soil_function = sim.parameters["soil_function"]
        if soil_function == "pareto":        
            Smax = _calculate_smax_pareto(sim.parameters["soil_params1"], sim.parameters["soil_params2"], sim.parameters["soil_params3"])
        elif soil_function == "rectangular":
            Smax = _calculate_smax_rectangular(sim.parameters["soil_params1"], sim.parameters["soil_params2"])
        elif soil_function == "triangular":
            Smax = _calculate_smax_triangular(sim.parameters["soil_params1"], sim.parameters["soil_params2"])
        smd_initial = sim_smd.loc[start:end].iloc[0]
        SWd_initial = Smax * (1-smd_initial)
        SWd = SWd_initial + (obs_P_mmmonth - obs_Q_mmmonth - sim_ETa_mmmonth).cumsum()
        SWd_dict[sim_id] = SWd
    
    plotET_ActualvsPotential(obs_ETp_mmmonth, ETa_dict, obs.catchment, period_id, directories.ET)
    plotET_ratio(ET_ratio_dict, obs.catchment, start, end, period_id, directories.ET)
    plotET_soilwatervariation(SWd_dict, obs.catchment, start, end, period_id, directories.ET)

def evaluate_soil(catchment, period_id, start, end, directories):
    
    # 1 Observation
    obs_row = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs     = Observation(obs_row, directories.obs)
    
    obs_P_mmdt = obs.P_mmdt.loc[start:end]    
    obs_Q_m3s  = obs.Q_m3s.loc[start:end]     
  
    obs_Q_mmdt = _convert_rate_to_depth(obs_Q_m3s, obs.catchment_size, obs.Q_freq) 
    
    obs_P_mmhr       = obs_P_mmdt.resample("H").sum()          # for soil water variation
    obs_Q_mmhr       = obs_Q_mmdt.resample("H").sum()  # for soil water variation
    obs_PminQ_mmhr   = obs_P_mmhr - obs_Q_mmhr
    
    # 2 Simulation 
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &
        (config_sim["period_id"] == period_id) &
        (config_sim["stage"] == "submodel") &
        (config_sim["calibration_target"] == "soil") 
    ]
    
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        
        sim_name = sim.name
        sim_λSWd = sim.λSWd
        sim_ETa_mmhr = sim.ETa_mmday.loc[start:end] / 24
        sim_smd = sim.smd.loc[start:end]
        
        # 2.1 Observed Soil Water Depth (SWd) Variation
        soil_function = sim.parameters["soil_function"]
        if soil_function == "pareto":        
            Smax = _calculate_smax_pareto(sim.parameters["soil_params1"], sim.parameters["soil_params2"], sim.parameters["soil_params3"])
        elif soil_function == "rectangular":
            Smax = _calculate_smax_rectangular(sim.parameters["soil_params1"], sim.parameters["soil_params2"])
        elif soil_function == "triangular":
            Smax = _calculate_smax_triangular(sim.parameters["soil_params1"], sim.parameters["soil_params2"])
        
        smd_initial = sim_smd.iloc[0]
        SWd_initial = Smax * (1-smd_initial)
        obs_SWd = SWd_initial + (obs_P_mmhr - obs_Q_mmhr - sim_ETa_mmhr).cumsum()
        
        # 2.2 Simulated Soil Water Depth (SWd) Variation
        sim_SWd = Smax * (1-sim_smd)
        
        # 2.3 Event-based (Slow Flow Event) SWd Values
        slowflow_periods = _get_slowflow_periods(catchment, period_id, obs_PminQ_mmhr) # use any related timeseries to count index
        SWd_peaks = _extract_peak_values(slowflow_periods, obs_SWd, sim_SWd)
        SWd_lows  = _extract_low_values(slowflow_periods, obs_SWd, sim_SWd)
        
        # 2.4 Box-cox Transformed, Event-based SWd Values
        BC_obs_SWd_peak, BC_sim_SWd_peak = _transform_boxcox(SWd_peaks["obs_peak"], SWd_peaks["sim_peak"], sim_λSWd)
        SWd_peaks["BC_obs_peak"] = BC_obs_SWd_peak
        SWd_peaks["BC_sim_peak"] = BC_sim_SWd_peak
        
        BC_obs_SWd_low, BC_sim_SWd_low = _transform_boxcox(SWd_lows["obs_low"], SWd_lows["sim_low"], sim_λSWd)
        SWd_lows["BC_obs_low"] = BC_obs_SWd_low
        SWd_lows["BC_sim_low"] = BC_sim_SWd_low
        
        # 2.5 RMSE
        SWd_peaks["residuals"] = SWd_peaks["BC_obs_peak"] - SWd_peaks["BC_sim_peak"]
        RMSE_peaks = np.sqrt( np.mean(SWd_peaks["residuals"] ** 2) )
        
        SWd_lows["residuals"] = SWd_lows["BC_obs_low"] - SWd_lows["BC_sim_low"]
        RMSE_lows = np.sqrt( np.mean(SWd_lows["residuals"] ** 2) )
        
        plotsoil_evaluation(obs_SWd, sim_SWd, 
                            slowflow_periods, 
                            catchment, sim_name, period_id, 
                            SWd_peaks, SWd_lows, 
                            sim_λSWd, RMSE_peaks, RMSE_lows, directories.soil['evaluation'])
        
        plotsoil_report(obs_SWd = obs_SWd, sim_SWd = sim_SWd, 
                        slowflowperiods = slowflow_periods, 
                        catchment = catchment, simname =  sim_name, period_id = period_id, 
                        SWd_peaks = SWd_peaks, SWd_lows = SWd_lows,  
                        λ = sim_λSWd, RMSE_peaks = RMSE_peaks, RMSE_lows = RMSE_lows, 
                        plotsoil_timeseries_path = directories.soil['timeseries'], plotsoil_boxcox_path = directories.soil['boxcox'])

def evaluate_runoff(catchment, period_id, start, end, directories):
    
    # 1 Observation
    obs_row = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs     = Observation(obs_row, directories.obs)

    obs_QF_m3s  = obs.QF_m3s.loc[start:end]
    obs_QF_mmdt = _convert_rate_to_depth(obs_QF_m3s, obs.catchment_size, obs.QF_freq)    
    
    # 2 Simulation
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &
        (config_sim["period_id"] == period_id) &
        (config_sim["stage"] == "submodel") &
        (config_sim["calibration_target"] == "runoff") 
    ]    
    
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        sim_name = sim.name
        
        sim_λQF = sim.λQF
        sim_QF_m3s = sim.QF_m3s.loc[start:end]
        sim_QF_freq = pd.infer_freq(sim_QF_m3s.index)
        sim_QF_mmdt = _convert_rate_to_depth(sim_QF_m3s, obs.catchment_size, sim_QF_freq)
        
        # Event-based (quick flow event) Accumulated Runoff Volume
        quickflow_periods = _get_quickflow_periods(catchment, period_id, obs_QF_m3s) # use any timeseries to count index
        QF_volume = _calculate_volume_values(quickflow_periods, obs_QF_mmdt, sim_QF_mmdt)
        
        BC_obs_QF_vol, BC_sim_QF_vol = _transform_boxcox(QF_volume["obs_volume"], QF_volume["sim_volume"], sim_λQF)
        QF_volume["BC_obs_volume"] = BC_obs_QF_vol
        QF_volume["BC_sim_volume"] = BC_sim_QF_vol
        
        QF_volume["residuals"] = QF_volume["BC_obs_volume"] - QF_volume["BC_sim_volume"]
        RMSE_volume = np.sqrt( np.mean(QF_volume["residuals"] ** 2) )
                        
        plotrunoff_evaluation(obs_QF_mmdt = obs_QF_mmdt , 
                              sim_QF_mmdt = sim_QF_mmdt, 
                              quickflowperiods = quickflow_periods, 
                              catchment = catchment, simname = sim_name, period_id = period_id, 
                              QF_volume = QF_volume, residuals = QF_volume["residuals"], 
                              λ = sim_λQF, RMSE_volume = RMSE_volume, 
                              plotrunoff_evaluation_path = directories.runoff['evaluation'])
        
        plotrunoff_report(obs_QF_mmdt = obs_QF_mmdt , 
                              sim_QF_mmdt = sim_QF_mmdt, 
                              quickflowperiods = quickflow_periods, 
                              catchment = catchment, simname = sim_name, period_id = period_id, 
                              QF_volume = QF_volume, residuals = QF_volume["residuals"], 
                              λ = sim_λQF, RMSE_volume = RMSE_volume, 
                              plotrunoff_timeseries_path = directories.runoff['timeseries'], plotrunoff_boxcox_path = directories.runoff['boxcox'])

def evaluate_statistics(catchment, period_id, start, end, flow_type, directories):

    # 1 Observation
    obs_row   = config_obs[config_obs["catchment"] == catchment].iloc[0]
    obs       = Observation(obs_row, directories.obs)
    obs_F_m3s = _get_flow(obs, flow_type, start, end)
    
    # 2 Simulation
    sim_rows = config_sim[
        (config_sim["catchment"] == catchment) &            
        (config_sim["period_id"] == period_id) &            
        (config_sim["stage"] == "overall") &
        (config_sim["evaluation_method"] == "timeseries") & 
        (config_sim["flow_type"] == flow_type) 
    ]                                       
    
    for _, sim_row in sim_rows.iterrows():
        sim = Simulation(sim_row, directories.sim)
        sim_name = sim.name
        sim_F_m3s = _get_flow(sim, flow_type, start, end)
        
        F_residuals = obs_F_m3s - sim_F_m3s
        F_deviation = obs_F_m3s - np.mean(obs_F_m3s)

        ME = np.mean(F_residuals)        
        RMSE = np.sqrt(np.mean(F_residuals ** 2))
        NSE = 1 - ( np.mean(F_residuals ** 2) / np.mean(F_deviation ** 2))
        
        obs_label = _get_obs_label(flow_type)
        
        # Plot function inside the loop, 1 plot per simulation.
        plotflow_timeseries(obs_F_m3s = obs_F_m3s, 
                            sim_F_m3s = sim_F_m3s, 
                            obslabel = obs_label,
                            years_per_figure=3,
                            flowtype=flow_type, 
                            catchment = catchment, simname = sim_name, period_id = period_id, 
                            plotflow_timeseries_path = directories.statistics[flow_type],
                            plot_statistics=True,
                            ME = ME, RMSE = RMSE, NSE = NSE,)

def evaluate_waterbalance(catchment, period_id, start, end, flow_type, directories):
    
    # 1 Observation
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
    
    # 2 Simulation
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
        sim_name = sim.name 
        
        sim_F_m3s = _get_flow(sim, flow_type, start, end)
        sim_F_freq = pd.infer_freq(sim_F_m3s.index)
        sim_F_mmdt = _convert_rate_to_depth(sim_F_m3s, obs.catchment_size, sim_F_freq)
        sim_F_wb = sim_F_mmdt.cumsum()

        sim_F_wb_dict[sim_name] = sim_F_wb
        
        # deficit = (sim - obs) / obs
        wb_deficit = float((sim_F_wb.iloc[-1] - obs_F_wb.iloc[-1]) / obs_F_wb.iloc[-1] * 100) 
    
    obs_label = _get_obs_label(flow_type)
    
    # Plot function outside the loop, 1 plot for all simulations.
    plotflow_waterbalance(obs_F_wb = obs_F_wb, 
                          sim_F_wb_dict = sim_F_wb_dict, 
                          obslabel = obs_label, 
                          wb_deficit = wb_deficit, 
                          flowtype = flow_type, 
                          catchment = catchment, 
                          simname = sim_name, 
                          period_id = period_id, 
                          plotflow_waterbalance_path = directories.waterbalance[flow_type])
