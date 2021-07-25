## data integration
import warnings
warnings.filterwarnings(action='ignore')
from functools import partial
from shapely import ops
import pyproj
import json, math
import matplotlib.pyplot as plt
from folium import plugins
import re
from matplotlib import font_manager, rc, rcParams
# def set_korea_font():
#     font_name = font_manager.FontProperties(fname="/System/Library/Fonts/Supplemental/AppleGothic.ttf").get_name()
#     rc('font', family=font_name)
#     rcParams.update({'font.size': 11})
#     rcParams['axes.unicode_minus'] = False  
# set_korea_font()
from shapely.geometry import Point as shapely_Point
from geopy.distance import great_circle as distance
from geopy.point import Point as Point
from math import sin, cos, atan2, sqrt, degrees, radians, pi

from geopy.distance import geodesic
import folium
from folium import plugins
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import os
import datetime

#reproject import 필요

os.chdir('./data')

def reproject(geom, from_proj=None, to_proj=None):
    tfm = partial(pyproj.transform, pyproj.Proj(init=from_proj), pyproj.Proj(init=to_proj))
    return ops.transform(tfm, geom)
os.getcwd()

### 심재훈
1. 사고 개수
2. 혼잡빈도
3. 너비
4. 교차로


### data import
#tab에서 찾기 편하게 모든 단어에 _count_ 붙음
#refer_data 는 data_set['function name']

#심재훈
accident_count_ = pd.read_csv("accident_count.csv")
chaos1_nearby_count_ = [gpd.read_file('23.오산시_상세도로망_LV6.geojson'),
                 pd.read_csv('chaos1.csv')]
width_nearby_count_ = gpd.read_file('23.오산시_상세도로망_LV6.geojson')
cross_road_nearby_count_ = width_nearby_count_


data_set = {
'overspeed_cam_count': overspeed_cam_count_,
'floating_pop_count':floating_pop_count_,
'child_pedestrian_count':child_pedestrian_count_,
'bump_count':bump_count_,
'parking_count':parking_count_,
'parking_cctv_count':parking_cctv_count_,
'car_count':car_count_,
'child_count':child_count_,
'child_rate_count':child_rate_count_,
'elem_kinder_count':elem_kinder_count_,
'isSchoolZone_count':isSchoolZone_count_,
'numberSchoolZone_count':numberSchoolZone_count_,
'accident_count':accident_count_,
'chaos1_nearby_count':chaos1_nearby_count_,
'width_nearby_count':width_nearby_count_,
'cross_road_nearby_count':cross_road_nearby_count_,
'num_cram_school_count':num_cram_school_count_,
'shortest_cross_count':shortest_cross_count_,
'shortest_traffic_signal_count':shortest_traffic_signal_count_,
'shortest_sidewalk_count':shortest_sidewalk_count_,
}

#only <= 12
data_set['accident_count'].loc[:,'가해운전자 연령'] = data_set['accident_count'].loc[:,'가해운전자 연령'].apply(lambda x: int(x[:-1]) if x[:-1].isnumeric() else 999)
data_set['accident_count'].loc[:,'피해운전자 연령'] = data_set['accident_count'].loc[:,'피해운전자 연령'].apply(lambda x: int(x[:-1]) if str(x)[:-1].isnumeric() else 999)

mask1 = data_set['accident_count'].loc[:,'가해운전자 연령'] <= 12
mask2 = data_set['accident_count'].loc[:,'피해운전자 연령'] <= 12

data_set['accident_count'] = data_set['accident_count'].loc[mask1|mask2]
data_set['accident_count'].index = range(len(data_set['accident_count']))
#tuple이 str으로 저장되는 문제
def _str_to_tuple(string):
  """
  input: multilinestring object
  output: arr_cords; lon, lat
  ex) multiline_to_arr_cords(road_gdf.loc[0].geometry)
  """
  return re.findall(r'\d+\.\d+',string)


## 심재훈
### accident_count
def accident_count(lat, lon, radi, refer_data, idx=False):
  """
  input: origin lat lon, radi(m), data(accidents record)
  output: following point count
  optional: (idx of point, count)
  """

  if (type(refer_data['geometry'][0]) == str):
    refer_data['geometry'] = refer_data['geometry'].apply(_str_to_tuple)
  #apply
  bool_mask = refer_data['geometry'].apply(lambda x: geodesic((lat, lon),x).m <= radi)
  if idx:
    return refer_data[bool_mask].index, sum(bool_mask)
  else:
    return sum(bool_mask)
