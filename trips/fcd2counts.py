import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, mapping, Point, LineString
import xml.etree.ElementTree as ET

zones_path = "data/taxi_zones.geojson"
fcd_path = "sumo/fcd.txt"
req_polys = [140, 141, 236, 237, 262, 263]
offset = (-584029.48,-4507296.15)
begin_value = 0
end_value = 7862400
step_length = 3
time_laps = 600
dataframe_path = "dataframe"

n = (end_value - begin_value) // step_length

# Read the map.xml file
mapRoot = ET.parse(fcd_path).getroot()
zones = gpd.read_file(zones_path)
# Save polygons in GeoSeries format
polys = gpd.GeoSeries({zones['OBJECTID'][i-1] : zones.geometry[i-1] for i in req_polys})
print("Number of zones: "+str(len(polys)))

M = []
j=0
counts = np.zeros(len(polys))
n_polys = len(polys)
for i in range(n): # for every timestep
    stepCounts = np.zeros(n_polys)
    for child in mapRoot[i]: # for every active vehicle
        x = float(child.attrib['x'])
        y = float(child.attrib['y'])
        p0 = Point((x-offset[0], y-offset[1]))
        stepCounts += np.array(list(polys.intersects(p0)), dtype=int) # check its zone and added to the counts

    counts = np.array([(stepCounts[i] if stepCounts[i]>counts[i] else counts[i]) for i in range(n_polys)]) # Can be max, min, mean or identity

    if i%(time_laps // step_length ) == 0: # Every time_laps seconds save the results
        M.append(counts)
        counts = np.zeros(n_polys)
        print(str(j/n * 100) + "%")
        j += (time_laps // step_length)

import pandas as pd
indexes = np.array([i for i in range(0, n+1, time_laps)]) # Indexes (seconds)

MM = np.array(M, dtype=int) # Convert to a numpy array
df = pd.DataFrame(data=MM, index=indexes,    # 1st column as index
             columns=list(polys.index)) # first row as the zones

df.to_csv(dataframe_path, sep=",")
