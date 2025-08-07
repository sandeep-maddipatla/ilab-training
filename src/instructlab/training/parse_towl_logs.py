import towl.db as tdb
import os

### Create db with Python API
# for x in $(seq 0 7); do echo ------- $x;  python -m towl.db create from-log-file logs/${x}/towl_log.txt -o db/mydb${x} --overwrite; done

### Alternative ways to create db files below
#
# tdb.create_from_log_file(
#    os.path.join(os.environ['HABANA_LOGS'], "0", "towl_log.txt"),
#    "tmpfiles/db",
#    overwrite=True,
#    do_nothing_if_exists=False,
# )
#
# tdb.create_from_log_file(
#    "data/towl_log.txt.xz",
#    "tmpfiles/db",
#    overwrite=True,
#    do_nothing_if_exists=True,
#)

import matplotlib.pyplot as plt

# Good package for browsing DataFrames
import itables

# Configuring matplotlib output size
plt.rcParams['figure.figsize'] = (12, 5)

import towl.user as tu


for x in range(0, 8):
    print(f"Loading scenario {x}...")
    scenario = tu.Scenario(f'db/mydb{x}')
    print('Scenario global time range:', scenario.global_event_timerange)
    global_view = scenario.make_view(scenario.global_event_timerange)
    # shortcut:
    # global_view = scenario.make_global_view()

    global_memory_usage_df = global_view.query_memory_usage()
    print(type(global_memory_usage_df))

    itables.show(global_memory_usage_df)
    with open(f"mem_usage_{x}.html", "w", encoding="utf-8") as f:
        f.write(global_memory_usage_df.to_html())

    compile_events_df = global_view.query_recipe_compile()
    itables.show(compile_events_df)
    with open(f"compile_events_{x}.html", "w", encoding="utf-8") as f:
        f.write(compile_events_df.to_html())

    tu.plots.plot_memory_usage(global_view)
    if os.path.exists('plot.png'):
        os.rename('plot.png', f'plot_{x}.png')
        print(f"Renamed plot.png to plot_{x}.png")