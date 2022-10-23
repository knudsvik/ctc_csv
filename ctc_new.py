import pandas as pd
import numpy as np
import os
import glob
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import date

# Timezone:

timezone = 'CET'

# Influxdb parameters:

url = 'localhost:8086'
token = "YourToken"
org = "YourOrg"
bucket = "ctc/autogen"


client = InfluxDBClient(url=url, token=token, org=org)

def main(_tz=timezone, _client=client):
    """
    Main function to be run
    :return: prints success message
    """

    df = pd.DataFrame()
    files = glob.glob('*.csv')

    for file in files:
        # parse(file)
        df = df.append(read_csv(file, _tz), sort=False)

    df.sort_index(inplace=True)
    influx(df, _client)

    for file in files:
        os.remove(file)

    return print(len(files), 'csv file(s) have been parsed and pushed to the influxDB database')

def read_csv(file, tz):
    """
    Reads the file into a pandas dataframe, cleans data and rename columns
    :param file: file to be read
    :param tz: timezone
    :return: pandas dataframe
    """

    df = pd.read_csv(file, index_col=0, parse_dates=True, header=1)
    df.index = df.index.tz_localize(tz, ambiguous='NaT')
    df = df.loc[df.index.notnull()]
    df = df.loc[~df.index.duplicated(keep='first')]
    return df


def influx(DataFrame, client):
    """
    Instantiates influxdb and writes the dataframe to the database
    :param DataFrame: DataFrame to be written to db
    :param host: optional if other than localhost
    :param port: optional if other than 8086
    :return: Name of database that has been written to
    """
    today = str(date.today())

    measurements = {'temperature': ['Outdoor temp',
                                    'TankUpperTemp',
                                    'TankLowerTemp',
                                    'RoomTemperature1',
                                    'RoomTemperature2',
                                    'HeatWater1Temp',
                                    'Return temp',
                                    'BrineInTemp',
                                    'BrineOutTemp',
                                    'PrimarySystemInTemp',
                                    'PrimarySystemOutTemp',
                                    'DischargeGasTemp',
                                    'SuctionTemp',
                                    'Superheat',
                                    'HetgasOverheat'],
                    'electric power': ['ElBoilerUsedPwr',
                                    'InverterMotorPower'],
                    'electric current': ['CurrentL1',
                                         'CurrentL2',
                                         'CurrentL3',
                                         'Compressor L1']
                    }
    write_api = client.write_api(write_options=SYNCHRONOUS)
    for x,y in measurements.items():
        data = DataFrame.filter(y, axis=1)

        write_api.write(bucket, org, record=data, data_frame_measurement_name=x, record_tag_keys={'source': 'ctc_csv', 'date_read': today})
    
    return

if __name__ == '__main__':
    main()
