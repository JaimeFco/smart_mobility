import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, mapping, Point, LineString
import xml.etree.ElementTree as ET

import pandas as pd
import os
import collections
import datetime
import random
import sys

from datetime import timedelta, date

def geojson2plygons(zones_path, zones_req=None):
    """
    Function that given the path to a file geojson, extract the geometry and
    convert it to Polygons
    Inputs:
        - zones_path: string with the path to the geojson files
        - zones_req: names' list of the zones required
    Output:
        - Geoseries with the poligons
    """
    zones = gpd.read_file(zones_path)
    if zones_req == None:
        zones_req = [a for a in range(len(zones))]
    else:
        zones_req = [a-1 for a in zones_req]
    # Save polygons in GeoSeries format
    polys = gpd.GeoSeries({zones['OBJECTID'][i] : zones.geometry[i] for i in zones_req})
    return polys

def getTypesAllowed(mapRoot, type, verbose = 1):
    """
    Function that extracts from net.xml (SUMO format) the types of edges allowed for car type `type`.
    Inputs:
        - mapRoot: An fcd-export type from xml.etree.ElementTree, that correspond to the root of the net.xml.
        - type: Atring with the type.
        - verbose: if >0, reports the types of edges allowed.
    Outputs:
        - A set with the name of the edges allowed.
    """
    allowedTypes = set({})
    # Get types of edges
    for child in mapRoot: # For every label in file
        flag = False
        if child.tag == "type": # if tag is <type>
            try: # Allow specification
                allowed = child.attrib['allow'].split(" ")
                if type in allowed:
                    flag = True
            except: # Disallow specification
                disallowed = child.attrib['disallow'].split(" ")
                if type not in disallowed:
                    flag = True
            if flag: # if 'private' is allowed
                allowedTypes.add(child.attrib['id'])

    if verbose > 0:
        print("Allowed:")
        print(allowedTypes)

    return allowedTypes

def getAllowedEdges(mapRoot, allowedTypes, verbose = 1):
    """
    Given a map in net.xml SUMO format, extract the indexes of the allowed edges
    in the xml file.
    Inputs:
        - mapRoot: An fcd-export type from xml.etree.ElementTree, that correspond to the root of net.xml.
        - allowedTypes: list of strings with the name of the types that you are looking for.
        - Verbose: if >0, reports the indexes.
    Outputs:
        - A list with the indexes in mapRoot where are located the edges allowed for `allowedTypes`.
    """
    allowedTypes = set(allowedTypes)

    # Getting the allowed edges
    allowedIndexs = [] # To save the index of the allowed edges
    for i in range(len(mapRoot)):
        if mapRoot[i].tag == "edge": # if it is an edge
            try: # if it has an attribut 'type'
                if mapRoot[i].attrib['type'] in allowedTypes:
                    allowedIndexs.append(i)
            except:
                continue
    if verbose > 1:
        print("Indexs of the allowed edges:")
        print(allowedIndexs)

    return allowedIndexs

def classifyEdges(mapRoot, allowedIndexs, polys, offset=(0,0)):
    """
    This function intersects the edges with the Polygon objects in `polys`
    and return an array that at i, contains the set of edges intersecting
    poly[i].
    Inputs:
        - mapRoot: An fcd-export type from xml.etree.ElementTree, that correspond to the root of net.xml.
        - allowedIdexes: indexes in mapRoot where are located the edges to classify.
        - polys: Geoseries object with the plygons.
        - offset: a pair with a bias for the coordinates in `polys`.

        The last one can be seen in the header of the network if necessary.
    """
    n = len(polys)
    ## Classification of the edges per zone ##
    tazs = {polys.index[i] : set({}) for i in range(n)} #sets per zone
    k=0
    K = len(allowedIndexs) // 10
    for index in allowedIndexs: #for every permitted edge
        if k%K == 0:
            print(str(k/len(allowedIndexs)))
        k+=1
        for lane in mapRoot[index]: #for all the lanes in the edge
            coordStrings = lane.attrib['shape'].split(' ') #Split in coordinates
            pts = []
            #Create a Line object
            for point in coordStrings:
                pair = point.split(',')
                pts.append([float(pair[0])-offset[0], float(pair[1])-offset[1]])
            line = LineString(pts)
            #Check if Line intersect polygons
            positives = list(polys.intersects(line))
            for i, val in enumerate(positives): #For polys intersected
                if val: #Add this edge to the list
                    tazs[polys.index[i]].add(mapRoot[index].attrib['id'])
    return tazs

