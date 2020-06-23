import json
from datetime import timedelta
from math import sin, cos, sqrt, atan2, radians, pi
from datetime import datetime


class CommonHelperException(Exception):
    def __init__(self, error_code, error_message):
        Exception.__init__(self, error_message)        
        self.error_code = error_code # new member
        #OLD code: self.message = error_message # derived from base class Exception
        
class CommonHelper:
        
    @classmethod
    def get_distance_between_coordinates(cls, coord1, coord2):
        # from: http://stackoverflow.com/questions/1253499/simple-calculations-for-working-with-lat-lon-km-distance
        # The approximate conversions are:
        # Latitude: 1 deg = 110.574 km
        # Longitude: 1 deg = 111.320*cos(latitude) km

        x_diff = (coord1[0] - coord2[0]) * 110320 * cos(coord2[1] / 180 * pi)
        y_diff = (coord1[1] - coord2[1]) * 110574

        distance = (x_diff * x_diff + y_diff * y_diff)**0.5
        return distance

    @classmethod
    def get_distance_between_coordinates_new(A, B):    
        R = 6373.0 # approximate radius of earth in km
        
        lat1 = radians(A[0])
        lon1 = radians(A[1])
        lat2 = radians(B[0])
        lon2 = radians(B[1])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c * 1000 # distance in meters
            
        return distance


    @classmethod
    def point_coordinates(cls, p):
        return json.loads(p["geojson"])["coordinates"]

    @classmethod
    def point_distance(cls, p0, p1):
        return cls.get_distance_between_coordinates(cls.point_coordinates(p0), cls.point_coordinates(p1))

    @classmethod
    def point_distance_byGeoJSON(cls, p0, p1):
        return cls.get_distance_between_coordinates(json.loads(p0)['coordinates'], json.loads(p1)['coordinates'])


    # ------ point, geoLoc point functions ------------
    @classmethod    
    def pointRow_to_geoText(cls, point):
        point_location = cls.point_coordinates(point)
        point_location_str='{1},{0}'.format(point_location[0], point_location[1])
        return point_location_str

    @classmethod
    def pointRow_to_postgisPoint(cls, point):
        point_location = cls.point_coordinates(point)
        point_location_str='POINT({0} {1})'.format(point_location[0], point_location[1])
        return point_location_str

    @classmethod
    def geoJSON_to_geoText(cls, geoJSONPoint):
        point_location = json.loads(geoJSONPoint)["coordinates"]
        point_location_str='{1},{0}'.format(point_location[0], point_location[1])
        return point_location_str
        
    @classmethod        
    def geoLoc_to_pointRow(cls, lat, lon):
        return {"geojson": json.dumps({"coordinates": [lon, lat]})} #TODO NOTE: "time" and other attributes are irrelevant here and not set

    @classmethod
    def geoJSON_to_pointRow(cls, geoJSONPoint):
        return {"geojson":geoJSONPoint}

    @classmethod
    def json_to_sqlstr(cls, json_collection):
        sqlstr = ""
        try:
            sqlstr = cls.jsonstr_to_sqlstr(json.dumps(json_collection))
        except Exception as e: 
            raise CommonHelperException(0, "CommonHelper::json_to_sqlstr() error: {}".format(str(e)))
        return sqlstr
    
    @classmethod
    def jsonstr_to_sqlstr(cls, jsonstr):
        #newstr = str(jsonstr)
        newstr = jsonstr
        newstr = newstr.replace("'", "''")
        #newstr = newstr.replace(":", "\:")        
        return newstr

    # ------ date time and duration helper functions -------
    @classmethod    
    def DateTime_to_Text(cls, t):
        if t is None:
            return ""
        else:
            return str(t.replace(microsecond = 0))
            
    @classmethod
    def DateTime_to_SqlText(cls, t):
        if t is None:
            return "null"
        else:
            return "'" + str(t.replace(microsecond = 0)) + "'"
    
    @classmethod
    def str_to_DateTimeDuration(cls, str):
        if str is None:
            return timedelta(0)
        else:
            data = str.split(":")
            time = timedelta(hours=int(data[0]), minutes=int(data[1]), seconds=int(data[2]))
            return time
    
    @classmethod
    def multiply_duration(cls, t, coeff):
        if t is not None:
            return timedelta(seconds=int(coeff * t.total_seconds()))
        else:
            return timedelta(0)
    
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
