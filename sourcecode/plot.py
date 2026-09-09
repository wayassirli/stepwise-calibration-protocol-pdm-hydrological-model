# -*- coding: utf-8 -*-
"""Plotting functions for calibration/evaluation output

Multiple simulations, 1 plot:
  - ETa vs ETp, ET ratio, soil water variation (5 years)
  - Water balance for all flowtype (Full time-series)
1 Simulation, 1 Plot:
  - Soil water variation (5 years)
  - Runoff (5 years)
  - Time-series for all flowtype (1 year)

Created on Sat Apr  4 10:35:09 2026
@author: Way
"""
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

#%% Helper function

def _plot_seasonal_blocks(start, end):
    """Add seasonal boundaries (lines) and labels to the time-series plot.
    
    Parameters
    ----------
    start, end : pandas.Timestamp
        The start and end of time-series where the seasonal blocks is added

    Returns
    -------
    None.
        The function returns seasonal boundaries in time-series plots
        
    Notes
    -----
    QS-DEC generates quarterly timestamps for seasonal boundaries starting in December.
    Seasonal labels are assigned according to the seasonal boundary month:
        December = DJF (Winter), March = MAM (Spring), June = JJA (Summer), September = SON (Fall)
    """
    
    seasonal_boundaries = pd.date_range(start=start, end=end, freq="QS-DEC")
    seasonal_labels = {12: "DJF", 3: "MAM", 6: "JJA", 9: "SON"}

    for date in seasonal_boundaries:
        plt.axvline(date, color="black", linestyle=":", linewidth=2, alpha=0.3)
    
    # Position the seasonal label at the top of the y-axis
    y_offset = plt.ylim()[1]
    
    for i in range(len(seasonal_boundaries)-1):
        # Position the seasonal label midway between consecutive seasonal boundaries (x-axis)
        midpoint = seasonal_boundaries[i] + (seasonal_boundaries[i+1] - seasonal_boundaries[i]) / 2
        
        season = seasonal_labels[seasonal_boundaries[i].month]
        plt.text(midpoint, y_offset, season, ha="center", va="top")

def _plot_flow_periods_lines(ax, obs, flow_periods):
    """Add flow period boundaries (lines) to the time-series plot

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes on which the flow period are plotted.
    obs : pandas.Series
        The time.
    flow_periods : list of tuple (int, int)
        Start and end integer of the flow period blocks.

    Returns
    -------
    None.
        The function returns flow period lines in time-series plots
    """
    
    date_flow_periods = [ (obs.index[start] , obs.index[end]) for start, end in flow_periods]
    
    for start, end in date_flow_periods:
        ax.axvline(end, color="lightskyblue", linestyle="--", alpha=0.8)
    
    # Add the first flow period line at the start of the time-series and use it as legend entry
    ax.axvline(date_flow_periods[0][0], color="lightskyblue", linestyle="--", label="Flow Periods")
    
def _calculate_deviation_lines(BC_obs, residuals):
    """Calculate standard deviation bands and mean deviation line for Box-cox plot.

    Parameters
    ----------
    BC_obs : pandas.Series
        Box-cox transformed observed values.
    residuals : pandas.Series
        Residuals between observed and simulated Box-cox transformed values.

    Raises
    ------
    ValueError
        When two flow periods derived, only two event-based observed values (i.e. peak, low, accumulated volume) are extracted.
        Therefore, not enough points to interpolate the standard deviation bands

    Returns
    -------
    df_deviation_bands : pandas.DataFrame
        One row per averaged point, with columns:
        average_obs = the sim=obs (x=y) diagonal line, used as the x-coordinate for standard deviation bands and mean deviation line
        local_upper_dev, local_lower_dev = the y-coordinate used for fitting linear equation of standard deviation band's line
    upper_band_coefs, lower_band_coefs : numpy.ndarray.
        The coefficients of the linear equation fitted from the local_upper_dev and local_lower_dev. (i.e. a, b in y = ax + b)        
    mean_residuals : float
        Global averaged residual value, used to offset the sim=obs diagonal line
        to plot the mean deviation line and represent the systematic bias
    """
    
    average_obs = BC_obs.rolling(window=2).mean()      
    mean_residuals = residuals.mean()
    local_stdev   = residuals.rolling(window=2).std()

    local_upper_deviation = average_obs + mean_residuals + local_stdev   
    local_lower_deviation = average_obs + mean_residuals - local_stdev   
    
    df_deviation_bands = pd.DataFrame({
        "average_obs"       : average_obs,
        "local_upper_dev"   : local_upper_deviation,
        "local_lower_dev"   : local_lower_deviation
    }).dropna() # used to drop the NaN values in the first row left by rolling calculation
    
    if len(df_deviation_bands) < 2:
        raise ValueError(
            f"Not enough points for standard deviation band's line interpolation. "
            f"Found {len(df_deviation_bands)} points."
        )
    
    upper_band_coefs = np.polyfit(df_deviation_bands["average_obs"], df_deviation_bands["local_upper_dev"], 1)
    lower_band_coefs = np.polyfit(df_deviation_bands["average_obs"], df_deviation_bands["local_lower_dev"], 1)
    
    return df_deviation_bands, upper_band_coefs, lower_band_coefs, mean_residuals