def chaos1_nearby_count(lat, lon, radi, refer_data):
  """
  input: origin lat lon, radi(m), road_data(shapely multilinestring), chaos1_data
  output: following road's chaos1 by different times or lanes
  
  #test_set
  lat, lon = (37.14875860564099, 127.0773701360968)
  radi = 1
  chaos1_nearby(lat, lon, radi, road_gdf, chaos1_gdf)[11]
  #link_id 끝자리 01(상행) 02(하행) 순으로 나옴
  평일 주말 총 평균값
   """
  road_data, chaos1_data = refer_data[0], refer_data[1]
  roads = road_nearby(lat, lon, radi, road_data)
  result = roads.link_id.apply(lambda x: chaos1_data.loc[(chaos1_data.loc[:,'link_id']//100)==int(x),['time_range','chaos1']].mean()[0])
  return result.mean()

def width_nearby_count(lat, lon, radi, road_data):
  roads = road_nearby(lat, lon, radi, road_data)
  return roads.width.apply(int).mean()

def cross_road_nearby_count(lat, lon, radi, road_data):
  """
  4	교차로 통로
  32	복합교차로
  64	로타리
  128	회전교차로

  output = # of cross roads
  """
  cross_roads = [4,32,64,128]
  roads = road_nearby(lat, lon, radi, road_data)
  result = roads.loc[roads.link_type.apply(lambda x: int(x) in cross_roads)]
  return len(result)

# 피쳐 만들기
from tqdm import tqdm
#reproject import 필요
from tqdm._tqdm_notebook import tqdm_notebook
tqdm_notebook.pandas()

function_dict = {
    "overspeed_cam_count" : overspeed_cam_count,
    "floating_pop_count" : floating_pop_count,
    "child_pedestrian_count" : child_pedestrian_count,
    "bump_count" : bump_count,
    "parking_count" : parking_count,
    "parking_cctv_count" : parking_cctv_count,
    "car_count" : car_count,
    "child_count" : child_count,
    "child_rate_count" : child_rate_count,
    "elem_kinder_count" : elem_kinder_count,
    "isSchoolZone_count" : isSchoolZone_count,
    "numberSchoolZone_count" : numberSchoolZone_count,
    "accident_count" : accident_count,
    "chaos1_nearby_count" : chaos1_nearby_count,
    "width_nearby_count" : width_nearby_count,
    "cross_road_nearby_count" : cross_road_nearby_count,
    "num_cram_school_count" : num_cram_school_count,
    "shortest_cross_count" : shortest_cross_count,
    "shortest_traffic_signal_count" : shortest_traffic_signal_count,
    "shortest_sidewalk_count" : shortest_sidewalk_count}

radi_dict = {
    'overspeed_cam_count' : [100],
    'floating_pop_count' : [50],
#    'child_pedestrian_count' : 50 빼야함
    'bump_count' : [0], # [12.5 + 15, 25 + 15],
   'parking_count' : [12.5, 25],
#     'parking_cctv_count' : [12.5, 25],
    'car_count' : [1000], # max값
    'child_count' : [1000], # max값
#    'child_rate_count' : 50,
    'elem_kinder_count' : [400], 
#     'isSchoolZone_count' : 400,
    'numberSchoolZone_count' : [400],
    'accident_count' : [12.5, 25],
    'chaos1_nearby_count' : [12.5, 25, 50],
    'width_nearby_count' : [12.5, 25],
    'cross_road_nearby_count' : [12.5, 25],
    'num_cram_school_count' : [400],
    'shortest_cross_count' : [0],
#     '중앙분리대' : [12.5, 25],
    'shortest_traffic_signal_count' : [0],
    'shortest_sidewalk_count' : [0]} #[12.5, 25],} # 도로 보도의 유무
df = pd.read_csv("learn_point25.csv")[6642:8856]#2214#[6642:8856]#[4428:6642]#[2214:4428] 
values = [df]
for key in list(radi_dict.keys()):
    for radi in radi_dict[key]:
        print(key + str(radi))
        tmp = df.progress_apply(lambda x: function_dict[key](x[1], x[0], radi, data_set[key]),axis = 1)
        if len(tmp.shape) == 1:
            tmp.name = key + str(radi)
        else:
            tmp.columns = [key + str(radi) +"_" + str(i) for i in range(tmp.shape[1])]
        values.append(tmp)

pd.concat(values,axis=1).to_csv("6642_8856.csv",index = False)

