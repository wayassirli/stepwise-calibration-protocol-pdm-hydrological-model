## 1 Introduction
### Probability Distributed Model (PDM)
Probability Distributed Model (Moore, 2007) is a lumped, conceptual rainfall-runoff model, where the spatial variability of the soil storage is represented by probability distribution. It is a saturation-excess model with baseflow and quick flow as the sub-component.

### Step-wise calibration protocol
The step-wise calibration protocol (Vansteenkiste, 2014) is a calibration approach in which parameters controlling different hydrological process are calibrated sequentially against multiple derived information relevant to each process. This protocol is adapted from top-down modelling approach (Willems, 2014) and implemented to five different hydrological models including the PDM. 

### Tool overview
This tool facilitates the manual step-wies calibration protocol by automatically generating the evaluation indicators (statistical indices and plots) of multiple PDM simulation output  against different calibration targets. The configurations of calibration are defined through Excel configuration files, while the execution is with command-line arguments via anaconda prompt. 

## 2 Installation
Download this repository and install the required Python packages.
```bash
pip install pandas numpy matplotlib openpyxl
```

## 3 Project Structure
The project is organized into the following folders and files. No additional folders need to be created. The project contains three main folders `observation/`, `simulation/`, and `calibration/`. Each folder contains a configuration Excel file that serves a different purpose. The `observation/` and `simulation/` folders store two types of input data required for the calibration: observation time-series and simulation output time-series.  
```text
│
├── README.md
├── sourcecode/
│   ├── calibration.py
│   └── main.py
│   └── observation.py
│   └── plot.py
│   └── simulation.py
│
├── observation/
│   ├── config_observations.xlsx
│   └── observations/
│       └── [observation time-series files]
│
├── simulation/
│   ├── config_simulations.xlsx
│   └── simulationoutput/
│       └── [InfoWorks simulation output files]
│
└── evaluation/
    ├── config_periods.xlsx
    └── plot/
        └── [calibration plots]
```

### 3.1 Evaluation folder
The `evaluation/` folder contains `plot/` subfolder and `config_periods.xlsx` Excel.<br>The `plot/` subfolder contains the result of different submodel and overall evaluation plots.<br>The `config_calibration.xlsx` Excel defines the calibration period, including the start and end dates of the simulation period to be evaluated. It also specifies the quick and slow flow period associated with each calibration period.  

### 3.2 Observation folder
The `observation/` folder contains `observations/` subfolder and `config_observations.xlsx` Excel.

Place all the observation time-series for all catchments required for the calibration in the `observations/` subfolder. The required observation data for each catchment are rainfall, ETp, flow, baseflow, quickflow. The time-series data must be in `xlsx` format. Name the date and time column `“Timestamp”` and the data column `“Value”`.Timestamp must be in `DD/MM/YYYY HH:MM` format. The expected unit are mm for rainfall and evapotranspiration, and m³/s for flow. The temporal resolution of rainfall and flow should be the same. ETp can have a different temporal resolution and should be monthly or finer. 

The `config_observations.xlsx` Excel is used to assign the associated observation time-series (e.g. rainfall, ETp, flow) to each catchment. The same observation time-series can be assigned to different catchments, for example, nearby catchments can use the same ETp data.

### 3.3 Simulation folder
The `simulation/` folder contains `simulationoutput/` subfolder and `config_simulations.xlsx` Excel.

Place all the simulation output files in the `simulationoutput/` subfolder. For each simulation, export `Actual evapotranspiration [pdm_evaporation]` together with `Soil moisture deficit [pdm_smd]` together in one file, and `Surface flow [pdm_surfaceflow]` together with `Rainfall-driven Baseflow [pdm_baseflow]` in one file. The ETa and SMD file is used for the calibration of the ETa and soil sub-model, while the quick flow and baseflow file is used for the calibration of runoff related sub-models.