def _plot_boxcox(ax, BC_obs, BC_sim, residuals, title, x_label, y_label, color): 
    """Generate plot of box-cox transformed observed and simulated variables
    
    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes on which the Box-Cox plot is plotted.
    BC_obs, BC_sim, residuals : pandas.Series
        Box-cox transformed observed, simulated values (i.e. flow, soil water depth) and residuals .
    title, x_label, y_label : str
        Plot title, x-axis label, and y-axis label.
    color : str
        Color used for the plotted data.

    Returns
    -------
    None.
        The function returns Box-cox plot
    """    
    
    df_deviation_bands, upper_band_coefs, lower_band_coefs, mean_residuals = _calculate_deviation_lines(BC_obs, residuals)
    
    # Use the overall minimum and maximum values for both axes to create a square plot
    axis_min = min(BC_obs.min(), BC_sim.min(), df_deviation_bands["local_lower_dev"].min()) - 2 
    axis_max = max(BC_obs.max(), BC_sim.max(), df_deviation_bands["local_upper_dev"].max()) + 2
    
    # Coordinates calculation
    x_coordinates = np.linspace(axis_min, axis_max, 100)
    y_upper_deviation_bands = np.polyval(upper_band_coefs, x_coordinates)
    y_lower_deviation_bands = np.polyval(lower_band_coefs, x_coordinates)
    y_systematic_bias = x_coordinates + mean_residuals
    
    ## 1 Plot BC_obs and BC_sim values
    ax.scatter(BC_obs, BC_sim, color=color, label="Obs vs Sim")
    
    ## 2 Plot bisector line
    # Draws diagonal line from (axis_min, axis_min) to (axis_max, axis_max)
    ax.plot([axis_min, axis_max], [axis_min, axis_max], color="black", linestyle="-", linewidth=1, label="Bisector")
    
    ## 3 Plot standard deviation bands
    ax.plot(x_coordinates, y_upper_deviation_bands, color="black", linestyle="--", linewidth=2, label="Standard Deviation")
    ax.plot(x_coordinates, y_lower_deviation_bands, color="black", linestyle="--", linewidth=2)
    
    ## 4 Plot residuals/error/mean deviation line
    ax.plot(x_coordinates, y_systematic_bias, color="black", linestyle="-", linewidth=2, label="Mean Deviation")

    ## 5 Format plot
    ax.set_xlim(axis_min, axis_max)
    ax.set_ylim(axis_min, axis_max)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(x_label, fontsize=14)
    ax.set_ylabel(y_label, fontsize=14)
    ax.set_title(title, fontsize=14)
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
    ax.tick_params(axis="both", labelsize=14)
    ax.legend(fontsize=14)

#%% Plot ET

def plot_et_actual_vs_potential(ETp_series, ETa_dict, catchment, period_id, output_path):
    """Plot multiple simulated actual evapotranspiration time-series against the potential rate time-series, and save to file.

    Parameters
    ----------
    ETp_series : pandas.Series
        Potential evapotranspiration time-series.
    ETa_dict : dictionary of pandas.Series
        Simulated actual evapotranspiration time-series, keyed by ET exponent (b_e).
    catchment : str
        Catchment name, used in the plot title and filename.
    period_id : str
        Unique identifier for simulation period to be plotted.
    output_path : str
        Folder to save the resulting plot to.

    Returns
    -------
    None.
        Saves the plot as a PNG file to output_path.
    """
    plt.figure(figsize=(12,6))
    
    ## 1 Plot ETp
    plt.plot(ETp_series.index, ETp_series.values, label="ETp", color="orange", linewidth=2)
    
    ## 2 Plot ETa
    for sim_id in sorted(ETa_dict):
        ETa_series = ETa_dict[sim_id]
        plt.plot(ETa_series.index, ETa_series.values, label = f"ETa $b_{{e}}$ = {sim_id}")
    
    # 3 Format plot
    plt.xlabel('Month', fontsize=16)
    plt.ylabel('ET (mm/day)', fontsize=16)
    plt.title(f'ETa vs ETp for Different $b_{{e}}$ Values\n{catchment} {period_id}', fontsize=16)
    plt.tick_params(axis='both', labelsize=16)
    plt.legend(fontsize=16)
    plt.tight_layout()
    
    ## 4 Save plot
    filename = f"{catchment} ETa vs ETp {period_id}.png"
    filepath = os.path.join(output_path, filename)
    plt.savefig(filepath, dpi=300)
    plt.close()

