# python3.12 ./36_5_RRG/run_sweep_load.py
# python3.12 ./36_5_RRG/run_nexu_sweep_load.py
# python3.12 ./36_5_DDF/run_sweep_load.py
# python3.12 ./36_5_DDF/run_nexu_sweep_load.py
# python3.12 ./32_6_Slimfly/run_sweep_load.py
# python3.12 ./32_6_Slimfly/run_nexu_sweep_load.py

# python3.12 run_experiment.py --path_dict ASP --V 32 --D 6 --topo_name Slimfly
python3.12 run_experiment.py --path_dict nexullance --V 32 --D 6 --topo_name Slimfly

# python3.12 run_experiment.py --path_dict ASP --V 36 --D 5 --topo_name DDF
python3.12 run_experiment.py --path_dict nexullance --V 36 --D 5 --topo_name DDF

# python3.12 run_experiment.py --path_dict ASP --V 36 --D 5 --topo_name RRG
python3.12 run_experiment.py --path_dict nexullance --V 36 --D 5 --topo_name RRG
