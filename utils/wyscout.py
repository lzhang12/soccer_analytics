"""
provide utility to download, process Wyscount data from https://figshare.com/collections/Soccer_match_event_dataset/4415000/5.

Reference:
- https://github.com/Friends-of-Tracking-Data-FoTD/mapping-match-events-in-Python
- Pappalardo, L., Cintia, P., Rossi, A. et al. A public data set of spatio-temporal match events in soccer competitions. Scientific Data 6, 236 (2019) doi:10.1038/s41597-019-0247-7, https://www.nature.com/articles/s41597-019-0247-7
"""

import os
import requests
import zipfile
import io

def download_data():
    dataset_links = {
    'matches' : 'https://ndownloader.figshare.com/files/14464622',
    'events' : 'https://ndownloader.figshare.com/files/14464685',
    'players' : 'https://ndownloader.figshare.com/files/15073721',
    'teams': 'https://ndownloader.figshare.com/files/15073697',
    'competitions': 'https://ndownloader.figshare.com/files/15073685'
    }

    dirname = './data/Wyscout'

    print ("Downloading teams data")
    r = requests.get(dataset_links['teams'], stream=False)
    print (r.text, file=open(os.path.join(dirname, 'teams.json'),'w'))

    print ("Downloading players data")
    r = requests.get(dataset_links['players'], stream=False)
    print (r.text, file=open(os.path.join(dirname, 'players.json'),'w'))
    
    print ("Downloading competitions data")
    r = requests.get(dataset_links['competitions'], stream=False)
    print (r.text, file=open(os.path.join(dirname, 'competitions.json'),'w'))

    print ("Downloading matches data")
    r = requests.get(dataset_links['matches'], stream=True)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(os.path.join(dirname, 'matches'))

    print ("Downloading events data")
    r = requests.get(dataset_links['events'], stream=True)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(os.path.join(dirname, 'events'))
    
    print ("Download completed")

    return

if __name__ == "__main__":
    download_data()