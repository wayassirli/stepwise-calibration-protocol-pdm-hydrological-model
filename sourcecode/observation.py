# -*- coding: utf-8 -*-
"""Load observation time-series of catchments, run quality check, and prepare them for calibration and validation

Created on Mon Mar  2 21:22:08 2026
@author: Way
"""

import os
import pandas as pd

columnname = "Value"

class Observation:
    """Load a catchment's hydrological observed time-series, run quality checks on them, 
    and prepare them for calibration and evaluation.
    
    Parameters
    ----------
    excel_row : pandas.Series
        One row from the observation configuration excel containing catchment information and their associated time-series metadata
    sim_path : str
        Path to folder containing the observation files.
    
    Attributes
    ----------
    catchment : str
        Name of the catchment associated with the time-series metadata.
    catchmentsize = float
        Catchment area in m2
    P_freq, ETp_freq, Q_freq, BF_freq, QF_freq : str
        Expected frequency of the observed hydrological time-series (rainfall, evapotranspiration, flow, baseflow, quickflow)
    P_mmdt, ETp_mmdt, Q_m3s, BF_m3s, QF_m3s : pandas.Series
        The observed hydrological time-series
    """
    
    def __init__(self, excel_row, obs_path):
        row_todict = excel_row.to_dict()
        
        self.catchment = row_todict['catchment']
        self.catchment_size = row_todict['catchment_size_m2']
        
        rainfall_filename = row_todict['rainfall_filename']
        ETp_filename = row_todict['ETp_filename']
        flow_filename = row_todict['flow_filename']
        baseflow_filename = row_todict['baseflow_filename']
        quickflow_filename = row_todict['quickflow_filename']
        
        self.P_freq = row_todict['rainfall_freq']
        self.ETp_freq = row_todict['ETp_freq']
        self.Q_freq = row_todict['flow_freq']
        self.BF_freq = row_todict['baseflow_freq']
        self.QF_freq = row_todict['quickflow_freq']
        
        self.P_mmdt = self.load_timeseries(obs_path, rainfall_filename, columnname)
        self.ETp_mmdt = self.load_timeseries(obs_path, ETp_filename, columnname)
        self.Q_m3s = self.load_timeseries(obs_path, flow_filename, columnname)
        self.BF_m3s = self.load_timeseries(obs_path, baseflow_filename, columnname)
        self.QF_m3s = self.load_timeseries(obs_path, quickflow_filename, columnname)
        
        self.qualitycheck_timeseries(self.P_mmdt, self.P_freq, "Rainfall")
        self.qualitycheck_timeseries(self.ETp_mmdt, self.ETp_freq, "ETp")
        self.qualitycheck_timeseries(self.Q_m3s, self.Q_freq, "Total Flow")
        self.qualitycheck_timeseries(self.BF_m3s, self.BF_freq, "Baseflow")
        self.qualitycheck_timeseries(self.QF_m3s, self.QF_freq, "Quick flow")
        
    def load_timeseries(self, folder, filename, columnname):
        """Extract the time-series from obesrvation files and prepare them for use in calibration

        Parameters
        ----------
        folder : str
            Path of the folder that stores the observation files.
        filename : str
            Filename of the observation file.
        columnname : str
            The column header of the time-series.

        Returns
        -------
        pandas.Series
            Time-series of hydrological observations (P, ETp, Q, BF, QF).
        """
        file = os.path.join(folder, filename)
        df = pd.read_excel(file)
        
        # Raise an error when user has not renamed the column header
        if "Timestamp" not in df.columns:
            raise ValueError(
                f'"Rename date/time column header into "Timestamp" in {filename}'
            )
        
        if "Value" not in df.columns:
            raise ValueError(
                f'"Rename time-series column header into "Value" in {filename}'
            )
        
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        df = df.set_index("Timestamp")                             
        
        return df[columnname] 
    
    def qualitycheck_timeseries(self, timeseries, freq, name):
        """Run quality check on observation time-series and raise an error if fails quality check.
        
        Parameters
        ----------
        timeseries : pandas.Series
            The observation time-series to be quality checked.
        freq : str
            Expected frequency of the time-series, used to detect missing timestamp.
        name : str
            Variable name to identify which variable has failed quality check.

        Raises
        ------
        ValueError
            When duplicate timestamp, missing timestamp, missing values are found.
        """
        
        # Ensure timestamp in chronological order
        timeseries = timeseries.sort_index()
        
        # Check 1: Duplicate timestamp
        duplicate_timestamps = timeseries.index[timeseries.index.duplicated()]
         
        if not duplicate_timestamps.empty:
            print(f"Duplicated {name} data at: ")
            print(duplicate_timestamps[:5])
            raise ValueError("Duplicated data")
            
        # Check 2: Missing timestamp
        expected_timestamps = pd.date_range(
            start = timeseries.index.min(),
            end = timeseries.index.max(),
            freq = freq
            )

        missing_timestamps = expected_timestamps.difference(timeseries.index)

        if not missing_timestamps.empty:       
            print(f"Missing {name} data at: ")
            print(missing_timestamps[:5])
            raise ValueError("Missing data")
        
        # Check 3: Missing values (NaN)
        NaN_timestamps = timeseries[timeseries.isna()].index 

        if not NaN_timestamps.empty:
            print("Missing {name} values at: ")
            print(NaN_timestamps[:5])
            raise ValueError("Missing Values (NaN)")            