The `config_simulations.xlsx` Excel contains `simulation_id`, an identifier for the parameter set used to produced the corresponding simulation output. The Excel then defines which sub-model performance is evaluated using this simulation output, for which catchment, and within which calibration period. The same simulation output can be used to evaluate the performance of different sub-models, for example, a simulation output can be used to evaluate soil storage and runoff sub-model performance.

## 4 Configuration
The calibration of simulation output is configured through the three Excels in which their own responsibilities explained in the previous section.
**Cell colour convention**<br>
🟩 **Green cells** Input required for the code to run<br>
🟦 **Blue cells** Information Only (code would run with or without a value, but information is useful for context)<br>
🟥 **Red cells** Customization for Box-Cox plotting
⬜ **Grey cells** Automatically filled, do not modify. If your simulation exceeds the pre-filled 5000 rows, drag the formula down as required. 

### 4.1 Calibration Configuration
**Excel: 'calibration_config.xlsx'**  
**Sheet 1: 'simulation_periods'**
| Column | Cell | Type | Description |
|---|---|---|---|
| `catchment` | 🟩 | String | Write the name of the catchment to be calibrated or evaluated. The catchment name must be consistent across configuration files. It is used as an argument when running the program to filter which catchment to be evaluated. It is also used in Figure title. |
| `start_date` | 🟩 | DateTime<br>(DD/MM/YYYY HH:MM) | Write the start of the evaluation period, excluding warm up period. It is used to extract the time-series data evaluated, and as the Date/x-axis in the plots. |
| `end_date` | 🟩 | DateTime<br>(DD/MM/YYYY HH:MM) | Write the end of the evaluation period.It is used to extract the time-series data evaluated, and as the Date/x-axis in the plots.
| `period_id` | 🟩 | String | Write a unique identifier for the period in which the simulation is to be evaluated (e.g. `Jan21-Jan25`), refering to the period defined by start_date and end_date. The `period_id` value must be consistent across configuration files. It is used as an argument when running the program to filter which period the simulations to be evaluated. |
| `period_type` | 🟦 | String | Specify whether this simulation period is calibration or validation |
| `original_start_date` | 🟦 | String | Specify the original start date of the simulation file, including the warm up period. |
| `warm_up` | 🟦 | String | Specify the duration of the warm up period, excluded from the evaluation. |

**Sheet 2: 'flow_periods'**
Each catchment will have quick and flow period. Multiple rows with the same catchment and flow_type corresponds to the number of events that the catchment and the flowtype has, each cell represent the start time-step of that period.
| Column | Cell | Type | Description |
|---|---|---|---|
| `start_timestep` | 🟩 | Integer | Copy the starting time-step of each quick and slow flow event of one simulation period generated by WETSPRO into this column. The number of rows corresponds to the number of quick and slow flow events identified for the associated simulation period. |
| `flowperiod_type` | 🟩 | String | Enter “quick” for quick flow events and “slow” for slow flow events. Specify a flow type for every start_timestep, do not leave any cells blank. Together with start_timestep, this column is used to define the flow periods over which rainfall depth and flow volume are accumulated for sub-model calibration. |
| `catchment` | 🟩 | String | Write the name of the catchment to which the previous quick/slow flow periods belongs. The catchment name must be consistent across configuration files. |
| `period_id` | 🟩| String | Write the `period_id` in which the quick/slow flow events are extracted.<br>The `period_id` value must be consistent across configuration files. |

