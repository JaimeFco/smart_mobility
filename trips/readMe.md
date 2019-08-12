# Trips generator for yellow cabs in NYC
This programs extract trips from https://www1.nyc.gov/site/tlc/about/tlc-trip-record-data.page.

python3 functions.py configfilePath

The configuration file has the following:
- path to geojson
- path to the network map (SUMO format)
- path to the dataframe if you have it, or "none" if you want to download from internet.
- offset to use in the coordinates in the geojson, two floats separeted by a comma ','
- path to the TAz file to be output
- path to the trips file to be generated
- start date in format yyy/mm/dd
- end date in format yyy/mm/dd
- a list, separated by commas, of the number of zones to be consider. If you want all, just write "all"
- car type, use "private" by default
- list with the name of the types of edges to be selected. Write "none" to let the program extract the ones that are allowed for the car type chosen

Example of configfile.txt
data/taxi_zones.geojson
data/map.net.xml
data/dataFrame.csv
-584029.48,-4507296.15
sumo/tazs.xml
sumo/odTrips.xml
2017/10/01
2017/12/31
140,141,236,237,262,263
private
none


After this program, you can do:
duarouter -c duarcfg_file.trips2routes.duarcfg --additional-files additional.xml --ignore-errors --remove-loops t --repair.from t

then:
$SUMO_HOME/tools/route/sort_routes.py od_route-file.odtrips.rou.xml

sumo -c config_file.sumocfg --fcd-output fcd.txt --fcd-output.geo f --collision.action none --time-to-teleport 180 --step-length 3 --no-step-log t
