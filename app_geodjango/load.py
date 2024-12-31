import os
from django.contrib.gis.utils import LayerMapping
from .models import stations, city_border

city_border_mapping = {
    'key_code': 'key_code',
    'city_name': 'city_name',
    'geom': 'POLYGON',
}
city_border_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'city_border.shp'))

stations_mapping = {
    'station_cd': 'station_cd',
    'station_g_field': 'station_g_',
    'station_na': 'station_na',
    'station_1': 'station_1',
    'station_2': 'station_2',
    'line_cd': 'line_cd',
    'pref_cd': 'pref_cd',
    'post': 'post',
    'address': 'address',
    'lon': 'lon',
    'lat': 'lat',
    'open_ymd': 'open_ymd',
    'close_ymd': 'close_ymd',
    'e_status': 'e_status',
    'e_sort': 'e_sort',
    'station_3': 'station_3',
    'circuity_a': 'circuity_a',
    'edge_densi': 'edge_densi',
    'edge_lengt': 'edge_lengt',
    'edge_len_1': 'edge_len_1',
    'intersecti': 'intersecti',
    'intersec_1': 'intersec_1',
    'k_avg': 'k_avg',
    'm': 'm',
    'n': 'n',
    'node_densi': 'node_densi',
    'self_loop_field': 'self_loop_',
    'street_den': 'street_den',
    'street_len': 'street_len',
    'street_l_1': 'street_l_1',
    'street_seg': 'street_seg',
    'streets_pe': 'streets_pe',
    'average_cl': 'average_cl',
    'mean_integ': 'mean_integ',
    'num_commun': 'num_commun',
    'modularity': 'modularity',
    'var_integr': 'var_integr',
    'geom': 'POINT',
}
stations_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'stations.shp'))

def run(verbose=True):
    lm = LayerMapping(city_border, city_border_path, city_border_mapping, transform=False, encoding='utf-8')
    lm.save(strict=True, verbose=verbose)

    lm = LayerMapping(stations, stations_path, stations_mapping, transform=False, encoding='utf-8')
    lm.save(strict=True, verbose=verbose)
