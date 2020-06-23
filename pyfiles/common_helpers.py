import json

from datetime import timedelta
from math import cos, pi

from datetime import datetime

    
def get_distance_between_coordinates(coord1, coord2):
    # from: http://stackoverflow.com/questions/1253499/simple-calculations-for-working-with-lat-lon-km-distance
    # The approximate conversions are:
    # Latitude: 1 deg = 110.574 km
    # Longitude: 1 deg = 111.320*cos(latitude) km

    x_diff = (coord1[0] - coord2[0]) * 110320 * cos(coord2[1] / 180 * pi)
    y_diff = (coord1[1] - coord2[1]) * 110574

    distance = (x_diff * x_diff + y_diff * y_diff)**0.5
    return distance


def point_coordinates(p):
    return json.loads(p["geojson"])["coordinates"]


def point_distance(p0, p1):
    return get_distance_between_coordinates(
        point_coordinates(p0), point_coordinates(p1))


def round_dict_values(keyvals, precision):
    rounded_keyvals = {}
    for k,v in keyvals.items():
        rounded_keyvals[k] = round(v, precision)
    if precision == 0:
        for k,v in rounded_keyvals.items():
            rounded_keyvals[k] = int(v)
    return rounded_keyvals

def dict_timedelta_to_text(keyvals):
    new_keyvals = {}
    for k,v in keyvals.items():
        new_keyvals[k] = DateTimeDelta_to_Text(v)
    return new_keyvals

def dict_to_sqlstr(keyvals):
    newkeyvals = str(keyvals)
    newkeyvals = newkeyvals.replace("'", "''")
    newkeyvals = newkeyvals.replace(":", "\:")        
    return newkeyvals

def jsonstr_to_sqlstr(jsonstr):
    #newstr = str(jsonstr)
    newstr = jsonstr
    newstr = newstr.replace("'", "''")
    #newstr = newstr.replace(":", "\:")        
    return newstr

def shift_time_to_specific_date(original_date_time,  desired_date_time):
    adjusted_datetime = datetime.combine(desired_date_time.date(), original_date_time.time())
    return adjusted_datetime

# ------ point, geoLoc point functions ------------
def pointRow_to_geoText(point):
    point_location = point_coordinates(point)
    point_location_str='{1},{0}'.format(point_location[0], point_location[1])
    return point_location_str

def pointRow_to_postgisPoint(point):
    point_location = point_coordinates(point)
    point_location_str='POINT({0} {1})'.format(point_location[0], point_location[1])
    return point_location_str

def geoJSON_to_geoText(geoJSONPoint):
    point_location = json.loads(geoJSONPoint)["coordinates"]
    point_location_str='{1},{0}'.format(point_location[0], point_location[1])
    return point_location_str
    
def geoLoc_to_pointRow(lat, lon):
    return {"geojson": json.dumps({"coordinates": [lon, lat]})} #TODO NOTE: "time" and other attributes are irrelevant here and not set

def geoJSON_to_pointRow(geoJSONPoint):
    return {"geojson":geoJSONPoint}

# ------ date time and duration helper functions -------
def DateTime_to_Text(t):
    if t is None:
        return ""
    else:
        return str(t.replace(microsecond = 0))

def DateTime_to_SqlText(t):
    if t is None:
        return "null"
    else:
        return "'" + str(t.replace(microsecond = 0)) + "'"
        
def DateTimeDelta_to_Text(delta):
    return str(delta).split(".")[0]

def OTPTimeStampToNormalDateTime(hsl_timestamp):
    date_and_time = datetime.fromtimestamp(hsl_timestamp / 1000) #datetime doesn't like millisecond accuracy
    return date_and_time

def OTPDurationToNormalDuration(hsl_duration):
    # hsl_duration is in seconds
    duration = timedelta(seconds = hsl_duration)
    # old code (converetd to string!): duration = "{0}:{1}".format(hsl_duration/60 , hsl_duration%60)  # convert to in min:sec format
    return duration
# --------------------------------------------------