### 4.2 Observation Configuration
**Excel: 'observation_config.xlsx'**  
Each row corresponds to the information of one catchment including its size and metadata of the associated hydrological time-series.
| Column | Cell | Type | Description |
|---|---|---|---|
| `catchment` | 🟩 | String | Write the name of the catchment that the following observation time-series belongs to. The catchment name must be consistent across configuration files. |
| `catchment_size_m2` | 🟩 | Float | Specify the catchment size in squared meters unit. |
| `rainfall_filename` | 🟩 | String | Write the filename of the rainfall time-series associated for your catchment, including the .xlsx file extension (e.g. `rainfall_thiessen.xlsx`). |
| `rainfall_freq` | 🟩 | String | Write the frequency of the rainfall time-series using the format `number + unit` , (e.g. `15min`, `2H`, `1D`, `3M`). |
| `ETp_filename` | 🟩 | String | Write the filename of the ETp time-series associated for your catchment, including the .xlsx file extension (e.g. `ETp_station1.xlsx`). |
| `ETp_freq` | 🟩 | String | Write the frequency of the ETp time-series using the format `number + unit` , (e.g. `15min`, `2H`, `1D`, `3M`). |
| `flow_filename` | 🟩 | String | Write the filename of the flow time-series associated for your catchment, including the .xlsx file extension (e.g. `flow_station1.xlsx`). |
| `flow_freq` | 🟩 | String | Write the frequency of the flow time-series using the format `number + unit` , (e.g. `15min`, `2H`, `1D`, `3M`). |
| `baseflow_filename` | 🟩 | String | Write the filename of the baseflow time-series associated for your catchment, including the .xlsx file extension (e.g. `baseflow_station1.xlsx`). |
| `baseflow_freq` | 🟩 | String | Write the frequency of the baseflow time-series using the format `number + unit` , (e.g. `15min`, `2H`, `1D`, `3M`). |
| `quickflow_filename` | 🟩 | String | Write the filename of the quickflow time-series associated for your catchment, including the .xlsx file extension (e.g. `quickflow_station1.xlsx`). |
| `quickflow_freq` | 🟩 | String | Write the frequency of the quickflow time-series using the format `number + unit` , (e.g. `15min`, `2H`, `1D`, `3M`). |

### 4.3 Simulation Configuration
**Excel: 'simulation_config.xlsx'**  
**Sheet 1: scenarios**
| Column | Cell | Type | Description |
|---|---|---|---|
| `simulation_id` | 🟩 | String | Write the unique identifier for your simulation, as a combination of your catchment, the period you simulated it, and your parameter set |
| `catchment` | 🟩 | String | Write the name of the catchment that the simulation output belongs to. The name must match the `catchment` value in the other configuration files. |
| `period_id` | 🟩 | String | Write the `period_id` in which the simulation is to be evaluated. The `period_id` value must be consistent across configuration files. It is used to select the part of the simulation between the corresponding `start_date` and `end_date` for evaluation.|
| `stage` | 🟩 | String | Specify the stage of model calibration and evaluation procedure. Specify `submodel` to calibrate submodel(s) against a calibration target, or `overall` to evaluate the overall performance of the parameter set |
| `calibration_targets` | 🟩 | String | Specify calibration target to evaluate the performance of the simulation (parameter set). Specify the field when the `stage` is set to `submodel`. The available calibration targets are `recession`, `ETa`, `soil`, `runoff`. The same simulation can be calibrated aganist different targets, in which case, you have to wrote it twice in different rows. |
| `evaluation_method` | 🟩 | String | Specify the evaluation method used to assess the overall model performance. This field applies only when `stage` is set to `overall`. The available evaluation methods are `statistics` and `waterbalance`. |
| `flowtype` | 🟩 | String | Specify the flowtype to be calibrated/evaluated (`QF`, `BF`, or `TF`). |
| `ETa_soilmoisture_filename` | 🟩 | String | Write the filename of the ETa and soil moisture time-series associated with your simulation_id, including the InfoWorks output file extension (e.g. `ETa_soilmoisture_sim1.csv`). Enter when calibrating ETa or soil  storage sub-model, leave empty otherwise. |
| `baseflow_quickflow_filename` | 🟩 | String | Write the filename of the quick flow and baseflow time-series associated with the simulation_id, including the InfoWorks output file extension (e.g. `QF_BF_sim1.csv`). Enter the filename when calibrating runoff related storage sub-models, leave empty otherwise. |
| `λSWd` | 🟥 | Float | Enter the Box-Cox parameter λ value (0-1) when calibrating soil storage sub-model |
| `λBF` | 🟥 | Float | Enter the Box-Cox parameter λ value (0-1) when calibrating recharge sub-model |
| `λQF` | 🟥 | Float | Enter the Box-Cox parameter λ value (0-1) when calibrating runoff sub-model |

