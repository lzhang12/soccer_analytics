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
import seaborn as sns
import pandas as pd
from collections import defaultdict
import numpy as np

# if the whole repo needs to be published as a package, better to use importlib for reading data in subfolder
# from importlib import resources
# _TAGFILE = resources.open_binary('soccer_analytics/data/Wyscout', 'tags2name.csv')

_TEAMFILE = './data/Wyscout/teams.json'
_PLAYERFILE = './data/Wyscout/players.json'
_TAGFILE = './data/Wyscout/tags2name.csv'


def download_data():
    """
    download events, matches, players, competitions and teams dataset from figshare.
    """

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


def add_event_cols(events, cols, match_file=None):
    """
    Add columns in events Dataframe

    Argument:
        events = events Dataframe
        cols = added column label

    Return:
        events = Dataframe with added column
    """

    for col in cols:

        if col == 'team':
            df_team = pd.read_json(_TEAMFILE)
            teamId2team = dict(zip(df_team['wyId'], df_team['name']))
            events['team'] = events.teamId.apply(lambda x: teamId2team[x])

        elif col == 'player':
            df_player = pd.read_json(_PLAYERFILE)
            playerId2player = dict(zip(df_player['wyId'], df_player['shortName']))
            playerId2player[0] = '' #  Interruption has playerId 0, and some free kicks missing player has playerId = 0.
            events['player'] = events.playerId.apply(lambda x: playerId2player[x])

        elif col == 'taglist':
            df_tag = pd.read_csv(_TAGFILE, sep=';')
            tagId2tag = dict(zip(df_tag['Tag'], df_tag['Description']))
            events['taglist'] = events.tags.apply(lambda x: [tagId2tag[i['id']] for i in x])

        elif col == 'time': # time format = (match_half=1/2, match_minute --> int, match_sec --> int)
            events['time'] = events.apply(lambda x: (int(x['matchPeriod'][0]), int(x['eventSec']//60), round(x['eventSec']%60)), axis=1)

        elif col == 'homeaway':
            df_match = pd.read_json(match_file)
            matchId2homeaway = dict(zip(df_match['wyId'], df_match['teamsData'].apply(lambda x: {i['teamId']:i['side'] for i in x.values()})))
            events['homeaway'] = events[['matchId', 'teamId']].apply(lambda x: matchId2homeaway[x['matchId']][x['teamId']], axis=1)

        else:
            print('ADDING COLUMN NOT AVAILABLE')

    return events


def within_time_period(t, time_period):
    """
    Check if time is in the time period

    Argument:
        t = given time in format (half, min, sec)
        time_period = tuple of (start_time, end_time) in format (half, min, sec)

    Return:
        boolean
    """

    start_time = time_period[0]
    end_time = time_period[1]
    assert start_time[0] == end_time[0], "TIME PERIOD NOT IN THE SAME HALF !"

    if t[0] == start_time[0]:
        t_sec = t[1]*60+t[2]
        start_sec = start_time[1]*60 + start_time[2]
        end_sec = end_time[1]*60 + end_time[2]
        if t_sec >= start_sec and t_sec <= end_sec:
            return True

    return False


def filter_events_by_time(match_events, half=1, minute_period=(0,10)):
    """
    filter match events within time period

    Argument:
        match_events = Dataframe of a single match events
        half = 1 for first half, 2 for second half
        minute_period = tuple of time window (starting_time, end_time) in full-time minutes

    Return:
        match_events = filtered match event
    """

    # sort events by time
    match_events = match_events.sort_values(by=['matchPeriod', 'eventSec'])

    # extract events within time period
    time_period = ((half, minute_period[0], 0), (half, minute_period[1], 0))
    match_events = match_events[match_events.time.apply(lambda x: within_time_period(x, time_period))]
    print('{} EVENTS IN THIS PERIROD'.format(len(match_events)))

    return match_events


def is_successful_pass(event, next_event):
    """
    check if a successuful pass
    """
    if 'Not accurate' not in event['taglist'] and event['team'] == next_event['team']:
        return True
    return False


def generate_narrative(events):
    """
    generate storyline of the match from match_events

    Argument:
        event = Dataframe of a single match events

    Return:
        narrative = list of event narrative
    """
    dict_events = events.to_dict('records')  # faster loop over list of dicts
    narrative = []

    dict_next_events = dict_events[1:]
    dict_next_events.append({key:[] for key in dict_events[0].keys()})

    for event, next_event in zip(dict_events, dict_next_events):
        time = event['time']
        subjective = ' '.join((event['player'], 'of', event['team']))
        action = ' '.join(('made', event['subEventName']))
        description = '('+', '.join(event['taglist'])+')'
        prepositional = ''

        if not event['player']:
            subjective = ''
            action = event['subEventName']

        if not event['subEventName']:
            action = ' '.join(('made', event['eventName']))

        if not event['taglist']:
            description = ''

        if event['eventName'] == 'Pass':
            if is_successful_pass(event, next_event):
                prepositional = ' '.join(('to', next_event['player']))

        str_ = "({half}H) {min:0>2}:{sec:0>2}, {sub} {act} {descript} {preposit} ".format(
                        half = time[0],
                        min = time[1],
                        sec = time[2],
                        sub = subjective,
                        act = action.lower(),
                        descript = description.lower(),
                        preposit = prepositional
                        )

        narrative.append(str_)

    return narrative