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

DONT_PLOT = ["gas storage"]

PREFIX_TO_REMOVE = [
    "residential ",
    "services ",
    "urban ",
    "rural ",
    "central ",
    "decentral ",
]

RENAME_IF_CONTAINS = [
    "solid biomass CHP",
    "gas CHP",
    "gas boiler",
    "biogas",
    "solar thermal",
    "air heat pump",
    "ground heat pump",
    "resistive heater",
    "Fischer-Tropsch",
]

RENAME_IF_CONTAINS_DICT = {
    "water tanks": "TES",
    "retrofitting": "building retrofitting",
    # "H2 Electrolysis": "hydrogen storage",
    # "H2 Fuel Cell": "hydrogen storage",
    # "H2 pipeline": "hydrogen storage",
    "battery": "battery storage",
    # "CC": "CC"
}

RENAME = {
    "Solar": "solar PV",
    "solar": "solar PV",
    "Sabatier": "methanation",
    "helmeth" : "methanation",
    "Offshore Wind (AC)": "offshore wind",
    "Offshore Wind (DC)": "offshore wind",
    "Onshore Wind": "onshore wind",
    "offwind-ac": "offshore wind",
    "offwind-dc": "offshore wind",
    "Run of River": "hydroelectricity",
    "Run of river": "hydroelectricity",
    "Reservoir & Dam": "hydroelectricity",
    "Pumped Hydro Storage": "hydroelectricity",
    "PHS": "hydroelectricity",
    "NH3": "ammonia",
    "co2 Store": "DAC",
    "co2 stored": "CO2 sequestration",
    "AC": "transmission lines",
    "DC": "transmission lines",
    "B2B": "transmission lines",
    "solid biomass for industry": "solid biomass",
    "solid biomass for industry CC": "solid biomass",
    "electricity distribution grid": "distribution lines",
    "Open-Cycle Gas":"OCGT",
    "gas": "gas storage",
    'gas pipeline new': 'gas pipeline',
    "gas for industry CC": "gas for industry",
    "SMR CC": "SMR",
    "process emissions CC": "process emissions",
    "Battery Storage": "battery storage",
    'H2 Store': "H2 storage",
    'Hydrogen Storage': "H2 storage",
    'co2 sequestered': "CO2 sequestration",
    "solid biomass transport": "solid biomass"
}

PREFERRED_ORDER = pd.Index(
    [
        "nuclear",
        "solid biomass",
        "biogas",
        "gas for industry",
        "coal for industry",
        "methanol",
        "oil",
        "coal",
        "shipping oil",
        "shipping methanol",
        "naphtha for industry",
        "land transport oil",
        "kerosene for aviation",
        
        "transmission lines",
        "distribution lines",
        "gas pipeline",
        "H2 pipeline",
        
        "H2 Electrolysis",
        "H2 Fuel Cell",
        "DAC",
        "Fischer-Tropsch",
        "methanation",
        "BEV charger",
        "V2G",
        "SMR",
        "methanolisation",
        
        "battery storage",
        "gas storage",
        "H2 storage",
        "TES",
        
        "hydroelectricity",
        "OCGT",
        "onshore wind",
        "offshore wind",
        "solar PV",
        "solar thermal",
        "solar rooftop",

        "co2",
        "CO2 sequestration",
        "process emissions",

        "gas CHP",
        "solid biomass CHP",
        "resistive heater",
        "air heat pump",
        "ground heat pump",
        "gas boiler",
        "biomass boiler",
        "building retrofitting",
     ]
)


def rename_techs(label):

    for ptr in PREFIX_TO_REMOVE:
        if label[: len(ptr)] == ptr:
            label = label[len(ptr) :]

    for rif in RENAME_IF_CONTAINS:
        if rif in label:
            label = rif

    for old, new in RENAME_IF_CONTAINS_DICT.items():
        if old in label:
            label = new

    for old, new in RENAME.items():
        if old == label:
            label = new
    return label


