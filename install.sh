#!/bin/bash
# Install all project dependencies

pip install -r requirements.txt

# python-jobspy pins numpy==1.26.3 which fails to build on Python 3.13+
# Install without deps since numpy, pandas, etc. are already handled above
pip install python-jobspy --no-deps
