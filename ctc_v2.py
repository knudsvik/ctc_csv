import pandas as pd
import fileinput
import numpy as np
import os
import glob
from influxdb_client import InfluxDBClient
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
    files = glob.glob('*.CSV')

    for file in files:
        parse(file)
        df = df.append(read_csv(file, _tz), sort=False)

    df.sort_index(inplace=True)
    influx(df, _client)

    for file in files:
        os.remove(file)

    return print(len(files), 'csv file(s) have been parsed and pushed to the influxDB database')


def parse(file):
    """
    Removes /x00 from the new lines
    :param file: csv file to be fixed
    :return: fixed file
    """
    with fileinput.FileInput(file, inplace=True) as f:
        for line in f:
            print(line.replace('\x00', ''), end='')
    return


def read_csv(file, tz):
    """
    Reads the file into a pandas dataframe, cleans data and rename columns
    :param file: file to be read
    :param tz: timezone
    :return: pandas dataframe
    """
    ctc_columns = {1: 'unknown_1',
                   2: 'Tank upper',  # temperature [deg C]
                   3: 'unknown_3',
                   4: 'Tank lower',  # temperature [deg C]
                   5: 'unknown_5',
                   6: 'unknown_6',
                   7: 'Primary flow 1',  # temperature [deg C]
                   8: 'Return flow',  # temperature [deg C]
                   9: 'unknown_9',
                   10: 'Heater',  # electric power [kW]
                   11: 'L1',  # electric current [A]
                   12: 'L2',  # electric current [A]
                   13: 'L3',  # electric current [A]
                   14: 'unknown_14',
                   15: 'unknown_15',
                   16: 'unknown_16',
                   17: 'unknown_17',
                   18: 'unknown_18',
                   19: 'unknown_19',
                   20: 'unknown_20',
                   21: 'Charge pump',  # speed [%]
                   22: 'unknown_22',
                   23: 'Heat pump flow',  # temperature [deg C]
                   24: 'Heat pump return',  # temperature [deg C]
                   25: 'unknown_25',
                   26: 'unknown_26',
                   27: 'unknown_27',
                   28: 'unknown_28',
                   29: 'unknown_29',
                   30: 'unknown_30',
                   31: 'unknown_31',
                   32: 'Compressor L1',  # electric current [A]
                   33: 'Compressor'  # on/off [-]
                   }

    df = pd.read_csv(file, header=None, index_col=0, parse_dates=True, usecols=[i for i in range(34)])
    df.index = df.index.tz_localize(tz, ambiguous='NaT')
    df = df.loc[df.index.notnull()]
    df = df.loc[~df.index.duplicated(keep='first')]
    df.rename(columns=ctc_columns, inplace=True)
    df['Compressor'] = np.where(df['Compressor'] == 'ON', 1, 0)
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

    measurements = {'temperature': ['Tank upper',
                                    'Tank lower',
                                    'Primary flow 1',
                                    'Return flow',
                                    'Heat pump flow',
                                    'Heat pump return'],
                    'electric power': ['Heater'],
                    'electric current': ['L1',
                                         'L2',
                                         'L3',
                                         'Compressor L1'],
                    'speed': ['Charge pump'],
                    'on/off': ['Compressor'],
                    'unknowns': [col for col in DataFrame if col.startswith('unknown')]
                    }
    write_api = client.write_api(write_options=SYNCHRONOUS)
    for x,y in measurements.items():
        data = DataFrame.filter(y, axis=1)
        tags = {'source': 'ctc_csv', 'date_read': today}
        write_api.write(bucket, org, record=data, data_frame_measurement_name=x, record_tag_keys=tags)

    return


if __name__ == '__main__':
    main()