def compute_costs(n, nice_name, cost_type):
    assert cost_type in ["Operational", "Capital"], "Type variable must be 'Operational' or 'Capital'"
    costs = n.statistics()[[f"{cost_type} Expenditure"]]
    costs = costs.droplevel(0)
    costs = costs.groupby(costs.index).sum()
    costs.columns = [nice_name]
    return costs


def plot_costs(cost_df, clusters, planning_horizon):
    df = cost_df.groupby(cost_df.index).sum()

    # convert to billions
    df = df / 1e9
    df = df.groupby(df.index.map(rename_techs)).sum()

    costs_threshold = 0.5
    to_drop = df.index[df.max(axis=1) < costs_threshold]  #df <

    logger.info(
        f"Dropping technology with costs below {costs_threshold} EUR billion per year"
    )
    logger.debug(df.loc[to_drop])

    df = df.drop(to_drop)

    logger.info(f"Total system cost of {round(df.sum())} EUR billion per year")

    new_index = PREFERRED_ORDER.intersection(df.index).append(
        df.index.difference(PREFERRED_ORDER)
    )

    for remove_tech in DONT_PLOT:
        new_index = new_index.drop(remove_tech)

    new_columns = df.sum().sort_values().index  


    fig, ax = plt.subplots(figsize=(7, 8))

    df.loc[new_index].T.plot(
        kind="bar",
        ax=ax,
        stacked=True,
        color=[c.tech_colors[i] for i in new_index],
        zorder=1,
    )

    handles, labels = ax.get_legend_handles_labels()

    handles.reverse()
    labels.reverse()

    plt.xticks(rotation=0, fontsize=10)

    ax.set_ylabel("System Cost [EUR billion per year]")

    ax.set_xlabel("")
    ax.set_ylim([0,1100])
    ax.set_yticks(np.arange(0, 1100, 100))

    # Turn off both horizontal and vertical grid lines
    ax.grid(False, which='both')

    ax.legend(
        handles, labels, ncol=1, loc="upper left", bbox_to_anchor=[1, 1], frameon=False
    )
    
    ax.set_facecolor('white')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('black')
    ax.spines['bottom'].set_color('black')
    ax.grid(axis='y', linestyle='--', linewidth=0.5, color='gray', zorder=0)
    plt.savefig(f"{RESULTS_DIR}/plot_total_costs_{clusters}_{planning_horizon}.png", dpi=600, bbox_inches = 'tight')
    

def compute_capacities(n, nice_name):
    capacities = n.statistics()[["Optimal Capacity"]]
    capacities = capacities[capacities.index.get_level_values(0).isin(["Generator","Link","StorageUnit"])]
    full_caps = capacities.sum(axis=1).droplevel(0).to_frame()
    full_caps = full_caps.groupby(full_caps.index).sum()
    full_caps.columns = [nice_name]
    return full_caps


def plot_capacities(caps_df, clusters, planning_horizon):
    df = caps_df.groupby(caps_df.index).sum()

    # drop solid biomass transport
    df = df[df.index != 'solid biomass transport']

    # convert to GW
    df = df / 1e3
    df = df.groupby(df.index.map(rename_techs)).sum()

    caps_threshold = 10
    to_drop = df.index[df.max(axis=1) < caps_threshold]  #df <

    logger.info(
        f"Dropping technology with capacity below {caps_threshold} GW"
    )
    logger.debug(df.loc[to_drop])

    df = df.drop(to_drop)

    logger.info(f"Total optimal capacity is {round(df.sum())} GW")

    new_index = PREFERRED_ORDER.intersection(df.index).append(
        df.index.difference(PREFERRED_ORDER)
    )

    for remove_tech in DONT_PLOT:
        if remove_tech in new_index:
            new_index = new_index.drop(remove_tech)

    new_columns = df.sum().sort_values().index  


    fig, ax = plt.subplots(figsize=(7, 9))

    df.loc[new_index].T.plot(
        kind="bar",
        ax=ax,
        stacked=True,
        color=[c.tech_colors[i] for i in new_index],
        zorder=1,
    )

    handles, labels = ax.get_legend_handles_labels()

    handles.reverse()
    labels.reverse()

    plt.xticks(rotation=0, fontsize=10)

    ax.set_ylabel("Installed capacities [GW]")

    ax.set_xlabel("")
    ax.set_ylim([0,15000])
    ax.set_yticks(np.arange(0, 15000, 2000))

    # Turn off both horizontal and vertical grid lines
    ax.grid(False, which='both')

    ax.legend(
        handles, labels, ncol=1, loc="upper left", bbox_to_anchor=[1, 1], frameon=False
    )
    
    ax.set_facecolor('white')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('black')
    ax.spines['bottom'].set_color('black')
    ax.grid(axis='y', linestyle='--', linewidth=0.5, color='gray', zorder=0)
    plt.savefig(f"{RESULTS_DIR}/plot_total_capacities_{clusters}_{planning_horizon}.png", dpi=600, bbox_inches = 'tight')


