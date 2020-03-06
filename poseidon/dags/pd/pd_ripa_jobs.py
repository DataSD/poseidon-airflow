"""PD ripa _jobs file."""
import pandas as pd
import numpy as np
import glob
import os
import re
import csv
from shlex import quote
from trident.util import general

conf = general.config


def get_data():
    """Download RIPA data from FTP."""

    # Sticking to wget for this because file names change drastically
    command = "wget -np --continue " \
        + f"--user={$ftp_user} " \
        + f"--password='{$ftp_pass}' " \
        + f"--directory-prefix={$temp_dir} " \
        + "ftp://ftp.datasd.org/uploads/sdpd/" \
        + "ripa/*.xlsx"

    command = command.format(quote(command)) 

    p = Popen(command, stdout=PIPE, stderr=PIPE)
        output, error = p.communicate()
        
    if p.returncode != 0:
        logging.info(f"Error downloading files")
        raise Exception(p.returncode)
    else:
        logging.info(f"Files downloaded")
        filename = f"{conf['temp_data_dir']}/*RIPA*.xlsx"
        list_of_files = glob.glob(filename)
        logging.info(list_of_files)
        latest_file = max(list_of_files, key=os.path.getmtime)
        return latest_file

def process_excel(**context):
    """Process RIPA data."""
    latest_file = context['task_instance'].xcom_pull(dag_id="pd_ripa",
        task_ids='get_data')
    
    logging.info(f"Reading in {latest_file} {mode}")

    ripa = pd.read_excel(f"{conf['temp_data_dir']}/{latest_file}",sheet_name=none)

    keys = [*ripa]

    for key in keys:
        # Names need underscores where each capital letter is
        filename = re.sub(r'([a-z](?=[A-Z])|[A-Z](?=[A-Z][a-z]))', r'\1_', key)
        df = ripa[key]
        df.columns = df.columns.str.replace(r'([a-z](?=[A-Z])|[A-Z](?=[A-Z][a-z]))', r'\1_').str.lower()
        df = df.rename(columns={'id':'stop_id',
                                              'stopdate':'date_stop',
                                              'stoptime':'time_stop',
                                              'block':'address_block',
                                              'street':'address_street',
                                              'cityname':'address_city'
                                             })
        float_cols = df.select_dtypes(include=['float'])
        if float_cols.empty:
            print('No float columns')
        else:
            float_col_names = float_cols.columns.values
            df.loc[:,float_col_names] = df.loc[:,float_col_names].fillna(-999999.0).astype(int)
            df = df.replace(-999999,'')
            df.loc[:,float_col_names] = df.loc[:,float_col_names].astype(str)
            
        outfile = f"{conf['temp_data_dir']}/ripa_{filename}.csv"

        general.pos_write_csv(
            df,
            outfile)

    return 'Successfully processed new ripa files'

def process_prod_files(mode='stops',**context):
    """ Append new data to each prod file """
    outfile = f"{conf['prod_data_dir']}/ripa_{mode}_datasd.csv"

    new_df = pd.read_csv(f"{conf['temp_data_dir']}/ripa_{mode}.csv",
        low_memory=False
        )

    prod_df = pd.read_csv(outfile,low_memory=false)

    df = pd.concat([prod_df,new_df])

    df = df.sort_values(['stop_id','pid'])

    general.pos_write_csv(
        df,
        outfile)

    return f"Successfully created {mode} ripa prod file"