#!/bin/bash

# n=500
# CPE=8

echo "Running ECMP_ASP"
# sed -i "s/_n=.*/_n=$n/" ECMP_ASP.py
# sed -i "s/CPE=.*/CPE=$CPE/" ECMP_ASP.py
sst -n 16 ECMP_ASP.py

echo "Running UGAL_ASP"
# sed -i "s/_n=.*/_n=$n/" UGAL.py
# sed -i "s/CPE=.*/CPE=$CPE/" UGAL.py
sst -n 16 UGAL.py

echo "Running Nexu_MP_APST4"
# sed -i "s/_n=.*/_n=$n/" Nexu_MP_APST4.py
# sed -i "s/CPE=.*/CPE=$CPE/" Nexu_MP_APST4.py
sst -n 16 Nexu_MP_APST4.py
