# -*- coding: utf-8 -*-
"""

Created on Sat Apr  4 10:35:09 2026
@author: Way
"""
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

#%% Helper function

def add_seasonalblocks(start, end):
    # 1 Create Range of seasonal boundaries (months) based on the start date
    seasonal_boundaries = pd.date_range(start=start, end=end, freq="QS-DEC")
    seasonal_blocks = ["DJF", "MAM", "JJA", "SON"]
    """
    QS-DEC = Quarterly start from December
      i.e start = APR, end = JAN, seasonal_blocks = JUN, SEP, DEC, FEB, 
      date_range automatically select the closest quarterly month after APR(start)
    """
    # 2 Plot a Vertical Axis on each months inside seasonal_boundaries
    for date in seasonal_boundaries:
        plt.axvline(date, color="black", linestyle=":", linewidth=2, alpha=0.3)
    
    # 3 Vertical axis extend on the y axis, ylim()[1] is the maximum value on y axis, so Vertical axis extend to the top
    y_offset = plt.ylim()[1]
    
    # 4 Plot seasonal blocks text
    for i in range(len(seasonal_boundaries)-1):
        # if we have 5 vertical lines of seasonal boundaries, i.e. DEC MAR JUN SEP DEC
        # we would like 4 seasonal blocks DJF MAM JJA SON
        
        # calculate distance of the midpoint inbetween 2 vertical lines, DEC + MAR-DEC/2
        midpoint = seasonal_boundaries[i] + (seasonal_boundaries[i+1] - seasonal_boundaries[i]) / 2
        
        # plot Seasonal blocks text
        # [i % 4] means seasonal blocks index repeated after 4 times, its a loop for seasonal_blocks member
        plt.text(midpoint, y_offset, seasonal_blocks[i % 4], ha="center", va="top")

def add_flowperiodlines(ax, obs, flowperiods):
    # 1 extract index of slowflowperiods and convert it into datetime from obs index
    """
    date_flowperiods = []
    for start, end in flowperiods:
        date_slowflowperiods.append( obs.index[start], obs.index[end] )
    *shorter version below
    """  
    date_flowperiods = [ (obs.index[start] , obs.index[end]) for start, end in flowperiods]
    
    # 2 plot end periods as blue lines
    for start, end in date_flowperiods:
        ax.axvline(end, color="lightskyblue", linestyle="--", alpha=0.8)
    
    # 3 plot 1 line of start period, also act as legend
    # date_flowperiods contains tuple (dateA, dateB), [0][0] takes the first tuple and the first date i.e. dateA
    ax.axvline(date_flowperiods[0][0], color="lightskyblue", linestyle="--", label="Flow Periods")
    