def update_capital_cost(cap_cost_df, planning_horizon):
    pass


if __name__ == "__main__":
    if "snakemake" not in globals():
        snakemake = mock_snakemake(
            "plot_total_costs", 
            clusters="48",
            planning_horizon="2030",
        )
    # update config based on wildcards
    config = update_config_from_wildcards(snakemake.config, snakemake.wildcards)


    # network parameters
    co2l_limits = {"2030":"0.45", "2040":"0.1", "2050":"0.0"}
    line_limits = {"2030":"v1.15", "2040":"v1.3", "2050":"v1.5"}
    clusters = config["plotting"]["clusters"]
    planning_horizons = ["2030", "2040", "2050"]
    time_resolution = config["plotting"]["time_resolution"]

    # initialize capital cost storing dictionary for different horizons
    cap_costs_dict = {}
    for planning_horizon in planning_horizons:
        lineex = line_limits[planning_horizon]
        sector_opts = f"Co2L{co2l_limits[planning_horizon]}-{time_resolution}-T-H-B-I"

        # define scenario namings
        scenarios = {"flexible": "Optimal \nRenovation &\nHeating", 
                    "retro_tes": "Optimal \nRenovation &\nGreen Heating", 
                    "flexible-moderate": "Limited \nRenovation &\nOptimal Heating", 
                    "rigid": "No \nRenovation &\nOptimal Heating"}

        # move to submodules/pypsa-eur
        change_path_to_pypsa_eur()
    
        # load networks
        networks = {}
        cap_cost_df = pd.DataFrame()
        op_cost_df = pd.DataFrame()
        capacities_df = pd.DataFrame()
        for scenario, nice_name in scenarios.items():
            n = load_network(lineex, clusters, sector_opts, planning_horizon, scenario)

            if n is None:
                # Skip further computation for this scenario if network is not loaded
                print(f"Network is not found for scenario '{scenario}', planning year '{planning_horizon}', and time resolution of '{time_resolution}'. Skipping...")
                continue

            # calculate capital costs for scenario
            cap_costs = compute_costs(n, nice_name, "Capital")
            cap_cost_df = cap_cost_df.join(cap_costs, how="outer").fillna(0)

            # calculate operational costs for scenario
            op_costs = compute_costs(n, nice_name, "Operational")
            op_cost_df = op_cost_df.join(op_costs, how="outer").fillna(0)

            # calculate capacities for scenario
            capacities = compute_capacities(n, nice_name)
            capacities_df = capacities_df.join(capacities, how="outer").fillna(0)

        # update capital costs based on previous horizons
        cap_costs_dict[planning_horizon] = cap_cost_df
        updated_caps_df = update_capital_cost(cap_cost_df, planning_horizon)


        # add capital and operational costs
        cost_df = cap_cost_df + op_cost_df

        # move to base directory
        change_path_to_base()

        # plot costs
        if not cost_df.empty:
            plot_costs(cost_df, clusters, planning_horizon)

        # plot capacities
        if not capacities_df.empty:
            plot_capacities(capacities_df, clusters, planning_horizon)
