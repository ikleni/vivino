# vivino

A modified fork of a [repo](https://github.com/boivinalex/vivino-recommenderpy) by Boivin Alex 
---

### Details
#### Data scraping (scrape.py)
This script uses Chrome and requires the appropriate driver (see the [docs](https://selenium-python.readthedocs.io/installation.html#drivers)).

The wine_data class is used to acquire and save data.

A user specifies a search query and the script crawls over all wines that satisfy that query and collects wine data. The script also collects reviews,
but it is not guaranteed to collect all. The reviews are collected through Vivino API which does not always display the full set of reviws

Results are stored in an instance of the wine_data class.

Data can be saved as two .csv files. 