def plot_et_ratio(ET_ratio_dict, catchment, start, end, period_id, output_path):
    """Plot multiple time-series of ratio between actual and potential evapotranspiration (ETa/ETp), and save to file.

    Parameters
    ----------
    ET_ratio_dict : dictionary of pandas.Series
        ET ratio time-series, keyed ET exponent (b_e).
    catchment : str
        Catchment name, used in the plot title and filename.
    start, end : pandas.Timestamp
        The start and end of time-series where the seasonal blocks is added.
    period_id : str
        Unique identifier for simulation period to be plotted.
    output_path : str
        Folder to save the resulting plot to.
        
    Returns
    -------
    None.
        Saves the plot as a PNG file to output_path.
    """
    plt.figure(figsize=(12,6))
    
    ## 1 Plot ET ratio
    for sim_id in sorted(ET_ratio_dict):
        ET_ratio_series = ET_ratio_dict[sim_id]
        plt.plot(ET_ratio_series.index, ET_ratio_series.values, 
                 marker="o", linestyle='-', linewidth = 2, label = f"ETa $b_{{e}}$ = {sim_id}")
    
    ## 2 Plot seasonal blocks
    _plot_seasonal_blocks(start, end)
    
    ## 3 Format plot
    plt.xlabel('Month', fontsize=15)
    plt.ylabel('ETa / ETp', fontsize=15)
    plt.title(f"ET ratio for Different $b_{{e}}$ Values\n{catchment} {period_id}", fontsize=15)
    plt.tick_params(labelsize=15)
    plt.legend(fontsize=15)
    plt.tight_layout()
    
    ## 4 Save plot
    filename = f"{catchment} ET ratio {period_id}.png"
    filepath = os.path.join(output_path, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    
def plot_soil_water_depth_multi(SWd_dict, catchment, start, end, period_id, output_path):
    """Plot multiple simulated soil water depth time-series against the observed one, and save to file.

    Parameters
    ----------
    SWd_dict : dictionary of pandas.Series
        Soil water depth time-series, keyed by ET exponent (b_e).
    catchment : str
        Catchment name, used in the plot title and filename.
    start, end : pandas.Timestamp
        The start and end of time-series where the seasonal blocks is added.
    period_id : str
        Unique identifier for simulation period to be plotted.
    output_path : TYPE
        Folder to save the resulting plot to.

    Returns
    -------
    None.
        Saves the plot as a PNG file to output_path.
    """
    
    plt.figure(figsize=(12,6))
    
    ## 1 Plot soil water depth time-series
    for sim_id in sorted(SWd_dict):
        SWd_series = SWd_dict[sim_id]
        plt.plot(SWd_series.index, SWd_series.values, 
                 marker="o", linestyle='-', linewidth = 2, label = f"ETa $b_{{e}}$ = {sim_id}")

    ## 2 Plot seasonal blocks
    _plot_seasonal_blocks(start, end)

    ## 3 Format plot
    plt.xlabel('Month', fontsize=14)
    plt.ylabel('Soil Storage (mm)', fontsize=14)    
    plt.title(f'Soil Water Variation for Different $b_{{e}}$ Values\n{catchment} {period_id}', fontsize=14)
    plt.tick_params(labelsize=14)
    plt.legend(fontsize=14)
    plt.tight_layout()

    ## 4 Save plot
    filename = f"{catchment} Soil water variation {period_id}.png"
    filepath = os.path.join(output_path, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()

#%% Plot Soil

def plot_soil_water_depth_single(ax, obs_SWd, sim_SWd, SWd_maxima, SWd_minima, flow_periods, catchment, sim_id, period_id):                         
    """Plot soil water depth time-series of a single simulation.
    
    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes on which the soil water depth is plotted into (a subplot of a larger figure).
    obs_SWd, sim_SWd : pandas.Series
        Observed and simulated soil water depth time-series.
    SWd_maxima, SWd_minima: pandas.DataFrame
        Extracted maximum and minimum soil water depth values, and their timestamp.
    flow_periods : list of tuple (int, int)
        Start and end integer of the flow period blocks.
    catchment : str
        Catchment name, used in the plot title and filename.
    sim_id : str
        Simulation idenifier, used in the plot title and filename.
    period_id : str
        Unique identifier for simulation period to be plotted.

    Returns
    -------
    None.
        The function returns the plot into the given axis
    """
    
    ## 1 Plot soil water depth time-series
    ax.plot(sim_SWd.index, sim_SWd.values, color="green", label="Simulated")
    ax.plot(obs_SWd.index, obs_SWd.values, color="black", label="Observed")
    
    ## 2 Plot maximum and minimum values of soil water depth per each flow period block
    ax.scatter(SWd_maxima["max_timestamp"], SWd_maxima["obs"], color="blue", s=12, zorder=3, label="Wet Soil Storage")
    ax.scatter(SWd_maxima["max_timestamp"], SWd_maxima["sim"], color="blue", s=12, zorder=3)
    ax.scatter(SWd_minima["min_timestamp"], SWd_maxima["obs"], color="red",  s=12, zorder=3, label="Dry Soil Storage")
    ax.scatter(SWd_minima["min_timestamp"], SWd_maxima["sim"], color="red",  s=12, zorder=3)

    ## 3 Plot slow flow periods
    _plot_flow_periods_lines(ax, obs_SWd, flow_periods)
    
    ## 4 Format plot
    ax.set_xlabel('Date', fontsize=14)
    ax.set_ylabel('Soil Water Depth [mm]', fontsize=14)
    ax.set_title(f"Soil Water Depth Variation\n{catchment} {sim_id} {period_id}", fontsize=14)
    ax.tick_params(axis="both", labelsize=14)
    ax.legend(fontsize=14)

def plot_soil_evaluation(obs_SWd, sim_SWd, flow_periods, SWd_maxima, SWd_minima, λ, RMSE_maxima, RMSE_minima, 
                         catchment, sim_id, period_id, output_path):                  
    """Save plot to file, containing two subplots of soil water depth time-series and box-cox side-by-side for individual simulation. 

    Parameters
    ----------
    obs_SWd, sim_SWd : pandas.Series
        Observed and simulated soil water depth time-series.
    flow_periods : list of tuple (int, int)
        Start and end integer of the flow period blocks.
    SWd_maxima, SWd_minima: pandas.DataFrame
        Extracted maximum and minimum soil water depth values, and their timestamp.
    λ : float
        Box-cox transformation parameter, shown in the subplot titles.
    RMSE_maxima, RMSE_minima : float
        RMSE of the Box-cox transformed maximum and minimum values, shown in the subplot titles.
    catchment : str
        Catchment name, used in the plot title and filename.
    sim_id : str
        Simulation idenifier, used in the plot title and filename.
    period_id : str
        Unique identifier for simulation period to be plotted.
    output_path : str
        Folder to save the resulting plot to.

    Returns
    -------
    None.
        Saves the plot as a PNG file to output_path.
    """
    
    # Box-cox plot title
    title_peaks = f"Box-Cox Transformed Wet Soil Storage\nλ = {λ}, BC( RMSE = {RMSE_maxima:.2f} mm )"
    x_label_peaks = "BC( Observed Wet Soil Storage, St [mm] )"
    y_label_peaks = "BC( Simulated Wet Soil Storage, St [mm] )"
    title_lows  = f"Box-Cox Transformed Dry Soil Storage\nλ = {λ}, BC( RMSE = {RMSE_minima:.2f} mm )"
    x_label_lows  = "BC( Observed Dry Soil Storage, St [mm] )"
    y_label_lows  = "BC( Simulated Dry Soil Storage, St [mm] )"
    
    ## 2 Plot layout
    fig = plt.figure(figsize=(12, 12))
    grid  = gridspec.GridSpec(2, 2, height_ratios=[1.5, 2])

    ax1 = fig.add_subplot(grid[0, :]) # Soil water depth time-series (Top)
    ax2 = fig.add_subplot(grid[1, 0]) # Box-cox, wet soil storage per flow period block (Bottom left)
    ax3 = fig.add_subplot(grid[1, 1]) # Box-cox, dry soil storage per flow period block (Bottom right)
    
    ## 3 Plot soil water depth
    plot_soil_water_depth_single(ax1, obs_SWd, sim_SWd, SWd_maxima, SWd_minima, flow_periods, catchment, sim_id, period_id)
    
    ## 4 Plot Box-cox transformation for maxima
    _plot_boxcox(ax2, SWd_maxima["BC_obs"], SWd_maxima["BC_sim"], SWd_maxima["BC_residuals"], 
                 title_peaks, x_label_peaks, y_label_peaks, color="blue")
    ## 5 Plot Box-cox transformation for minima
    _plot_boxcox(ax3, SWd_minima["BC_obs"], SWd_minima["BC_sim"], SWd_minima["BC_residuals"],
                 title_lows,  x_label_lows,  y_label_lows,  color="red")
    fig.tight_layout()
    
    ## 6 Save plot
    filename = f"Soilwaterdepth_evaluation_{catchment}_{sim_id}_{period_id}).png"
    plt.savefig(os.path.join(output_path, filename), dpi=300)
    plt.close()    
    
def plot_soil_report(obs_SWd, sim_SWd, flow_periods, SWd_maxima, SWd_minima, λ, RMSE_maxima, RMSE_minima,
                     catchment, sim_id, period_id, timeseries_output_path, boxcox_output_path):     
    """Save soil water depth timeseries and boxcox plots of individual simulation separately to files.
    
    Parameters
    ----------
    obs_SWd, sim_SWd : pandas.Series
        Observed and simulated soil water depth time-series.
    flow_periods : list of tuple (int, int)
        Start and end integer of the flow period blocks.
    SWd_maxima, SWd_minima: pandas.DataFrame
        Extracted maximum and minimum soil water depth values, and their timestamp.
    λ : float
        Box-cox transformation parameter, shown in the subplot titles.
    RMSE_maxima, RMSE_minima : float
        RMSE of the Box-cox transformed maximum and minimum values, shown in the subplot titles.
    catchment : str
        Catchment name, used in the plot title and filename.
    sim_id : str
        Simulation idenifier, used in the plot title and filename.
    period_id : str
        Unique identifier for simulation period to be plotted.
    timeseries_output_path, boxcox_output_path : TYPE
        Folder to save the resulting timeseries, and box-cox transformation plot to.

    Returns
    -------
    None.
        Saves separate plots as a PNG file to timeseries_output_path and boxcox_output_path.
    """
    
    ## Figure 1: Soil water depth time-series
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    plot_soil_water_depth_single(ax1, obs_SWd, sim_SWd, SWd_maxima, SWd_minima, flow_periods, catchment, sim_id, period_id)
    fig1.tight_layout()
    plt.savefig(os.path.join(timeseries_output_path, f"Soilwaterdepth_timeseries_{catchment}_{sim_id}_{period_id}.png"), dpi=300)
    plt.close()

    ## Figure 2: Box-cox
    # Box-cox plot title
    title_peaks = f"Box-Cox Transformed Wet Soil Storage\n{catchment} {sim_id} {period_id}\nλ = {λ}, BC( RMSE = {RMSE_maxima:.2f} mm )"
    x_label_peaks = "BC( Observed Wet Soil Storage, St [mm] )"
    y_label_peaks = "BC( Simulated Wet Soil Storage, St [mm] )"  
    title_lows  = f"Box-Cox Transformed Dry Soil Storage\n{catchment} {sim_id} {period_id}\nλ = {λ}, BC( RMSE = {RMSE_minima:.2f} mm )"
    x_label_lows  = "BC( Observed Dry Soil Storage, St [mm] )"
    y_label_lows  = "BC( Simulated Dry Soil Storage, St [mm] )"
    
    ## 2.1 Plot layout
    fig2, (ax2, ax3) = plt.subplots(1, 2, figsize=(12, 6)) 
    
    ## 2.2 Subplots
    _plot_boxcox(ax2, SWd_maxima["BC_obs"], SWd_maxima["BC_sim"], SWd_maxima["BC_residuals"],
                 title_peaks, x_label_peaks, y_label_peaks,  color="blue")
    _plot_boxcox(ax3, SWd_minima["BC_obs"], SWd_minima["BC_sim"], SWd_minima["BC_residuals"],
                 title_lows, x_label_lows, y_label_lows, color="red")
    fig2.tight_layout(rect=[0, 0.05, 1, 0.95]) # rect %margin [left, bottom, right, top]
    
    ## 2.3 Save plot
    plt.savefig(os.path.join(boxcox_output_path, f"Soilwaterdepth_boxcox_{catchment}_{sim_id}_{period_id}.png"), dpi=300)
    plt.close()
    
#%% Plot Runoff Depth

def plot_runoff_depth(ax, obs_QF_mmdt, sim_QF_mmdt, QF_depth_cumulative, flow_periods, catchment, sim_id, period_id):
    """Plot observed and simulation cumulative runoff depth time-series for individual simulation. 
    
    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes on which the soil water depth is plotted into (a subplot of a larger figure).
    obs_QF_mmdt, sim_QF_mmdt : pandas.Series
        Observed and simulated runoff depth time-series.
    QF_depth_cumulative: pandas.DataFrame
        Extracted event-based cumulative runoff depth and their timestamp (midpoint) per each flow period block.
    flow_periods : list of tuple (int, int)
        Start and end integer of the flow period blocks.
    catchment : str
        Catchment name, used in the plot title and filename.
    sim_id : str
        Simulation idenifier, used in the plot title and filename.
    period_id : str
        Unique identifier for simulation period to be plotted.

    Returns
    -------
    None.
        The function returns the plot to a given axis
    """
    
    # 1 Plot cumulative volumes per each quick flow event
    ax.scatter(QF_depth_cumulative["mid_flow_period"], QF_depth_cumulative["obs_volume"], color="blue", s=12, zorder=3, label="Filter-based Cumulative Runoff Depth")
    ax.scatter(QF_depth_cumulative["mid_flow_period"], QF_depth_cumulative["sim_volume"], color="deepskyblue", s=12, zorder=3, label="Simulated Cumulative Runoff Depth")
    
    # 2 Plot timeseries runoff depth
    ax2 = ax.twinx() # Runoff depth time-series (second y-axis, shares x-axis with Cumulative runoff depth)
    # Keep cumulative runoff depth axis on top
    ax.set_zorder(2) 
    ax.patch.set_visible(False)
    
    ax2.plot(sim_QF_mmdt.index, sim_QF_mmdt.values, color="green", label="Simulated Runoff Depth")
    ax2.plot(obs_QF_mmdt.index, obs_QF_mmdt.values, color="black", label="Filter-based Runoff Depth")    
    
    # 3 Plot quick flow periods
    _plot_flow_periods_lines(ax, obs_QF_mmdt, flow_periods)
    
    # 4 Format plot
    ax.set_xlabel('Date', fontsize=14)
    ax.set_ylabel('Cumulative Runoff Depth [mm]', fontsize=14) 
    ax2.set_ylabel('Runoff Depth [mm]', fontsize=14)           
    ax.set_title(f"Runoff Depth\n{catchment} {sim_id} {period_id}", fontsize=14)
    ax.tick_params(axis="y", labelsize=14)
    ax2.tick_params(axis="y", labelsize=14)
    # merge legends from cumulative volume axis and runoff depth axis
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=14)
    
def plot_runoff_evaluation(obs_QF_mmdt, sim_QF_mmdt, flow_periods, QF_depth_cumulative, λ, RMSE, 
                          catchment, sim_id, period_id, output_path):                
    """Save plot to file, containing two subplots of cumulative runoff depth time-series and box-cox side-by-side for individual simulation. 
    
    Parameters
    ----------
    obs_QF_mmdt, sim_QF_mmdt : pandas.Series
        Observed and simulated runoff depth time-series.
    flow_periods : list of tuple (int, int)
        Start and end integer of the flow period blocks.
    QF_depth_cumulative: pandas.DataFrame
        Extracted event-based cumulative runoff depth and their timestamp (midpoint) per each flow period block.
    λ : float
        Box-cox transformation parameter, shown in the subplot titles.
    RMSE: float
        RMSE of the Box-cox transformed cumulative depth values, shown in the subplot titles.
    catchment : str
        Catchment name, used in the plot title and filename.
    sim_id : str
        Simulation idenifier, used in the plot title and filename.
    period_id : str
        Unique identifier for simulation period to be plotted.
    output_path : str
        Folder to save the resulting plot to.

    Returns
    -------
    None.
        Saves the plot as a PNG file to output_path.
    """
    
    # Box-cox plot title
    title_volume = f"Box-Cox Transformed Runoff Depth\nλ = {λ}, BC( RMSE = {RMSE:.2f} mm )"
    x_label_volume = "BC( Filter-based Cumulative Runoff Depth, QF_mmdt [mm] )"
    y_label_volume = "BC( Simulated Cumulative Runoff Depth, QF_mmdt [mm] )"
    
    ## 1 Plot layout
    fig = plt.figure(figsize=(22, 6))
    gs = gridspec.GridSpec(1, 2, width_ratios=[3, 1], figure=fig)
    ax1 = fig.add_subplot(gs[0, 0])  # Figure 1 Quick Flow Depth Time Series
    ax2 = fig.add_subplot(gs[0, 1])  # Figure 2 Box-cox 
    
    ## 2 Plot runoff depth time-series 
    plot_runoff_depth(ax1, obs_QF_mmdt, sim_QF_mmdt, QF_depth_cumulative, flow_periods, 
                     catchment, sim_id, period_id)
    ## 3 Plot Box-cox 
    _plot_boxcox(ax2, QF_depth_cumulative["BC_obs"],  QF_depth_cumulative["BC_sim"],  QF_depth_cumulative["BC_residuals"],
                 title_volume, x_label_volume, y_label_volume, color="blue")
    ax2.set_xlabel(x_label_volume, fontsize=12)
    ax2.set_ylabel(y_label_volume, fontsize=12)
    fig.tight_layout()
    
    ## 4 Save plot
    filename = f"Runoffdepth_evaluation_{catchment}_{sim_id}_{period_id}.png"
    plt.savefig(os.path.join(output_path, filename), dpi=300)
    plt.close() 
    
def plot_runoff_report(obs_QF_mmdt, sim_QF_mmdt, flow_periods, QF_depth_cumulative, λ, RMSE, 
                      catchment, sim_id, period_id, timeseries_output_path, boxcox_output_path):  
    """Save cumulative runoff depth time-series and boxcox plots of individual simultion separately to files.
    
    Parameters
    ----------
    obs_QF_mmdt, sim_QF_mmdt : pandas.Series
        Observed and simulated runoff depth time-series.
    flow_periods : list of tuple (int, int)
        Start and end integer of the flow period blocks.
    QF_depth_cumulative: pandas.DataFrame
        Extracted event-based cumulative runoff depth and their timestamp (midpoint) per each flow period block.
    λ : float
        Box-cox transformation parameter, shown in the subplot titles.
    RMSE: float
        RMSE of the Box-cox transformed cumulative depth values, shown in the subplot titles.
    catchment : str
        Catchment name, used in the plot title and filename.
    sim_id : str
        Simulation idenifier, used in the plot title and filename.
    period_id : str
        Unique identifier for simulation period to be plotted.
    timeseries_output_path, boxcox_output_path : str
        Folder to save the resulting timeseries, and box-cox transformation plot to.

    Returns
    -------
    None.
        Saves the plot as a PNG file to timeseries_output_path and boxcox_output_path.
    """
    
    ## Figure 1: Runoff depth time-series
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    plot_runoff_depth(ax1, obs_QF_mmdt, sim_QF_mmdt, QF_depth_cumulative, flow_periods, catchment, sim_id, period_id)
    fig1.tight_layout()
    plt.savefig(os.path.join(timeseries_output_path, f"Runoffdepth_timeseries_{catchment}_{sim_id}_{period_id}.png"), dpi=300)
    plt.close()
    
    ## Figure 2: Box-cox
    # Box-cox plot title
    title_volume = f"Box-Cox Transformed Runoff Depth\n{catchment} {sim_id} {period_id}, λ = {λ}, BC( RMSE = {RMSE:.2f} mm )"
    x_label_volume = "BC( Filter-based Cumulative Runoff Depth, QF_mmdt [mm] )"
    y_label_volume = "BC( Simulated Cumulative Runoff Depth, QF_mmdt [mm] )"
    
    ## 2.1 Format plot
    fig2, ax2 = plt.subplots(figsize=(12, 12))
    _plot_boxcox(ax2, QF_depth_cumulative["BC_obs"],  QF_depth_cumulative["BC_sim"],  QF_depth_cumulative["BC_residuals"],
                 title_volume, x_label_volume, y_label_volume, color="blue")
    fig2.tight_layout()
    
    ## 2.2 Save plot
    plt.savefig(os.path.join(boxcox_output_path, f"Runoffdepth_boxcox_{catchment}_{sim_id}_{period_id}.png"), dpi=300)
    plt.close()

#%% Plot Flow Timeseries

def plot_flow_timeseries(obs_F_m3s, sim_F_m3s, years_per_figure, flow_type, obs_label,
                        catchment, sim_id, period_id, output_path,
                        show_statistics,                
                        ME=None, RMSE=None, NSE=None,):                       
    """Plot simulated flow time-series against the observed one for individual simulation, and save to file.

    Parameters
    ----------
    obs_F_m3s, sim_F_m3s : pandas.Series
        Observed and simulated flow time-series in m3/s.
    years_per_figure : float
        Number of years (subplots) to include per saved image.
    flow_type : {"QF", "BF", "TF"}
        The flow type selected to be plotted (baseflow, quick flow or total flow).
    obs_label : str
        Legend label for the observed series ("filtered Observation" for QF/BF, "Observation" for TF).
    catchment : str
        Catchment name, used in the plot title and filename.
    sim_id : str
        Simulation idenifier, used in the plot title and filename.
    period_id : str
        Unique identifier for simulation period to be plotted.
    output_path : str
        Folder to save the resulting plot(s) to.
    show_statistics : boolean
        Whether to show the calculated statistics in the plot (a textbox inside the first subplot).
    ME, RMSE, NSE : float, optional
        Performance indices. The default is None, required if plot_statistics is True.

    Returns
    -------
    None.
        Saves plots as a PNG file(s) to output_path.
    """
    
    flow_label = {
        "QF": {"title": "Quick Flow", "y_label": "Quick Flow [m³/s]"},
        "BF": {"title": "Baseflow"  , "y_label": "Baseflow [m³/s]"},
        "TF": {"title": "Total Flow", "y_label": "Flow [m³/s]"}
    }    
    title = f"{flow_label[flow_type]['title']} Timeseries\n{catchment} {sim_id} {period_id}"
    y_label = flow_label[flow_type]['y_label']
    
    years = sorted(obs_F_m3s.index.year.unique()) 
    
    # Create a list of year grouped for 1 exported image
    # e.g. years_per_figure = 3 -> [ [2018, 2019, 2020], [2021, 2022] ]
    year_groups = [ years[i : i+years_per_figure]
                    for i in range(0, len(years), years_per_figure)]
    
    # Outer loop: loop over each group inside year-group, and save one image per group.
    for group_id, years_in_group in enumerate(year_groups):
        
        n_rows = len(years_in_group)
        
        # Plot layout
        fig, axes = plt.subplots(nrows=n_rows, ncols=1, figsize=(12, 4 * n_rows), sharey=True)
        
        # when n_rows > 1, plt.subplots returns axes in NumPy array i.e. axes = array([ax1, ax2, ax3])
        # when n_rows == 1, plt.subplots returns a single axes object, 
        # so we wrapped it in a list, otherwise the axes[i] below would rise a TypeError
        if n_rows == 1:
            axes = [axes]
    
        # Inner loop, loop over each year inside years_in_group, and plot.
        for i, year in enumerate(years_in_group):
            
            ax = axes[i] 
            
            year_mask = obs_F_m3s.index.year == year
            
            ## 1 Plot Timeseries
            ax.plot(obs_F_m3s.index[year_mask], obs_F_m3s[year_mask],
                    label=obs_label, color='black', linewidth=0.8)
            ax.plot(sim_F_m3s.index[year_mask], sim_F_m3s[year_mask],
                    label='Simulated', color='blue', linewidth=0.8)
            
            ## 2 Format Plot
            ax.set_title(str(year), fontsize=12, loc='left', pad=4)
            ax.set_ylabel(y_label, fontsize=14)
            ax.grid(True, linestyle='--', alpha=0.3)
            ax.tick_params(axis='both', labelsize=14)
        
        if show_statistics:
            
            # Add performance indices (in a textbox) on the first subplot.
            indices = f"ME = {ME:.2f}\nRMSE = {RMSE:.2f}\nNSE = {NSE:.2f}"
            properties = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
            axes[0].text(0.01, 0.98, indices, transform=axes[0].transAxes, fontsize=14,   
                         verticalalignment='top', bbox=properties, color='black')
        
        ## 3 Format plot
        axes[-1].set_xlabel("Date", fontsize=14)        
        axes[-1].legend(loc='upper right', fontsize=14)
        fig.suptitle(title, fontsize=16)
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        
        ## 4 Save plot
        filename = f"{flow_label[flow_type]['title']}_timeseries_{catchment}_{sim_id}_{period_id}.png"
        
        # Add "_partN" to the filename when saving more than one image. 
        if len(year_groups) > 1:          
            base, ext = os.path.splitext(filename)
            saved_filename = f"{base}_part{group_id + 1}{ext}"
        else:
            saved_filename = filename

        plt.savefig(os.path.join(output_path, saved_filename), dpi=300)
        plt.close()

#%% Plot Flow Water Balance

def plot_flow_waterbalance(obs_F_wb, sim_F_wb_dict, wb_deficit, 
                           flow_type, obs_label, catchment, sim_id, period_id, output_path):         
    """Plot multiple simulated water balance against the observed one, and save to file

    Parameters
    ----------
    obs_F_wb : pandas.Series
        DESCRIPTION.
    sim_F_wb_dict : dictionary of pandas.Series
        DESCRIPTION.
    wb_deficit : float
        Water balance deficit value per simulation.
    flow_type : {"QF", "BF", "TF"}
        The flow type selected to be returned (baseflow, quick flow or total flow).
    obs_label : {"QF", "BF", "TF"}
        The flow type selected to be returned (baseflow, quick flow or total flow).
    catchment : str
        Catchment name, used in the plot title and filename.
    sim_id : str
        Simulation idenifier, used in the plot title and filename.
    period_id : str
        Unique identifier for simulation period to be plotted.
    output_path : str
        Folder to save the resulting plot to.

    Returns
    -------
    None.
        Saves the plot as a PNG file to output_path.
    """
        
    plt.figure(figsize=(12,6))
    
    ## 1 Plot observed water balance
    plt.plot(obs_F_wb.index, obs_F_wb.values, label=obs_label, color="black", linewidth=2)
    
    ## 2 Plot simulated water balance
    for simkey in sorted(sim_F_wb_dict):
        sim_F_wb = sim_F_wb_dict[simkey]
        plt.plot(sim_F_wb.index, sim_F_wb.values, label = f"{simkey}")

    # Flow labels
    flow_label = {
        "QF": {"title": "Quick Flow", "y_label": "Cumulative Quick Flow Volume [m³]"},
        "BF": {"title": "Baseflow"  , "y_label": "Cumulative Baseflow Volume [m³]"},
        "TF": {"title": "Total Flow", "y_label": "Cumulatie Flow Volume [m³]"}
    }    
    title = f"{flow_label[flow_type]['title']} Timeseries\n{catchment} {sim_id} {period_id}"
    y_label = flow_label[flow_type]['ylabel']    

    ## 3 Format plot
    plt.xlabel('Date', fontsize=16)
    plt.ylabel(y_label, fontsize=16)
    plt.title(title, fontsize=16)
    plt.tick_params(axis='both', labelsize=16)
    plt.legend(fontsize=16)
    plt.tight_layout()
    
    ## 4 Save plot
    filename = f"{flow_type} Water Balance {catchment} {period_id}.png"
    filepath = os.path.join(output_path, filename)
    plt.savefig(filepath, dpi=300)
    plt.close()