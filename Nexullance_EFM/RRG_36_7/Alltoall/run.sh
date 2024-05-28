#!/bin/bash

n=16384
CPE=2

echo "Running ECMP_ASP"
sed -i "s/bytes=.*/bytes=$n\"/" ECMP_ASP.py
sed -i "s/CPE=.*/CPE=$CPE/" ECMP_ASP.py
sst -n 10 ECMP_ASP.py

echo "Running UGAL_ASP"
sed -i "s/bytes=.*/bytes=$n\"/" UGAL.py
sed -i "s/CPE=.*/CPE=$CPE/" UGAL.py
sst -n 10 UGAL.py

echo "Running Nexu_MP_APST4"
sed -i "s/bytes=.*/bytes=$n\"/" Nexu_MP_APST4.py
sed -i "s/CPE=.*/CPE=$CPE/" Nexu_MP_APST4.py
sst -n 10 Nexu_MP_APST4.py

echo "Running Nexu_MP_MMR"
sed -i "s/bytes=.*/bytes=$n\"/" Nexu_MP_MMR.py
sed -i "s/CPE=.*/CPE=$CPE/" Nexu_MP_MMR.py
sst -n 10 Nexu_MP_MMR.py
