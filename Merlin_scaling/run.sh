python3 run_scaling_experiments.py --traffic-pattern 'shift_half' --load 0.8 --num-threads 6 --topo-name Slimfly
python3 run_scaling_experiments.py --traffic-pattern 'uniform' --load 0.8 --num-threads 6 --topo-name Slimfly

python3 run_scaling_experiments.py --traffic-pattern 'uniform' --load 0.8 --num-threads 6 --topo-name DDF
python3 run_scaling_experiments.py --traffic-pattern 'shift_half' --load 0.8 --num-threads 6 --topo-name DDF

python3 run_scaling_experiments.py --traffic-pattern 'uniform' --load 0.8 --num-threads 6 --topo-name Polarfly
python3 run_scaling_experiments.py --traffic-pattern 'shift_half' --load 0.8 --num-threads 6 --topo-name Polarfly