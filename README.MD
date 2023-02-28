This repository contains a proof-of-concept virtual texture decoder (also can handle normal textures)

Current implementation only been tested on UE4.26, UE4.27 structures are a bit different so some adjustments will be required

Usage:
* Install python 3.10 or newer
* Install dependencies from requirements.txt ```python -m pip install -r requirements.txt```
* Replace path in runner.py with path to path with **_saved_** assets from UModel 
* Run scripts ```python runner.py```

This repo also contains attempt to parse UE4.26 save files