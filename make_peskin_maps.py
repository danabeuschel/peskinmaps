from shapely.geometry import Point, Polygon
import geopandas as gpd
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

def drop_index(df):
    for ind in ['index_right', 'index_left']:
        if ind in df.columns:
            df.drop(ind, axis=1, inplace=True)

def get_lots_with_zoning():
    lots = gpd.read_file('data/lots.geojson').rename(columns={'objectid': 'lot_id'})
    print('loaded lots')
    zoning = gpd.read_file('data/zoning.geojson').rename(columns={'objectid': 'zone_id'})

    lots_with_zoning = gpd.sjoin(lots, zoning, how='inner', op='intersects')
    residential_zones = ['Mixed Use', 'Residential', 'Mixed']
    lots_with_zoning['zoned_residential'] = lots_with_zoning.gen.isin(residential_zones)
    print('imports and merge with zoning done')

    # some lots are in multiple zoning districts. A regular geopandas sjoin will put a parcel in both, and this creates
    # weirdness in the presidio. So we need to not do a regular sjoin, and instead put each lot in the zoning district
    # with the greatest overlap
    minilots = lots[['lot_id', 'geometry']].merge(lots_with_zoning[['lot_id', 'zone_id']], on='lot_id') \
        .merge(zoning[['zone_id', 'geometry']], on='zone_id')
    minilots['overlap'] = gpd.GeoSeries(minilots['geometry_x']).intersection(gpd.GeoSeries(minilots['geometry_y'])).area
    maxes = minilots.groupby('lot_id').max()['overlap'].reset_index()
    minilot_ids = minilots[['lot_id', 'zone_id', 'overlap']].merge(maxes, on=['lot_id', 'overlap'])

    drop_index(lots_with_zoning)

    lots_with_zoning = lots_with_zoning.merge(minilot_ids, on=['lot_id', 'zone_id'])
    drop_index(lots_with_zoning)
    print('now merged with zoning')

    # numeric codes:
    # 1 = zoned residential, no housing (can build w/o CU)
    # 2 = has housing (maybe can build Goldilocks housing with a CU)
    # 3 = has housing and demolitions are banned

    lots_with_zoning['has_residential'] = (lots_with_zoning.resunits != '0') * 2
    lots_with_zoning['residential'] = np.maximum(lots_with_zoning['has_residential'],
                                                lots_with_zoning['zoned_residential'])
    return lots_with_zoning

def get_historic(lots_with_zoning):
    # There are too many of these!
    # state districts, federal districts, lot-level CEQA codes, local landmarks, and local districts
    historic_state = gpd.read_file('data/historic_state.geojson')
    historic_fed = gpd.read_file('data/historic_national.geojson').rename(columns={'name': 'fed_name'})

    drop_index(lots_with_zoning)
    lots_with_zoning = gpd.sjoin(lots_with_zoning, historic_state[['geometry', 'name']], how='left', op='intersects')
    print('got state historic')
    drop_index(lots_with_zoning)
    lots_with_zoning = gpd.sjoin(lots_with_zoning, historic_fed[['geometry', 'fed_name']], how='left', op='intersects')
    print('got fed historic')

    drop_index(lots_with_zoning)
    historic = gpd.read_file('data/historic.geojson')

    # right now I am only using CEQA code A, which means definitely historic. B means unknown, i.e. potentially historic,
    # but I didn't include it since the Planning Department makes a (negative) declaration as part of the application
    # process anyway.
    actually_historic = historic.loc[historic.ceqacode == 'A', ['highstnum', 'stname', 'sttype', 'lowstnum', 'ceqacode']]
    lots_with_zoning = lots_with_zoning.merge(actually_historic, how='left',
                                             right_on=['highstnum', 'stname', 'sttype', 'lowstnum'],
                                             left_on=['to_st', 'street', 'st_type', 'from_st'])
    drop_index(lots_with_zoning)
    print('got individual historic')


    historic_local = gpd.read_file('data/historic_local.geojson').rename(columns={'district': 'local_name'})
    lots_with_zoning = gpd.sjoin(lots_with_zoning, historic_local[['geometry', 'local_name']], how='left', op='intersects')
    print('got local historic districts')

    drop_index(lots_with_zoning)
    historic_localb = gpd.read_file('data/historic_local_landmarks.geojson').rename(columns={'name': 'localb_name'})
    lots_with_zoning = gpd.sjoin(lots_with_zoning, historic_localb[['geometry', 'localb_name']], how='left', op='intersects')
    print('got local historic buildings')

    # add in local historic too
    lots_with_zoning['is_historic'] = pd.notnull(lots_with_zoning['name']) & \
                                                pd.notnull(lots_with_zoning['fed_name']) | \
                                                pd.notnull(lots_with_zoning['ceqacode']) | \
        pd.notnull(lots_with_zoning['local_name']) | pd.notnull(lots_with_zoning['local_name'])

    # time to freeze in amber
    lots_with_zoning.loc[lots_with_zoning.is_historic & (lots_with_zoning.has_residential == 2), 'residential'] = 3
    return lots_with_zoning.drop_duplicates(subset='lot_id').reset_index()


def get_neighborhood_character(lots_with_zoning, height=10):
    buildings = gpd.read_file('data/buildings.geojson')[['geometry', 'hgt_mediancm']]
    buildings['height_median'] = pd.to_numeric(buildings['hgt_mediancm']) * 0.0328084
    print('loaded buildings')

    lots_with_zoning['block'] = pd.to_numeric(lots_with_zoning['from_st']) // 100
    block_cols = ['block', 'street', 'st_type']

    drop_index(lots_with_zoning)
    hgt = gpd.sjoin(buildings, lots_with_zoning[block_cols + ['geometry', 'lot_id']], how='left', op='intersects')
    print('joined buildings')
    drop_index(lots_with_zoning)
    block_hgt = hgt.groupby(block_cols).median()['height_median'].reset_index().rename(columns={'height_median':
                                                                                                'block_height'})
    lot_hgt = hgt.groupby('lot_id').median()['height_median'].reset_index().rename(columns={'height_median': 'height'})
    lots_with_zoning = lots_with_zoning.merge(block_hgt, how='left', on=block_cols)
    drop_index(lots_with_zoning)
    lots_with_zoning = lots_with_zoning.merge(lot_hgt, how='left', on='lot_id')
    drop_index(lots_with_zoning)

    lots_with_zoning['neighborhood_character'] = abs(lots_with_zoning['height'] - lots_with_zoning['block_height']) > height
    print('phew, got neighborhood character')

    # also encase neighborhood character in amber
    lots_with_zoning.loc[lots_with_zoning.neighborhood_character & (lots_with_zoning.has_residential == 2), 'residential'] = 3
    return lots_with_zoning


def plot_peskin(lots_with_zoning, filename):
    fig, ax = plt.subplots()
    ax.set_aspect('equal')
    ax.set_axis_off()
    plt.title('Demolition bill - effects on new housing')
    lots_with_zoning[lots_with_zoning.residential == 0].plot(ax=ax, color='blue', label='not residential.')
    lots_with_zoning[lots_with_zoning.residential == 1].plot(ax=ax, color='green', label='no CU required!')
    lots_with_zoning[lots_with_zoning.residential == 2].plot(ax=ax, color='yellow', label='maybe CU (but probably not)')
    lots_with_zoning[lots_with_zoning.residential == 3].plot(ax=ax, color='red', label='no CU allowed!')
    ax.legend(loc='center right', bbox_to_anchor=(1, 0.5))
    plt.savefig(filename, dpi=1000)