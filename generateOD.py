import pandas as pd
import os
import numpy as np
import collections
import sys
from numpyToVisum.py import convertToVMR

"""
    Given three arguments, the program obtain the O/D matrices from the Yellow Taxi dataset.
    Argument parameters:
    - Begining date in format year/month/day with day and month with a zero padding
    - End date (open interval) in format year/month/day with day and month with a zero padding
    - Name of the output file
"""

# Generates the dates that we need
from datetime import timedelta, date
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


## Read dates ##
# Format: year/month/day
# Read first date
sdate = sys.argv[1]
# Read last date
edate = sys.argv[2]

sdate = (int(sdate[0:4]), int(sdate[5:7]), int(sdate[8:]))
edate = (int(edate[0:4]), int(edate[5:7]), int(edate[8:]))

## Load database ##
# First year
data = []

lastMonth = 12

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
print("Done! \n\n")


## Create OD matrices ##
start_date = date(*sdate)
end_date = date(*edate)

OD_matrices = []
for single_date in daterange(start_date, end_date):
    for i in range(0, 24, 6):
        OD_matrix = np.zeros((266, 266))
        dateStr = single_date.strftime("%Y-%m-%d")
        temp_data = data[ (data['tpep_pickup_datetime'] >= dateStr + " {0:02d}:00:00".format(i)) &
               (data['tpep_pickup_datetime'] <= dateStr + " {0:02d}:59:59".format(i+5)) ]
        print("-> {0}: {1} - {2} hrs.".format(dateStr, i, temp_data.size))
        for k in temp_data.index:
            element = temp_data.PULocationID[k]
            OD_matrix[element][element] += 1

        OD_matrices.append(OD_matrix)


# Delete unknown Origin-Destination
# According to documentation, zones 264 and 265 are unknown
n = len(OD_matrices)
for i in range(n):
    OD_matrices[i] = np.delete(OD_matrices[i], 265, 1)
    OD_matrices[i] = np.delete(OD_matrices[i], 265, 0)

    OD_matrices[i] = np.delete(OD_matrices[i], 264, 1)
    OD_matrices[i] = np.delete(OD_matrices[i], 264, 0)

OD_matrices_np = np.array(OD_matrices, dtype=np.int64)
print(str(OD_matrices_np.shape) + " array to save")

np.save("OD_matrices_{0}.npy".format(sys.argv[3]), OD_matrices_np)
print('Saved!')

# convertToVMR(M)