def writeTazFile(tazFile_path, zones_path, tazs, zones_req=None, offset=(0,0)):
    """
    Write a xml docment with the regions in TAZ format, of `zones_req`
    with the coordinates in `zones_path` and edges in `tazs`.
    Inputs:
        - tazFile_path: path of the output file.
        - zones_path: path to the geojson file.
        - tazs: a dictionary where at k, are located the edges of zone k.
        - zones_req: if you don't want all the zones in the geojson to be plot.

    Outputs:
        - tazFile_path xml file.
    """
    offset = np.array(offset)
    ## read geojson
    zones = gpd.read_file(zones_path)
    ## Open output file
    fout = open(tazFile_path,'w')
    # Header
    fout.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n\n")
    fout.write("<additional xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:noNamespaceSchemaLocation=\"http://sumo.dlr.de/xsd/additional_file.xsd\">\n")

    colours = ["blue", "red", "green"]
    n = len(zones.OBJECTID)

    if zones_req == None:
        zones_req = [a for a in range(n)]

    # For all the geometries in the geojson
    for i in zones_req:
        arr = np.array(mapping(zones.geometry[i-1])["coordinates"][0]) # get coords
        if type(arr[0][0]) == np.float64: # if it's one piece
            fout.write("<taz id=\"taz_{0}\" color=\"{1}\" shape=\"".format(i, colours[i%3]))

            to_print = arr[0] + offset
            fout.write("{0},{1}".format(to_print[0], to_print[1]))

            for a in arr[1:]:
                to_print = a + offset
                fout.write(" {0},{1}".format(to_print[0], to_print[1]))
            fout.write("\">\n")
        else: # if there are more then one pieces
            #print(i+1)
            e=0
            for e, b in enumerate(np.array(mapping(zones.geometry[i])["coordinates"])):
                fout.write("<taz id=\"taz_{0}#{2}\" color=\"{1}\" shape=\"" .format(i+1, colours[i%3], e))
                bb = np.array(b[0])

                to_print = bb[0] + offset
                fout.write("{0},{1}".format(to_print[0], to_print[1]))

                for a in bb[1:]:
                    to_print = a + offset
                    fout.write(" {0},{1}".format(to_print[0], to_print[1]))
                fout.write("\">\n")
                if e < len(mapping(zones.geometry[i])["coordinates"])-1:
                    fout.write("</taz>\n")
        # Write edges
        for lane in tazs[i]:
            fout.write("<tazSource weight=\"1.00\" id=\"{0}\"/> \n".format(lane))
            fout.write("<tazSink weight=\"1.00\" id=\"{0}\"/> \n".format(lane))
        fout.write("</taz>\n")

    fout.write("</additional>\n\n") # Clousure

    fout.close()


def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)

# Clean Data
def clean_data(df):
    df = df.drop(['payment_type', 'fare_amount', 'extra', 'mta_tax', 'tip_amount',
       'tolls_amount', 'improvement_surcharge'], axis = 1) # Delete non-necessary
    df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime,
                                                 format='%Y-%m-%d %H:%M:%S')
    df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime,
                                                 format='%Y-%m-%d %H:%M:%S')
    return df