def add_deviationlines(BC_obs, residuals):
    # Calculation for box-cox transformed plot: x-axis is observed variable, y-axis is simulated variable
    
    # Observed variable, averaged for every 2 data points (moving average)
    # the x-coordinate for mean deviation line and standard deviation envelope
    average_obs = BC_obs.rolling(window=2).mean()      
    
    # Mean residuals/mean Error (ME)
    # residuals/error is averaged globally according to ME formula, since it represent systematic bias, constant bias.
    # rolling window would make it local error instead of global mean error
    mean_residuals = residuals.mean()
    
    # Stdev calulated for every 2 residuals data points
    # Stdev represent the deviation of the residuals
    stdev   = residuals.rolling(window=2).std()

    # the envelope lines represent deviation (stdev) from mean error/residuals
    # Hence the formula, y = bisector + mean residuals ± stdev
    # The bisector is represented by average obs, because bisector is y = x, and the y just follows the x coordinate
    
    # In the original code, envelope lines are deviated/shifted from the bisector instead of average residuals
    # Hence, simpler formula, y = bisector ± stdev, similarly bisector is represented by average obs
    # The idea is, stdev are deviation from perfect model (bisector, y = x), which is wrong theoretically
    # However, this mistake is hidden because the average residual value is small after transfromed with box cox transform
    upper   = average_obs + mean_residuals + stdev   
    lower   = average_obs + mean_residuals - stdev   
    
    # Dataframe
    df_deviationbands = pd.DataFrame({
        "average_obs"       : average_obs,
        "mean_residuals"    : mean_residuals,
        "stdev"             : stdev,
        "upper"             : upper,
        "lower"             : lower
    }).dropna() # rolling calculation causes NaN at the first row, so we use dropNaN
    
    # if there are less than 2 flow periods, not enough SWd peaks and lows to be extracted, deviation bands/lines cant be generated
    if len(df_deviationbands) < 2:
        raise ValueError(
            f"Not enough points for deviation-band calculation. "
            f"Found {len(df_deviationbands)} points."
        )
    
    # Linear interpolation
    # np.polyfit fits data with interpolation, 1 is linear fit, 2 is quadratic, etc
    # np.polyfit returns NumPy array of 2 values [a, b], as in y = ax + b
    # we want to have linear interpolation/line of upper and lower, with average obs as the x coordinate from values we have on x axis
    # dt["average_obs"] = the x coordinate from values we have on x axis
    # dt["upper"] and df["lower"] are on the y-axis, the deviation from average residuals
    fit_upper = np.polyfit(df_deviationbands["average_obs"], df_deviationbands["upper"], 1)
    fit_lower = np.polyfit(df_deviationbands["average_obs"], df_deviationbands["lower"], 1)
    
    return df_deviationbands, fit_upper, fit_lower, mean_residuals

#%% Plot ET

# Multiple simulations in 1 plot:
  # ETa vs ETp, ET ratio, soil water variation (5 years)
  # QF water balance, BF water balance, TF water balance (total)
# 1 Simulation, 1 Plot:
    # Soil water variation (5 years)
    # Recharge, Runoff (5 years)
    # Quickflow, Baseflow, Total flow (1 year)

def plotET_ActualvsPotential(ETp_series, ETa_dict, catchment, period_id, plotET_path):
    plt.figure(figsize=(12,6))
    
    # 1 ETp
    plt.plot(ETp_series.index, ETp_series.values, label="ETp", color="orange", linewidth=2)
    
    # 2 ETa
    for simkey in sorted(ETa_dict):
        ETa_series = ETa_dict[simkey]
        plt.plot(ETa_series.index, ETa_series.values, label = f"ETa $b_{{e}}$ = {simkey}")
    
    # 3 Format plot
    plt.xlabel('Month', fontsize=16)
    plt.ylabel('ET (mm/day)', fontsize=16)
    plt.title(f'ETa vs ETp for Different $b_{{e}}$ Values\n{catchment} {period_id}', fontsize=16)
    plt.tick_params(axis='both', labelsize=16)
    plt.legend(fontsize=16)
    plt.tight_layout()
    
    # 4 Save plot
    filename = f"{catchment} ETa vs ETp {period_id}.png"
    filepath = os.path.join(plotET_path, filename)
    plt.savefig(filepath, dpi=300)
    plt.close()