**Excel: 'simulation_config.xlsx'**  
**Sheet 2: parameters**  
Each row represents one simulation scenario, where you simulated a parameter set.  
| Column | Cell | Type | Description |
|---|---|---|---|
| `simulation_id` | ⬜ | String | Mirrors `simulation_id` value on simulations sheet |
| `stage` | ⬜ | String | Mirrors `stage` value on simulations sheet |
| `calibration_target` | ⬜ | String | Mirrors `calibration_target` value on simulations sheet |
| `evaluation_method` | ⬜ | String | Mirrors `evaluation_method` value on simulations sheet |
| `flowtype` | ⬜ | String |  |
| `ET_params1` | 🟩 | Float | `ET_params1` is the evapotranspiration exponent parameter value you choose for this simulation scenario. You will calibrate by simulating multiple exponent values (e.g. 1.5, 2, 2.5, 3). `ET_params1` value will be used as legends in your ET calibration plot. |
| `soil_function` | 🟩 | String | Specify which distribution you choose (Pareto, triangular, or rectangular). This will be used to select the formula to calculate `Smax`. |
| `soil_params1` | 🟩 | String | Specify the `cmin` parameter value you choose for this simulation scenario. |
| `soil_params2` | 🟩 | String | Specify the `cmax` parameter value you choose for this simulation scenario. |
| `soil_params3` | 🟩 | String | Specify the `b` parameter value you choose for this simulation scenario. |
| `recharge_function` | 🟦 | String | Specify which recharge function you choose (`Standard`, `Demand-based`, or `Splitting`) |
| `recharge_params1` | 🟦 | Float | Specify the first parameter value you choose for this scenario (for `Standard` function, specify `kg`; for `Demand-based` and `Splitting` Function, specify `α`) |
| `recharge_params2` | 🟦 | Float | Specify the second parameter value you choose for this scenario (for `Standard` function, specify `bg`; for `Demand-based`, specify `β`) |
| `recharge_params3` | 🟦 | Float | Specify the third parameter value you choose for this scenario (for `Standard` function, specify `St`; for `Demand-based`, specify `qsat`) |
| `baseflow_routing_function` | 🟦 | String | Specify which baseflow routing function you choose (`Linear` or `Groundwater` routing) |
| `baseflow_routing_params1` | 🟦 | Float | Specify the first parameter value you choose for this scenario (for `Linear` routing, specify `KBF`; for `Groundwater` routing, specify `kb`) |
| `baseflow_routing_params2` | 🟦 | Float | Specify the `m` parameter value of the `Groundwater` routing sub-model you choose for this scenario |
| `quickflow_routing_function` | 🟦 | String | Specify which quickflow routing function you choose (`Linear` or `Cascade` routing) |
| `quickflow_routing_params1` | 🟦 | Float | Specify the first parameter value you choose for this scenario (for `Linear` routing, specify `KQF`; for `Cascade` routing, specify `k1`) |
| `quickflow_routing_params2` | 🟦 | Float | Specify the `k2` parameter value of the `Cascade` routing sub-model you choose for this scenario |
| `params1` | 🟦 | Float | Specify the time delay/`td` parameter value you choose for this scenario |
| `params2` | 🟦 | Float | Specify the rainfall factor parameter value you choose for this scenario |

