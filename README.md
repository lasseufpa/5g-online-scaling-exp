# 5g-online-scaling-exp
# Online_Scaling

## Installation

### Conda Environment Configuration

This project utilizes an isolated Python environment managed by Conda. Follow the instructions below to properly set up the environment called online_scaling and install the dependencies from the `requirements.txt` file.

#### Environmental Information
- Supported Python versions: 3.6 - 3.9
- Tested systems: Ubuntu 22.04 and Ubuntu 24.04

#### 1. Install Miniconda or Anaconda

If you do not already have Conda installed, go to the official website and follow the installation instructions for your operating system:

[Conda Installation Guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)

#### 2. Create Conda environment
In the terminal run:

```bash
conda create -n online_scaling python=3.9 -y
```

#### 3. Activate the environment
```bash
conda activate online_scaling
```

#### 4. Install dependencies
Make sure you are in the root of the project (where the requirements.txt file is) and run:

```bash
pip install -r requirements.txt
```

## Creating predictions

This project implements an online regression model evaluation pipeline using the River library for temporal data. The goal is to compare the performance of different algorithms in tasks of continuous prediction of the number of control requests for an AMF function. At the end, a file containing the results of the evaluation metrics (MAE, RMSE, inference time, learning time, and model size) will be generated for each cluster, in addition to files containing the prediction and the real value of requests for each time instant for the different clusters.

To start the evaluation process, open the Models.ipynb notebook in your preferred editor (e.g., Jupyter, VS Code) and execute its cells sequentially to perform training, online prediction, and metrics logging for each cluster.

## Simulation

To facilitate efficient simulation running, we have developed the `run.py` script, which automates and parallelizes the simulation of multiple agents based on the model's results. At the end of the process, the results are automatically saved in a folder named `output`.

Even if you have no previous experience with Python or simulations, this guide is designed to help you get everything running smoothly.

### Organization of input files

Before running the script, it is important to understand how the files should be organized.

For this project, the results of the **top 5 models are already available** and should be used as input for the simulation.

All input files should be inside a folder called `input/`. Each .csv file represents the results of a specific model applied to a specific cluster.

#### File name format:
```bash
ModelName_Clusternumber.csv
```
- **ClusterName**: Name of the algorithm or approach used (e.g. BLR, EWA, etc.)
- **CLUSTER**: Number of the cluster to which that file refers (e.g.: 0, 1, 2, ...).

Examples:
```bash
BLR_0.csv
BLR_1.csv
EWA_0.csv
EWA_1.csv
```
This naming pattern is essential because the `run.py` script uses it to identify and group files correctly by model.

#### Model output
After the simulations are completed, the results will be **automatically stored** in the `output/` folder. If this folder does not yet exist, there **is no need to create it manually** — the simulator itself will create it during execution.

For each simulation performed, multiple output files are generated with detailed information. The files are named as follows:

- ClusterName_amf_utilization.csv
- ClusterName_ON_amfs_log.csv
- ClusterName_unallocated_requests.csv
- ClusterName_states_log.txt

These files contain detailed metrics and logs about the behavior of the simulated system, including AMF usage, unallocated requests, and internal states recorded throughout the execution.

It is worth noting that in addition to the results obtained by the models, there will also be results from an ideal simulation of the events, that is, a simulation that predicts all requests with all the established parameters. The results of this execution are saved with the Ideal_ prefix and follow the same structure as the model outputs.

### Running the Simulation

After organizing the .csv files inside the input/ folder, follow the steps below to start the simulation:

1. Open the command prompt and navigate to the directory where the `run.py` file is located.
2. Run the following command:
```bash
python3 run.py
```
This command automatically performs the following steps:

- Reading all files in the `input/` folder;
- Grouping files by model, based on the part before the _ character in the file name;
- Parallel execution of the `simulator.py` script for each `.csv` file;
- Re-execution in ideal mode for the files of the first model identified, to enable comparison between the ideal results and those obtained by the evaluated models;
- Storing all output files generated in the `output/` folder in an organized and automatic manner.

### Customizing the execution
To customize the execution, such as changing the number of simulations that will be executed in parallel, you can change some parameters of the ru.py file, such as:

```python3
INPUT_DIR = "input" # Folder with the .csv files
SIMULATOR = "simulador.py" # Script that will be executed for each simulation
MAX_WORKERS = 5 # Number of simulations executed at the same time
```

### Adjusting Simulation Parameters
In addition to the settings available in `run.py`, it is possible to customize the internal behavior of the simulation by modifying variables defined directly in the `simulator.py` file.

These parameters control the operation of the AMFs (Access and Mobility Management Functions) during the simulation, allowing you to simulate different load and adaptation scenarios.

Below, we explain the main parameters that can be adjusted:
```python3
requests_per_second = 20
```
Defines **the number of requests per second that each AMF can handle**. Increasing this value means that the AMF instance will be able to handle a larger number of requests.

```python3
utilization_percentage = 80
```
Sets the p**ercentage utilization threshold** that each AMF can reach before a new instance must be created. For example, if this value is `80`, new AMFs will be created as soon as existing ones exceed 80% of their capacity, promoting load balancing.

```python3
time_exec = 10
```
Represents the time interval between each simulation step, in minutes. A value of `10` indicates that each simulation cycle occurs every 10 minutes.

```python3
life = 2
```
Controls the **lifetime of inactive AMFs**. When an instance is no longer needed, it is **not shut down immediately**. Instead, its life counter is gradually decremented. If it reaches zero, the instance is shut down. This behavior allows for a smoother transition and prevents premature shutdowns.

```python3
damage = 1
```
Sets the decrement value of the `life` counter at each simulation step. Together with the previous parameter, it controls the **speed at which an inactive AMF is deactivated**.

## Evaluating models

In addition to the results obtained by the simulation, the "Simulator" folder also contains Jupyter Notebook files for extracting certain metrics. These are divided into 2, namely:

1. **Model**: This notebook performs statistical and visual analysis of the residual errors of regression models applied to different data clusters. It automates reading the prediction files saved in the input folder, calculates error metrics, generates cumulative visualizations (CDFs), and exports the results in usable formats. 

2. **Simulation**: This notebook analyzes the simulated results of request allocation in AMFs, automatically reading the files generated by the simulations to evaluate metrics such as unallocated requests, AMF utilization, and number of active AMFs. It compares the performance of different regression models about an ideal scenario, calculates absolute and percentage deviations, generates graphs of service by cluster over time, and produces detailed reports with the main statistics and prediction errors.