def plotET_ratio(ETratio_dict, catchment, start, end, period_id, plotET_path):
    plt.figure(figsize=(12,6))
    
    # 1 ETratio
    for simkey in sorted(ETratio_dict):
        ETratio_series = ETratio_dict[simkey]
        plt.plot(ETratio_series.index, ETratio_series.values, 
                 marker="o", linestyle='-', linewidth = 2, label = f"ETa $b_{{e}}$ = {simkey}")
    
    # 2 add Seasonal Blocks
    add_seasonalblocks(start, end)
    
    # 3 Format plot
    plt.xlabel('Month', fontsize=15)
    plt.ylabel('ETa / ETp', fontsize=15)
    plt.title(f"ET ratio for Different $b_{{e}}$ Values\n{catchment} {period_id}", fontsize=15)
    plt.tick_params(labelsize=15)
    plt.legend(fontsize=15)
    plt.tight_layout()
    
    # 4 Save plot
    filename = f"{catchment} ET ratio {period_id}.png"
    filepath = os.path.join(plotET_path, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    
def plotET_soilwatervariation(SWd_dict, catchment, start, end, period_id, plotET_path):
    plt.figure(figsize=(12,6))
    
    # 1 Plot Timeseries soil water variation 
    for simkey in sorted(SWd_dict):
        SWd_series = SWd_dict[simkey]
        plt.plot(SWd_series.index, SWd_series.values, 
                 marker="o", linestyle='-', linewidth = 2, label = f"ETa $b_{{e}}$ = {simkey}")

    # 2 add Seasonal Blocks
    add_seasonalblocks(start, end)

    # 3 Format plot
    plt.xlabel('Month', fontsize=14)
    plt.ylabel('Soil Storage (mm)', fontsize=14)    
    plt.title(f'Soil Water Variation for Different $b_{{e}}$ Values\n{catchment} {period_id}', fontsize=14)
    plt.tick_params(labelsize=14)
    plt.legend(fontsize=14)
    plt.tight_layout()

    # 4 Save plot
    filename = f"{catchment} Soil water variation {period_id}.png"
    filepath = os.path.join(plotET_path, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()

#%% Plot Box-cox

def plot_boxcox(ax,                            # ax passed in to define location of the subplots. i.e. ax3 is bottom left
                BC_obs, BC_sim, residuals,     # variable
                title, xlabel, ylabel, color): # Figure title
    
    # Calculated variables for Box-cox plot
    df_deviationbands, fit_upper, fit_lower, mean_residuals = add_deviationlines(BC_obs, residuals)
    
    # Find smallest and largest value from all variables: 
      # to make all points and lines visible and in rectangular shape
    axis_min = min(BC_obs.min(), BC_sim.min(), df_deviationbands["lower"].min()) - 2 
    axis_max = max(BC_obs.max(), BC_sim.max(), df_deviationbands["upper"].max()) + 2
    
    # Create NumPy array of 100 values [axis_min, axis_min + 2 ..., axis_max]
    # The x-coordinates for interpolated lines
    xline = np.linspace(axis_min, axis_max, 100)
    # Calculate List of y-coordinates from fitted equation on standard deviation line
    y_upper = np.polyval(fit_upper, xline)
    y_lower = np.polyval(fit_lower, xline)
    
    # additional coordinates for mean residuals/ME/mean deviation line
    y_mean = xline + mean_residuals
    
    # 1 Plot BC_obs and BC_sim
    ax.scatter(BC_obs, BC_sim, color=color, label="Obs vs Sim")
    
    # 2 Plot bisector line
    ax.plot([axis_min, axis_max],       [axis_min, axis_max],      color="black", linestyle="-", linewidth=1, label="Bisector")
    #       [x1, x2] x-coordinate list, [y1, y2] y-coordinate list
    
    # 3 Plot standard deviation envelope
    ax.plot(xline, y_upper, color="black", linestyle="--", linewidth=2, label="Standard Deviation")
    ax.plot(xline, y_lower, color="black", linestyle="--", linewidth=2)
    
    # 4 Plot residuals/error/mean deviation line
    ax.plot(xline, y_mean, color="black", linestyle="-", linewidth=2, label="Mean Deviation")
    """
    # +5 Plot scatter points 
    ax.scatter(df_stdevband["average"], df_stdevband["upper"],  color="black",   s=15, label="average + stdev")
    ax.scatter(df_stdevband["average"], df_stdevband["lower"], color="darkgray", s=15, label="average - stdev")
    """
    # 5 Format plot
    ax.set_xlim(axis_min, axis_max)
    ax.set_ylim(axis_min, axis_max)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_title(title, fontsize=14)
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
    ax.tick_params(axis="both", labelsize=14)
    ax.legend(fontsize=14)

#%% Plot Soil

def plotsoil_soilwatervariation(ax, # ax passed in de plotsoil_evaluation to define location of the subplot. i.e. ax1 is top
                            obs_SWd, sim_SWd, SWd_peaks, SWd_lows, slowflowperiods, # variables
                            catchment, simname, period_id):                         # Figure label
    
    # 1 Plot Timeseries soil water variation 
    ax.plot(sim_SWd.index, sim_SWd.values, color="green", label="Simulated")
    ax.plot(obs_SWd.index, obs_SWd.values, color="black", label="Observed")
    
    # 2 Plot Peak and End values of soil water variation
    ax.scatter(SWd_peaks["peak_time"], SWd_peaks["obs_peak"], color="blue", s=12, zorder=3, label="Wet Soil Storage")
    ax.scatter(SWd_peaks["peak_time"], SWd_peaks["sim_peak"], color="blue", s=12, zorder=3)
    ax.scatter(SWd_lows["low_time"],   SWd_lows["obs_low"],   color="red",  s=12, zorder=3, label="Dry Soil Storage")
    ax.scatter(SWd_lows["low_time"],   SWd_lows["sim_low"],   color="red",  s=12, zorder=3)

    # 3 Plot Slow flow periods
    add_flowperiodlines(ax, obs_SWd, slowflowperiods)
    
    # 4 Format plot
    ax.set_xlabel('Date', fontsize=14)
    ax.set_ylabel('Soil Water Depth [mm]', fontsize=14)
    ax.set_title(f"Soil Water Variation\n{catchment} {simname} {period_id}", fontsize=14)
    ax.tick_params(axis="both", labelsize=14)
    ax.legend(fontsize=14)

def plotsoil_evaluation(obs_SWd, sim_SWd, slowflowperiods,     # Variables: Timeseries soil water
                                    catchment, simname, period_id,  # Figure title: Soil water
                                    SWd_peaks, SWd_lows,                   # Variables: Box-cox
                                    λ, RMSE_peaks, RMSE_lows,              # Figure title, label: Box-cox 
                                    plotsoil_evaluation_path):                  # output folder
    
    # Box-cox plot title
    title_peaks = f"Box-Cox Transformed Wet Soil Storage\nλ = {λ}, BC( RMSE = {RMSE_peaks:.2f} mm )"
    xlabel_peaks = "BC( Observed Wet Soil Storage, St [mm] )"
    ylabel_peaks = "BC( Simulated Wet Soil Storage, St [mm] )"
    
    title_lows  = f"Box-Cox Transformed Dry Soil Storage\nλ = {λ}, BC( RMSE = {RMSE_lows:.2f} mm )"
    xlabel_lows  = "BC( Observed Dry Soil Storage, St [mm] )"
    ylabel_lows  = "BC( Simulated Dry Soil Storage, St [mm] )"
    
    # Plot layout
    # Image size
    fig = plt.figure(figsize=(12, 12))
    gs  = gridspec.GridSpec(2, 2, height_ratios=[1.5, 2])
    # ax passed here define location of the subplots
    ax1 = fig.add_subplot(gs[0, :]) # Subplot 1, Figure Time series Soil water (Top)
    ax2 = fig.add_subplot(gs[1, 0]) # Subplot 2, Figure Box-cox Peak Soil Water (Bottom left)
    ax3 = fig.add_subplot(gs[1, 1]) # Subplot 3, Figure Box-cox Dry Soil Water (Bottom right)
    
    # 1 Plot Soil water variation
    plotsoil_soilwatervariation(ax1, # put this plot in ax1
                            obs_SWd, sim_SWd, SWd_peaks, SWd_lows, slowflowperiods, 
                            catchment, simname, period_id)
    # 2 Plot Box-cox transformation for peak values
    plot_boxcox(ax2, 
                SWd_peaks["BC_obs_peak"], SWd_peaks["BC_sim_peak"], SWd_peaks["residuals"],
                title_peaks, xlabel_peaks, ylabel_peaks, color="blue")
    # 3 Plot Box-cox transformation for low values
    plot_boxcox(ax3, 
                SWd_lows["BC_obs_low"], SWd_lows["BC_sim_low"], SWd_lows["residuals"],
                title_lows,  xlabel_lows,  ylabel_lows,  color="red")
    
    # Save
    fig.tight_layout()
    filename = f"SoilStorage_evaluation_{catchment}_{simname}_{period_id}).png"
    plt.savefig(os.path.join(plotsoil_evaluation_path, filename), dpi=300)
    plt.close()    
    
def plotsoil_report(obs_SWd, sim_SWd, slowflowperiods,         # Variables: Timeseries soil water
                                catchment, simname, period_id,      # Figure title: Soil water
                                SWd_peaks, SWd_lows,                       # Variables: Box-cox
                                λ, RMSE_peaks, RMSE_lows,                  # Figure title, label: Box-cox 
                                plotsoil_timeseries_path, plotsoil_boxcox_path):     # Output folder

    # Figure 1 - Soil water variation Timeseries
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    plotsoil_soilwatervariation(ax1, obs_SWd, sim_SWd, SWd_peaks, SWd_lows,
                            slowflowperiods, catchment, simname, period_id)
    fig1.tight_layout()
    plt.savefig(os.path.join(plotsoil_timeseries_path, f"Soilwater_timeseries_{catchment}_{simname}_{period_id}.png"), dpi=300)
    plt.close()

    # Figure 2 - Box-cox
    title_peaks = f"Box-Cox Transformed Wet Soil Storage\n{catchment} {simname} {period_id}\nλ = {λ}, BC( RMSE = {RMSE_peaks:.2f} mm )"
    xlabel_peaks = "BC( Observed Wet Soil Storage, St [mm] )"
    ylabel_peaks = "BC( Simulated Wet Soil Storage, St [mm] )"
        
    title_lows  = f"Box-Cox Transformed Dry Soil Storage\n{catchment} {simname} {period_id}\nλ = {λ}, BC( RMSE = {RMSE_lows:.2f} mm )"
    xlabel_lows  = "BC( Observed Dry Soil Storage, St [mm] )"
    ylabel_lows  = "BC( Simulated Dry Soil Storage, St [mm] )"
    
    fig2, (ax2, ax3) = plt.subplots(1, 2, figsize=(12, 6)) # 1 row, 2 columns, total figure size 12 x 6
    plot_boxcox(ax2, SWd_peaks["BC_obs_peak"], SWd_peaks["BC_sim_peak"], SWd_peaks["residuals"],
               title_peaks, xlabel_peaks, ylabel_peaks,  color="blue")
    plot_boxcox(ax3, SWd_lows["BC_obs_low"],    SWd_lows["BC_sim_low"],    SWd_lows["residuals"],
               title_lows,  xlabel_lows,  ylabel_lows,  color="red")
    
    fig2.tight_layout(rect=[0, 0.05, 1, 0.95]) # rect %margin [left, bottom, right, top]
    plt.savefig(os.path.join(plotsoil_boxcox_path, f"Soilwater_boxcox_{catchment}_{simname}_{period_id}.png"), dpi=300)
    plt.close()
    
    
#%% Plot Runoff Depth

def plotrunoff_depth(ax, # for subplot 
                     obs_QF_mmdt, sim_QF_mmdt, QF_volume, quickflowperiods,
                     catchment, simname, period_id):
        
    # 1 Plot cumulative volumes per each quick flow event
    ax.scatter(QF_volume["mid_flowperiod"], QF_volume["obs_volume"], color="blue", s=12, zorder=3, label="Filter-based Cumulative Runoff Depth")
    ax.scatter(QF_volume["mid_flowperiod"], QF_volume["sim_volume"], color="deepskyblue", s=12, zorder=3, label="Simulated Cumulative Runoff Depth")
    
    # 2 Plot timeseries runoff depth
    ax2 = ax.twinx() # create second axis for timeseries
    ax.set_zorder(2) # keep cumulative volume axis on top
    ax.patch.set_visible(False)
    
    ax2.plot(sim_QF_mmdt.index, sim_QF_mmdt.values, color="green", label="Simulated Runoff Depth")
    ax2.plot(obs_QF_mmdt.index, obs_QF_mmdt.values, color="black", label="Filter-based Runoff Depth")    
    
    # 3 Plot quick flow periods
    add_flowperiodlines(ax, obs_QF_mmdt, quickflowperiods)
    
    # 4 Format plot
    ax.set_xlabel('Date', fontsize=14)
    ax.set_ylabel('Cumulative Runoff Depth [mm]', fontsize=14) # main axis, cumulative runoff depth     
    ax2.set_ylabel('Runoff Depth [mm]', fontsize=14)           # second axis, timseries runoff depth
    ax.set_title(f"Runoff Depth\n{catchment} {simname} {period_id}", fontsize=14)
    ax.tick_params(axis="y", labelsize=14)
    ax2.tick_params(axis="y", labelsize=14)
    # merge legends from Cumulative volume axis and runoff depth axis
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=14)
    
def plotrunoff_evaluation(obs_QF_mmdt, sim_QF_mmdt, quickflowperiods,
                          catchment, simname, period_id,              # Figure title, label: Runoff depth
                          QF_volume, residuals,                       # Variables : Box-cox
                          λ, RMSE_volume,                             # Figure title, label: Box-cox 
                          plotrunoff_evaluation_path):                     # Output folder
    
    # Box-cox plot title
    title_volume = f"Box-Cox Transformed Runoff Depth\nλ = {λ}, BC( RMSE = {RMSE_volume:.2f} mm )"
    xlabel_volume = "BC( Filter-based Cumulative Runoff Depth, QF_mmdt [mm] )"
    ylabel_volume = "BC( Simulated Cumulative Runoff Depth, QF_mmdt [mm] )"
    
    # Plot layout
    fig = plt.figure(figsize=(22, 6))
    gs = gridspec.GridSpec(1, 2, width_ratios=[3, 1], figure=fig)
    ax1 = fig.add_subplot(gs[0, 0])  # Figure 1 Quick Flow Depth Time Series
    ax2 = fig.add_subplot(gs[0, 1])  # Figure 2 Box-cox 
    
    # 1 Plot Runoff Depth Timeseries 
    plotrunoff_depth(ax1, 
                     obs_QF_mmdt, sim_QF_mmdt, QF_volume, quickflowperiods, 
                     catchment, simname, period_id)
    # 2 Plot Box-cox 
    plot_boxcox(ax2, 
                QF_volume["BC_obs_volume"],  QF_volume["BC_sim_volume"],  QF_volume["residuals"],
                title_volume, xlabel_volume, ylabel_volume, color="blue")
    ax2.set_xlabel(xlabel_volume, fontsize=12)
    ax2.set_ylabel(ylabel_volume, fontsize=12)
    
    # Save
    fig.tight_layout()
    filename = f"Runoffdepth_evaluation_{catchment}_{simname}_{period_id}.png"
    plt.savefig(os.path.join(plotrunoff_evaluation_path, filename), dpi=300)
    plt.close() 
    
def plotrunoff_report(obs_QF_mmdt, sim_QF_mmdt, quickflowperiods, # Variables : Runoff depth
                      catchment, simname, period_id,              # Figure title, label: Runoff depth
                      QF_volume, residuals,                        # Variables : Box-cox
                      λ, RMSE_volume,                              # Figure title, label: Box-cox 
                      plotrunoff_timeseries_path, plotrunoff_boxcox_path):  # Output folder
    
    # Figure 1 - Runoff Depth Timeseries
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    plotrunoff_depth(ax1, 
                     obs_QF_mmdt, sim_QF_mmdt, QF_volume, quickflowperiods, 
                     catchment, simname, period_id)
    fig1.tight_layout()
    plt.savefig(os.path.join(plotrunoff_timeseries_path, f"Runoffdepth_timeseries_{catchment}_{simname}_{period_id}.png"), dpi=300)
    plt.close()
    
    # Figure 2 - Box-cox
    title_volume = f"Box-Cox Transformed Runoff Depth\n{catchment} {simname} {period_id}, λ = {λ}, BC( RMSE = {RMSE_volume:.2f} mm )"
    xlabel_volume = "BC( Filter-based Cumulative Runoff Depth, QF_mmdt [mm] )"
    ylabel_volume = "BC( Simulated Cumulative Runoff Depth, QF_mmdt [mm] )"
    
    fig2, ax2 = plt.subplots(figsize=(12, 12))
    plot_boxcox(ax2, QF_volume["BC_obs_volume"],  QF_volume["BC_sim_volume"],  QF_volume["residuals"],
                title_volume, xlabel_volume, ylabel_volume, color="blue")
    fig2.tight_layout()
    plt.savefig(os.path.join(plotrunoff_boxcox_path, f"Runoffdepth_boxcox_{catchment}_{simname}_{period_id}.png"), dpi=300)
    plt.close()


#%% Plot Flow Timeseries

def plotflow_timeseries(obs_F_m3s, sim_F_m3s,
                        obslabel,                       # QF/BF = filtered observation, TF = observed 
                        years_per_figure,
                        flowtype,                       # QF/BF/TF
                        catchment, simname, period_id,  # Figure title, axis, and filename
                        plotflow_timeseries_path,                       # output path
                        plot_statistics,                # Fine tune = plot statistics, routing = do not plot statistics
                        ME=None, RMSE=None, NSE=None):  # Statistics, performance indices
                        
    # Flow labels, type: dictionary of dictionaries
    flow_label = {
        "QF": {"title": "Quick Flow", "ylabel": "Quick Flow [m³/s]"},
        "BF": {"title": "Baseflow"  , "ylabel": "Baseflow [m³/s]"},
        "TF": {"title": "Total Flow", "ylabel": "Flow [m³/s]"}
    }    
    title = f"{flow_label[flowtype]['title']} Timeseries\n{catchment} {simname} {period_id}"
    ylabel = flow_label[flowtype]['ylabel']
    
    # Create list of years from the timeseries
    years = sorted(obs_F_m3s.index.year.unique()) # [2018, 2019, 2020, 2021, 2022]
    
    # Create a list of year grouped for 1 exported image
    # [ [2018, 2019, 2020], [2021, 2022] ]
    year_groups = [ years[i : i+years_per_figure]
                    for i in range(0, len(years), years_per_figure)]
    """
    year_groups = []
    for i in range(0, len(years), years_per_figure):
        group = years[i : i+years_per_figure]
        year_groups.append(group)
    """
    
    # First loop, we loop the group of years where each loop we export 1 image
    for group_id, group_years in enumerate(year_groups):
        # enumerate returns (index, element), so, (1, [2018, 2019, 2020])
        
        # number of flow subplots
        nrows = len(group_years)
        
        # Plot Layout
        fig, axes = plt.subplots(nrows=nrows, ncols=1,
                         figsize=(12, 4 * nrows),
                         sharey=True)
        
        # if only 1 year left in the last group, we wrap axes in a list so the second loop didnt stuck
        if nrows == 1:
            axes = [axes]
    
        # Second loop, we loop the years inside 1 group to be plotted
        for i, year in enumerate(group_years):
            
            ax = axes[i] # i.e. ax1, ax2, ax3
            
            # select the year to be plotted from timeseries data
            mask = obs_F_m3s.index.year == year
            
            # 1 Plot Timeseries
            ax.plot(obs_F_m3s.index[mask], obs_F_m3s[mask],
                    label=obslabel, color='black', linewidth=0.8)
            ax.plot(sim_F_m3s.index[mask], sim_F_m3s[mask],
                    label='Simulated', color='blue', linewidth=0.8)
            
            # 2 Format Plot
            ax.set_title(str(year), fontsize=12, loc='left', pad=4)
            ax.set_ylabel(ylabel, fontsize=14)
            ax.grid(True, linestyle='--', alpha=0.3)
            ax.tick_params(axis='both', labelsize=14)
        
        if plot_statistics:
            
            # add performance indices (in a textbox) on every first subplot/ax1
            indices = f"ME = {ME:.2f}\nRMSE = {RMSE:.2f}\nNSE = {NSE:.2f}"
            # format textbox
            properties = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
            axes[0].text(0.01, 0.98, indices, transform=axes[0].transAxes, fontsize=14,   # axes[0] is the first subplot
                         verticalalignment='top', bbox=properties, color='black')
        
        # 2 Format plot
        axes[-1].set_xlabel("Date", fontsize=14)        # axes[-1] is the last subplot, -2 is the second last, etc.
        axes[-1].legend(loc='upper right', fontsize=14)
        fig.suptitle(title, fontsize=16)
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        
        # 3 Save plot
        filename = f"{flow_label[flowtype]['title']}_timeseries_{catchment}_{simname}_{period_id}.png"
        
        # if multiple images/group_years for 1 simulation
        if len(group_years) > 1:          # group_years is a list, so compare the length to > 1
            base, ext = os.path.splitext(filename)
            # base = {flow_label[flowtype]['title']}_timeseries_{catchment}_{simname}_{period_id}
            # ext  = .png"
            saved_filename = f"{base}_part{group_id + 1}{ext}"
        else:
            saved_filename = filename

        plt.savefig(os.path.join(plotflow_timeseries_path, saved_filename), dpi=300)
        plt.close()

#%% Plot Flow Water Balance

def plotflow_waterbalance(obs_F_wb, sim_F_wb_dict,
                          obslabel, 
                          wb_deficit,                     # indices
                          flowtype,                       # QF/BF/TF
                          catchment, simname, period_id,  # Figure title, axis, and filename
                          plotflow_waterbalance_path):         # output path

    plt.figure(figsize=(12,6))
    
    # 1 Plot Water Balance: Observation
    plt.plot(obs_F_wb.index, obs_F_wb.values, label=obslabel, color="black", linewidth=2)
    
    # 2 Plot Water Balance: Simulation
    for simkey in sorted(sim_F_wb_dict):
        sim_F_wb = sim_F_wb_dict[simkey]
        plt.plot(sim_F_wb.index, sim_F_wb.values, label = f"{simkey}")

    # 
    # 3 Flow labels, type: dictionary of dictionaries
    flow_label = {
        "QF": {"title": "Quick Flow", "ylabel": "Cumulative Quick Flow Volume [m³]"},
        "BF": {"title": "Baseflow"  , "ylabel": "Cumulative Baseflow Volume [m³]"},
        "TF": {"title": "Total Flow", "ylabel": "Cumulatie Flow Volume [m³]"}
    }    
    title = f"{flow_label[flowtype]['title']} Timeseries\n{catchment} {simname} {period_id}"
    ylabel = flow_label[flowtype]['ylabel']    

    # 4 Format plot
    plt.xlabel('Date', fontsize=16)
    plt.ylabel(ylabel, fontsize=16)
    plt.title(title, fontsize=16)
    plt.tick_params(axis='both', labelsize=16)
    plt.legend(fontsize=16)
    plt.tight_layout()
    
    # 4 Save plot
    filename = f"{flowtype} Water Balance {catchment} {period_id}.png"
    filepath = os.path.join(plotflow_waterbalance_path, filename)
    plt.savefig(filepath, dpi=300)
    plt.close()