def importDatabase(sdate, edate, dataset_path=None, verbose=1):
    """
    Import the taxi databases in the interval [`sdate`, `edate`).
    Inputs:
        - sdate: string with the date in format yyyy/mm/dd (%Y/%m/%d).
        - edate: string in the same format yyyy/mm/dd (%Y/%m/%d).
        - dataset_path: a path to the database. If you leave this in blank,
          the dbs will be download first from internet and save in taxiDataFrame.csv
        - verbose: if >0, print a summary.
    Outputs:
        - A geopandas dataframe object.
    """
    # Time definitions
    sdate = (int(sdate[0:4]), int(sdate[5:7]), int(sdate[8:]))
    edate = (int(edate[0:4]), int(edate[5:7]), int(edate[8:]))
    start_date = datetime.datetime(*sdate, 0, 0, 0)
    end_date = datetime.datetime(*edate, 0, 0, 0)

    # Load database
    data = []
    lastMonth = 12

    if dataset_path == None:
        print("Reading dataset from internet.")
        if sdate[0] == edate[0]: # Same year
            lastMonth = edate[1]

        # First year
        for i in range(sdate[1], lastMonth+1):
            url = "https://s3.amazonaws.com/nyc-tlc/trip+data/yellow_tripdata_{0}-{1:02d}.csv".format(sdate[0], i)
            print("Reading "+url)
            data_taxis = pd.read_csv(url)
            data_taxis = clean_data(data_taxis)
            if i == sdate[1]:
                data = data_taxis
            else:
                data = pd.concat([data, data_taxis], ignore_index=True)

        # Years in the middle
        for y in range(sdate[0]+1, edate[0]):
            for i in range(1, 13):
                url = "https://s3.amazonaws.com/nyc-tlc/trip+data/yellow_tripdata_{0}-{1:02d}.csv".format(y, i)
                data_taxis = pd.read_csv(url)
                print("Reading "+url)
                data_taxis = clean_data(data_taxis)
                data = pd.concat([data, data_taxis], ignore_index=True)

        # Last year if first and last are not equal (otherwise, is included in first loop)
        if sdate[0] != edate[0]:
            for i in range(1, edate[1]+1):
                url = "https://s3.amazonaws.com/nyc-tlc/trip+data/yellow_tripdata_{0}-{1:02d}.csv".format(edate[0], i)
                data_taxis = pd.read_csv(url)
                print("Reading "+url)
                data_taxis = clean_data(data_taxis)
                data = pd.concat([data, data_taxis], ignore_index=True)
        print("Writing data in taxiDataFrame.csv file\n")
        data.to_csv("taxiDataFrame.csv", sep=',')
    else:
        data = pd.read_csv(dataset_path)
        data.tpep_pickup_datetime = pd.to_datetime(data.tpep_pickup_datetime,
                                                     format='%Y-%m-%d %H:%M:%S')
        print("Read dataset from {0}".format(dataset_path))

    if verbose > 0:
        print("Dates:")
        print(start_date)
        print(end_date)
        print("Seconds between them: {0}".format(abs(int((end_date-start_date).total_seconds()))))

    data = data[(data['tpep_pickup_datetime'] >= start_date.strftime('%Y-%m-%d %H:%M:%S')) & (data['tpep_pickup_datetime'] < end_date.strftime('%Y-%m-%d %H:%M:%S'))]

    return data