## 3. Usage
Following the step-wise protocol, each sub-model will be calibrated one at a time, by evaluating the performance of different parameter sets/simulations at once. This is executed using command-line argument in the Anaconda prompt. Navigate to the project directory before executing the command. 
```bash
cd path/to/calibrationtools
python main.py <catchment> <period_id> <stage> <calibration_target/evaluation_method> [flowtype]
```
1 `catchment`<br>
Write the name of catchment to be calibrated or evaluated. It must match the `catchment` name in the  configuration files. The argument selects the catchment and its associated configuration information for evaluation.<br>
2 `period_id`<br>
Write the unique identifier of the period the simulations to be evaluated. It must match the `period_id` value in the configuration files. The arguments selects the period to be evaluated and its associated configuration information.<br>
3 `stage`<br>
Write `submodel` to evaluate simulations against a calibration target, or `overall` to evaluate their overall performances.<br>
4 `calibration_target`<br>
When `stage` = `submodel`, write one out of the following calibration targets `recession`, `ET`, `soil`, `runoff` for submodel calibration.<br>
5 `evaluation method`<br>
When `stage` = `overall`, write either `statistics` or `waterbalance` for overall performance evaluation.<br>
6 `flowtype`<br>
Write `QF`, `BF`, or `TF` if the calibration or evaluation is to be executed only for a specific type of flow.<br>

## 4. Output/Examples

## 5. Methodology
The methodology is based on Vansteenkiste, 2014 and additional processing time-series based on Willems, 2009. 
### 5.1 Probability Distributed Model (PDM)
The PDM model structure consists of four following submodels.<br>

**The evapotranspiration (ET) submodel** simulates actual evapotranspiration as limited by the soil moisture. The one parameter evapotranspiration exponent controls how the ratio of actual to potential ET responds to soil moisture.<br>

**The routing submodels** simulate the timing of subflow components. The original PDM configuration implements cascade linear reservoir routing for quick flow component and groundwater routing for baseflow component. PDM also offers linear reservoir routing as an alternative for both subflow components. Each routing submodel has a different number of time-related parameters (see config_simulations.xlsx) that controls the shape of the subflow hydrograph.<br>

**The soil storage submodel** simulates the depth of water held in soil storages across the catchment. The soil storage varies spatially across the catchment, which is characterised by probability distribution. This soil storage capacity determines when soil is saturated and excess water is produced. PDM provides different probability distribution models, including pareto, triangular, and rectangular. The three soil storage parameters (see config_simulations.xlsx) controls the probability distribution of the soil storage.<br>

**The recharge submodel** simulates the amount of water directed to the groundwater storage before being routed as baseflow, which is referred to as recharge or dᵢ. PDM provides three different recharge model, including standard, demand-based and splitting. For the standard and demand-based models, recharge is drawn directly from the water in the soil storage, reducing the soil water depth. This is described in the following equation:<br>
$$ 
πᵢ = Pᵢ − E′ᵢ − dᵢ
$$
where πᵢ is net rainfall that contributes to water in the soil storage, Pᵢ is total rainfall, and E′ᵢ as evapotranspiration. For the splitting model, dᵢ = 0. Instead, the amount of recharge as well as runoff (the amount of water directed to surface storage) are drawn from the excess water proeduced by the saturated soil storages. The parameters for each model control how much water is allocated into recharge according to their own mechanism.

### 5.2 Time-series Pre-processing
Prior to calibration and evaluation, hyrological time-series are pre-processed using WETSPRO (Willems, 2009), resulting in derived information used throughout the calibration and evaluation processes. WETSPRO is used to filter flow into quick flow and baseflow components, extract POT high flows, as well as near-independent quick and slow flow events.

### 5.3 Step-wise Calibration Protocol 
The sequence of step-wise protocol implemented for PDM are divided into multiple calibration targets. The structure of VHM modelling approach (Willems, 2014a) allows clear one-on-one sequential calibration between submodels and target variables. However, difference in the conceptualization and representation of hydrological processes in PDM, particularly the stronger interactions between hydrological processes mean that sometimes, one calibration target is used to evaluated multiple sub-models at once. For instance, while the soil moisture and runoff in VHM are separately represented with different submodels, they are both represented explicitly by soil storage submodel in PDM. VHM also did not explicitly parameterize recharge while PDM does. The following sections describe the calibration targets and how the PDM submodels are calibrated against them. <br>

**Recession**<br>
The recession characteristics of the flow hydrograph are used to calibrate the routing submodels. When the linear reservoir model is selected, the calibrated recession constants from WETSPRO can be directly applied here. When the original PDM routing models are selected, the parameters can be calibrated by matching the shape of the subflow components from the WETSPRO filter results.

