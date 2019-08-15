import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, mapping, Point, LineString
from lxml import etree

def fast_iter(context, func, *args):
    for event, elem in context:
        func(elem, *args)
        # It's safe to call clear() here because no descendants will be
        # accessed
        elem.clear()
        # Also eliminate now-empty references from the root node to elem

def process_element(elem, interv, counts, time_laps, n_polys):
    if int(float(elem.attrib['time']))%time_laps == 0:
        M.append(np.copy(counts))
        counts.fill(0)
        print(float(elem.attrib['time']) )

    if int(float(elem.attrib['time']))%interv != 0:
        return

    stepCounts = np.zeros(n_polys)
    for child in elem: # for every active vehicle
        x = float(child.attrib['x'])
        y = float(child.attrib['y'])
        p0 = Point((x-offset[0], y-offset[1]))
        stepCounts += np.array(list(polys.intersects(p0)), dtype=int) # check its zone and added to the counts

    for i in range(n_polys):
        counts[i] = (stepCounts[i] if stepCounts[i]>counts[i] else counts[i])

zones_path = "data/taxi_zones.geojson"
fcd_path = "sumo/fcd.txt"
req_polys = [140, 141, 236, 237, 262, 263]
offset = (-584029.48,-4507296.15)
begin_value = 0
end_value = 7862400
step_length = 3
time_laps = 600
dataframe_path = "dataframe.csv"

n = (end_value - begin_value) // step_length


# Read the geojson file
zones = gpd.read_file(zones_path)
# Save polygons in GeoSeries format
polys = gpd.GeoSeries({zones['OBJECTID'][i-1] : zones.geometry[i-1] for i in req_polys})
print("Number of zones: "+str(len(polys)))

context = etree.iterparse(fcd_path, tag='timestep')
M = []
n_polys = len(polys)
interv = 15
counts = np.zeros(n_polys)
fast_iter(context, process_element, interv, counts, time_laps, n_polys)


import pandas as pd
indexes = np.array([i for i in range(begin_value, end_value, time_laps)]) # Indexes (seconds)

npM = np.array(M, dtype=int) # Convert to a numpy array
df = pd.DataFrame(data=npM, index=indexes,    # 1st column as index
             columns=list(polys.index)) # first row as the zones

df.to_csv(dataframe_path, sep=",")
print("Data saved in {0}".format(dataframe_path))