def writeTripsFile(tripsFile_path, zones_req, tazs, df, sdate, edate):
    """
        Given some zones, the edges in the zones, the taxi dataset and
        `sdate`, `edate`, write a xml with the trips from the data frame
        using random edges.
    """
    sdate = (int(sdate[0:4]), int(sdate[5:7]), int(sdate[8:]))
    edate = (int(edate[0:4]), int(edate[5:7]), int(edate[8:]))
    start_date = datetime.datetime(*sdate, 0, 0, 0)
    end_date = datetime.datetime(*edate, 0, 0, 0)
    ## Creating the routes file ##
    print("Writing routes...")
    fout = open(tripsFile_path,'w')
    # Header
    fout.write("<routes xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:noNamespaceSchemaLocation=\"http://sumo.dlr.de/xsd/routes_file.xsd\">\n")

    n = len(df.VendorID)

    n_trips = 0
    for k in df.index[0:n]:
        zoneOrigin = int(df.PULocationID[k])
        zoneDestiny = int(df.DOLocationID[k])

        if zoneOrigin not in zones_req:
            continue
        if zoneDestiny not in zones_req:
            continue

        dateTrip = df.tpep_pickup_datetime[k]
        secondsTrip = abs(int((dateTrip-start_date).total_seconds()))

        lanePU = random.choice(list(tazs[zoneOrigin]))
        laneDO = random.choice(list(tazs[zoneDestiny]))

        fout.write("<trip id=\"{0}\" depart=\"{1}\" ".format(k, secondsTrip))
        fout.write("from=\"{0}\" to=\"{1}\" ".format(lanePU, laneDO))

        fout.write("type=\"private\" fromTaz=\"taz_{0}\" toTaz=\"taz_{1}\" ".format(zoneOrigin, zoneDestiny))
        fout.write("departLane=\"best\" departSpeed=\"0.0\" departPos=\"random_free\"/>\n")
        n_trips += 1

    # Footer
    fout.write("</routes>\n")
    fout.close()
    print("Trips saved:"+str(n_trips))

def main():
    """
    Read some parameters from a config file and build the trips using them.

    """
    fin = open(sys.argv[1],'r')
    ## Definition of some variables##
    # path to geojson with the zones
    zones_path = fin.readline()[:-1] # "taxi_zones.geojson"
    # path to the map (xml)
    map_path = fin.readline()[:-1] # "map.net.xml"
    # path to dataset
    dataset_path = fin.readline()[:-1] # "taxiDataFrame.csv"
    if dataset_path == "none":
        dataset_path = None
    # offset of the coordinate system
    offsetString = fin.readline()[:-1].split(',') # (-584029.48,-4507296.15) #bias
    offset = (float(offsetString[0]), float(offsetString[1]))
    # path to the TAZ xml file
    tazFile_path = fin.readline()[:-1] #"../test6/tazs.xml"
    # path to the trips xml file
    tripsFile_path = fin.readline()[:-1] # "../test6/odTrips.xml"
    # dates to consider
    sdate = fin.readline()[:-1] #'2017/10/01'
    edate = fin.readline()[:-1] #'2017/12/31'

    zones_reqString = fin.readline()[:-1].split(',')
    if zones_reqString == 'all':
        zones_req = None
    else:
        zones_req = [int(a) for a in zones_reqString] #[140, 141, 236, 237, 262, 263]

    carType = fin.readline() # private
    allowedTypesString = fin.readline()[:-1].split(',')
    if allowedTypesString != 'none':
        allowedTypes = set(allowedTypesString)
    else:
        allowedTypes = None
    # {'highway.secondary', 'highway.trunk_link', 'highway.track', 'highway.living_street', 'highway.unclassified', 'highway.residential', 'highway.primary', 'highway.tertiary', 'highway.unsurfaced', 'highway.primary_link', 'highway.trunk', 'highway.tertiary_link', 'highway.secondary_link'

    fin.close()

    polys = geojson2plygons(zones_path, zones_req)
    nZones = len(polys)
    print("Zones read: {0}.".format(nZones))

    mapRoot = ET.parse(map_path).getroot() #read the net.xml file

    if allowedTypes == None:
        allowedTypes = getTypesAllowed(mapRoot, carType, verbose = 1)
    print("Allowed types")
    print(allowedTypes)

    allowedEdges = getAllowedEdges(mapRoot, allowedTypes, verbose = 1)
    tazs = classifyEdges(mapRoot, allowedEdges, polys, offset=offset)
    writeTazFile(tazFile_path, zones_path, tazs, zones_req, offset=offset)
    print("TAZ file wrote.")

    df = importDatabase(sdate, edate, dataset_path)

    writeTripsFile(tripsFile_path, zones_req, tazs, df, sdate, edate)
    print("\nProgram ends successfully!")

if __name__ == '__main__':
    main()