**ET**<br>
Evapotranspiration-related variables are used to calibrate the evapotranspiration (ET) model. The one parameter (ET exponent) is calibrated according to the expected monthly or seasonal ratio between the actual and potential ET. For example, in temperate regions like Belgium, ET is almost at potential rate during winter, while in summer it remains below the potential rate.

**Soil**<br>
Soil water variation, specifically slow-flow event-based accumulated soil water depth, is used as calibration targets of multiple submodels depending on how the recharge model is configured. 
When standard or demand-based model is selected, recharge or dᵢ directly influences soil water variation. Therefore, soil water variation becomes a calibration target for both soil storage model and recharge submodels.
When splitting model is selected, recharge and runoff runoff are both drawn from the excess water once the soil storage is saturated. Therefore, soil water variations is primarily used to calibrate soil storage model. In addition, water balance of total flow is also recommended as a target variable to evaluate soil storage model. The total flow volume is directly informative to the soil storage model performance in representing excess water generated when soil storage is saturated.

**Runoff**<br>
In contrast, VHM does not explicitly parameterize a recharge model.* 
Runoff, specifically quick-flow event-based accumulated runoff, is a calibration target of multiple submodels that also depends on how recharge model is configured.
When standard or demand-based model is selected, runoff also becomes the calibration target for both soil storage and recharge submodel. Recharge, or dᵢ, influences the amount of water stored in the soil storage, while the resulting soil storage saturation influence the amount of excess water that goes into runoff.
When Splitting model is selected, excess water are splitted into runoff and recharge. Therefore, the quick flow runoff volume is primarly used to calibrate the splitting parameters.

### 5.4 Overall Performance Evaluation
After all submodels are sequentially calibrated, multiple candidate parameter sets are evaluated using the following methods. This tool does not implement the evaluation procedure described in Sections 3.4.3 and 3.4.4 of Vansteenkiste, 2014.<br>

**Statistics**<br>
The statistical indices evaluates the performance of the simulated flow and subflow time-series against the observed/empirical values. The statistical indices include root mean squarred error (RMSE), mean absolute error (MAE), and Nash-Sutcliffe efficiency (NSE). Beside the statistical indices, the shape of flow and subflow time-series as well as their peak should be evaluated visually.<br>

**Water balance**<br>
Water balance evaluates whether the simulation produces a similar runoff volume compared to the observed one. Water balance deficit (WBD) indicates the accumulated difference between the simulation and the observation over the evaluation period.<br> 

## 6. References

Moore, R. J. (2007). The PDM rainfall-runoff model. Hydrology and Earth System Sciences, 11(1), 483–499. https://doi.org/10.5194/hess-11-483-2007

Vansteenkiste, T., Tavakoli, M., Van Steenbergen, N., De Smedt, F., Batelaan, O., Pereira, F., & Willems, P. (2014). Intercomparison of five lumped and distributed models for catchment runoff and extreme flow simulation. Journal of Hydrology, 511, 335–349. https://doi.org/10.1016/j.jhydrol.2014.01.050

Willems, P. (2009). A time series tool to support the multi-criteria performance evaluation of rainfall-runoff models. Environmental Modelling & Software, 24(3), 311–321. https://doi.org/10.1016/j.envsoft.2008.09.005


Willems, P. (2014). Parsimonious rainfall–runoff model construction supported by time series processing and validation of hydrological extremes – Part 1: Step-wise model-structure identification and calibration approach. Journal of Hydrology, 510, 578–590. https://doi.org/10.1016/j.jhydrol.2014.01.017


### Notes<br>
#### add prints in anaconda prompt during/after calibration?<br>
#### add error warnings, a must for "column name in PDM output file doesnt match"<br>
#### add error warnings, not enough slow flow periods, minimum 3, box cox linear interpolation line requires 2 points.
#### create dummy/demonstrative datasets, for output examples

