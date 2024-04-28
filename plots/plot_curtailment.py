import os
import sys
sys.path.append("../submodules/pypsa-eur")
import pypsa
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
import geopandas as gpd
import cartopy.crs as ccrs
import logging
import colors as c
import warnings
warnings.filterwarnings("ignore")
from _helpers import mock_snakemake, update_config_from_wildcards, load_network, \
                     change_path_to_pypsa_eur, change_path_to_base

logger = logging.getLogger(__name__)

RESULTS_DIR = "plots/results"


def get_curtailment(n, nice_name):
    curtailments = n.statistics()[["Curtailment"]]
    techs = {
             "Solar Rooftop PV": ["solar rooftop"],
             "Solar Utility PV": ["Solar"],
             "Onshore Wind": ["Onshore Wind"],
             "Offshore Wind": ["Offshore Wind (AC)", "Offshore Wind (DC)"]
             }
    
    curtailment_dict = {}

    for name, tech in techs.items():
        curtailment_dict[name] = curtailments[curtailments.index.get_level_values(1).isin(tech)].sum().item()

    curtailment_dict["Total"] = sum(curtailment_dict.values())

    return curtailment_dict


def plot_curtailment(df_curtailment):
    # color codes for legend
    color_codes = {"Optimal Renovation and Heating":"purple", 
                   "Optimal Renovation and Green Heating":"limegreen", 
                   "Limited Renovation and Optimal Heating":"royalblue", 
                   "No Renovation and Green Heating":"#f4b609"}
    
    # MWh to TWh
    df_curtailment = df_curtailment / 1e6

    fig, ax = plt.subplots(figsize=(7, 3))
    for nice_name, color_code in color_codes.items():
        df_curtailment.loc["Total", (slice(None), nice_name)].plot(ax=ax, color=color_code, 
                                                                   linewidth=2, marker='o', label=nice_name)
    unique_years = sorted(set(df_curtailment.columns.get_level_values(0)))
    ax.set_xticks(range(len(unique_years)))  # Set the tick locations
    ax.set_xticklabels(unique_years)  # Set the tick labels
    ax.set_ylabel("Curtailment [TWh]")
    ax.set_xlabel(None)
    ax.legend(loc="upper right", facecolor="white", fontsize='x-small')
    plt.savefig(f"{RESULTS_DIR}/plot_curtailment_{clusters}.png", dpi=600, bbox_inches = 'tight')
    

def define_table_df(scenarios):
    # Define column levels
    col_level_0 = ["2030"]*4 + ["2040"]*4 + ["2050"]*4
    col_level_1 = list(scenarios.values()) * 3
    # Create a MultiColumns
    multi_cols = pd.MultiIndex.from_arrays([col_level_0, col_level_1], names=['Year', 'Scenario'])
    df = pd.DataFrame(columns=multi_cols, index=["Solar Rooftop PV", "Solar Utility PV", 
                                                 "Onshore Wind", "Offshore Wind", "Total"])
    return df


def fill_table_df(df, planning_horizon, scenarios, values):
    for scenario in scenarios.values():
        for tech_name, _ in values.iterrows():
            df.loc[tech_name, (planning_horizon, scenario)] = values.loc[tech_name, scenario]
    return df


if __name__ == "__main__":
    if "snakemake" not in globals():
        snakemake = mock_snakemake(
            "plot_curtailment", 
            clusters="48",
        )
    # update config based on wildcards
    config = update_config_from_wildcards(snakemake.config, snakemake.wildcards)

    # move to submodules/pypsa-eur
    change_path_to_pypsa_eur()

    # network parameters
    co2l_limits = {"2030":"0.45", "2040":"0.1", "2050":"0.0"}
    line_limits = {"2030":"v1.15", "2040":"v1.3", "2050":"v1.5"}
    clusters = config["plotting"]["clusters"]
    planning_horizons = ["2030", "2040", "2050"]
    time_resolution = config["plotting"]["time_resolution"]

    # define scenario namings
    scenarios = {"flexible": "Optimal Renovation and Heating", 
                "retro_tes": "Optimal Renovation and Green Heating", 
                "flexible-moderate": "Limited Renovation and Optimal Heating", 
                "rigid": "No Renovation and Green Heating"}


    # initialize df for storing curtailment information
    curtailment_df = define_table_df(scenarios)

    for planning_horizon in planning_horizons:
        lineex = line_limits[planning_horizon]
        sector_opts = f"Co2L{co2l_limits[planning_horizon]}-{time_resolution}-T-H-B-I"
    
        # load networks
        for scenario, nice_name in scenarios.items():
            n = load_network(lineex, clusters, sector_opts, planning_horizon, scenario)

            if n is None:
                # Skip further computation for this scenario if network is not loaded
                print(f"Network is not found for scenario '{scenario}', planning year '{planning_horizon}', and time resolution of '{time_resolution}'. Skipping...")
                continue
            
            curtailment_dict = get_curtailment(n, nice_name)
            curtailment_df.loc[:, (planning_horizon, nice_name)] = pd.Series(curtailment_dict)
    
    # move to base directory
    change_path_to_base()

    # store to csv and png
    if not curtailment_df.empty:
        # save to csv
        curtailment_df.to_csv(snakemake.output.table)
        # make plot
        plot_curtailment(curtailment_df)