
configfile: "configs/config.plot.yaml"

RESULTS = "plots/results/"


wildcard_constraints:
    space_resolution="[0-9]+",
    planning="[0-9]{4}",


rule plot_total_cost:
    params:
        space_resolution=config["plotting"]["space_resolution"],
        planning=config["plotting"]["planning"],
    output:
        figure=RESULTS+"plot_total_costs_{space_resolution}_{planning}.png",
    resources:
        mem_mb=20000,
    script:
        "plots/plot_total_costs.py"


rule plot_total_costs:
    input:
        expand(
            RESULTS
            + "plot_total_costs_{space_resolution}_{planning}.png",
            **config["plotting"],
        ),


rule plot_electricity_bill:
    params:
        space_resolution=config["plotting"]["space_resolution"],
        planning=config["plotting"]["planning"],
    output:
        figure_bills=RESULTS+"plot_bill_per_household_{space_resolution}_{planning}.png",
        figure_price=RESULTS+"plot_prices_per_MWh_{space_resolution}_{planning}.png",
    resources:
        mem_mb=20000,
    script:
        "plots/plot_electricity_bills.py"


rule plot_electricity_bills:
    input:
        expand(
            RESULTS
            + "plot_bill_per_household_{space_resolution}_{planning}.png",
            **config["plotting"],
        ),
        expand(
            RESULTS
            + "plot_prices_per_MWh_{space_resolution}_{planning}.png",
            **config["plotting"],
        ),


rule get_heat_pump:
    params:
        space_resolution=config["plotting"]["space_resolution"],
    output:
        table=RESULTS+"table_heat_pumps_{space_resolution}.xlsx",
    resources:
        mem_mb=20000,
    script:
        "plots/table_heat_pumps.py"


rule get_heat_pumps:
    input:
        expand(
            RESULTS
            + "table_heat_pumps_{space_resolution}.xlsx",
            **config["plotting"],
        ),


rule get_line_congestion:
    params:
        space_resolution=config["plotting"]["space_resolution"],
    output:
        table=RESULTS+"table_line_congestion_{space_resolution}.xlsx",
    resources:
        mem_mb=20000,
    script:
        "plots/table_line_congestion.py"


rule get_line_congestions:
    input:
        expand(
            RESULTS
            + "table_line_congestion_{space_resolution}.xlsx",
            **config["plotting"],
        ),