import os
import sys
sys.path.append("../submodules/pypsa-eur")
import pypsa
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
from _helpers import mock_snakemake, update_config_from_wildcards, load_network, \
                     change_path_to_pypsa_eur, change_path_to_base, \
                     LINE_LIMITS, CO2L_LIMITS, BAU_HORIZON


if __name__ == "__main__":
    if "snakemake" not in globals():
        snakemake = mock_snakemake(
            "get_line_congestion", 
            clusters="48",
        )
    # update config based on wildcards
    config = update_config_from_wildcards(snakemake.config, snakemake.wildcards)


    # move to submodules/pypsa-eur
    change_path_to_pypsa_eur()
    # network parameters
    co2l_limits = CO2L_LIMITS
    line_limits = LINE_LIMITS
    clusters = config["plotting"]["clusters"]
    time_resolution = config["plotting"]["time_resolution"]
    planning_horizons = config["plotting"]["planning_horizon"]
    planning_horizons = [str(x) for x in planning_horizons if not str(x) == BAU_HORIZON]
    opts = config["plotting"]["sector_opts"]

    # define scenario namings
    scenarios = {"flexible": "Optimal Renovation and Heating", 
                 "retro_tes": "Optimal Renovation and Green Heating", 
                 "flexible-moderate": "Limited Renovation and Optimal Heating", 
                 "rigid": "No Renovation and Green Heating"}

    # define dataframe to store grid congestion
    df_congestion = pd.DataFrame(index=list(scenarios.values()), columns=["2030", "2040", "2050"])

    # line congestion estimation
    for planning_horizon in planning_horizons:
        lineex = line_limits[planning_horizon]
        sector_opts = f"Co2L{co2l_limits[planning_horizon]}-{time_resolution}-{opts}"

        for scenario, nice_name in scenarios.items():
            # load networks
            n = load_network(lineex, clusters, sector_opts, planning_horizon, scenario)

            if n is None:
                # Skip further computation for this scenario if network is not loaded
                print(f"Network is not found for scenario '{scenario}', planning year '{planning_horizon}', and time resolution of '{time_resolution}'. Skipping...")
                continue

            # estimate upper and lower limits of congestion of grid
            upper = n.lines_t.mu_upper.multiply(n.snapshot_weightings.stores, axis=0).mean().multiply(n.lines.length).mean()
            lower = n.lines_t.mu_lower.multiply(n.snapshot_weightings.stores, axis=0).mean().multiply(n.lines.length).mean()
            congestion = (upper + lower) / 2
            df_congestion.loc[nice_name, planning_horizon] = round((congestion / 1e6), 2)

    # add name for columns
    df_congestion.index.name = "Scenario [m. Eur/MW]"

    # move to base directory
    change_path_to_base()

    # save the heat pumps data in Excel format
    df_congestion.to_csv(snakemake.output.table)

