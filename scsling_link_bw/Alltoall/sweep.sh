#!/bin/bash

# List of LOAD values to sweep through
Link_BWs=(2 4 8 16 32 64)

for BW in "${Link_BWs[@]}"; do
    sed -i "s/UNIFIED_ROUTER_LINK_BW=.*/UNIFIED_ROUTER_LINK_BW=$BW/" ECMP_ASP.py
    sst -n 16 ECMP_ASP.py
done

for BW in "${Link_BWs[@]}"; do
    sed -i "s/UNIFIED_ROUTER_LINK_BW=.*/UNIFIED_ROUTER_LINK_BW=$BW/" UGAL.py
    sst -n 16 UGAL.py
done


# python3 get_data.py