# ~~~ this class/file should be in package (namespace) DAL ~~~

import json
from copy import deepcopy

from commonlayer.common_helper_class import CommonHelper
from commonlayer.logger import (log, logi, loge)
from pyfiles.common.trip import Trip
from pyfiles.common_helpers import (DateTime_to_Text, DateTime_to_SqlText, dict_timedelta_to_text, round_dict_values)
from pyfiles.common_helpers import (pointRow_to_geoText, pointRow_to_postgisPoint, DateTimeDelta_to_Text, dict_to_sqlstr)
from dal.base.table_interface import TableInterface
import pandas as pd
from datetime import timedelta

class Trips(TableInterface):

    def store_trips_to_legs(self, ids_to_process, trips):        
        for trip in trips:
            for leg in trip.legs:
                self.store_trip_to_leg(trip,  leg)
                
            # TOOD: we don't save legs of alternative trips for now (keep it simple) ... should do later?
            #for tripalt in trip.alternative_trips:
            #    self.store_trip_to_leg(tripalt)        
    
    def store_trip_to_leg(self, trip,  leg):
        qstr = ""
        try:
            qstr = """INSERT INTO trips_to_legs (user_id, trip_id, plan_id, leg_id) 
                   VALUES ({0},{1},{2},{3})""".format(trip.user_id, trip.id, trip.plan_id, leg['id'])
    
            log(["store_trip_to_leg():: qstr:", qstr])
            log("")
            
            res, db_res = self.db_command.ExecuteSQL(qstr)
            log(["result:", str(res)])
        except Exception as e:
            print("Exception in store_trip_to_leg():")
            print("exception:",e)
            print("qstr:", qstr)
            raise #TODO NOTE critical .. so that BLL is able to rollback if needed *
            
    def get_next_user_trip_id(self, user_id, date_range_start, date_range_end):
        qstr = """SELECT max(id) as max_id
                    FROM trips_alts  
                    WHERE user_id = {0} AND (user_id, id, plan_id) NOT IN
                    (SELECT user_id, id, plan_id FROM trips_alts
                     WHERE user_id = {0}
                     AND start_time >= '{1}' AND end_time <= '{2}');
                """.format(user_id, CommonHelper.DateTime_to_Text(date_range_start), CommonHelper.DateTime_to_Text(date_range_end))                                            
        log(["get_next_user_trip_id():: qstr:", qstr])
        log("")
        res, maxid_rows = self.db_command.ExecuteSQL(qstr)  
        
        if maxid_rows.rowcount > 0:
            for maxid_row in maxid_rows: 
                if maxid_row['max_id'] == None:
                    return 0
                else:
                    return maxid_row['max_id']        
        return 0

    def get_next_user_trip_id_for_moprim(self, user_id, date_range_start, date_range_end):
        qstr = """SELECT max(id) as max_id
                    FROM trips_alts  
                    WHERE user_id = {0} AND (user_id, id, plan_id) IN
                    (SELECT user_id, id, plan_id FROM trips_alts
                     WHERE user_id = {0}
                     AND start_time >= '{1}' AND end_time <= '{2}');
                """.format(user_id, CommonHelper.DateTime_to_Text(date_range_start), CommonHelper.DateTime_to_Text(date_range_end))                                            
        log(["get_next_user_trip_id():: qstr:", qstr])
        log("")
        res, maxid_rows = self.db_command.ExecuteSQL(qstr)   
        
        if maxid_rows.rowcount > 0:
            for maxid_row in maxid_rows: 
                if maxid_row['max_id'] == None:
                    return 0
                else:
                    return maxid_row['max_id']
        
        return 0

    def delete_trip_alternatives(self, trip):
        for tripalt in trip.alternative_trips:
            self.delete_trip(tripalt)            
    
        
    def delete_trip(self, trip):
        qstr = """DELETE FROM trips_alts 
                    WHERE user_id IN ({0})
                    AND id = {1} AND plan_id = {2};
                """.format(trip.user_id, trip.id, trip.plan_id)
        #print("delete_trip(trip): qstr: ", qstr)
        res, db_res = self.db_command.ExecuteSQL(qstr)
        return res


    def delete_trips(self, ids_to_process, date_range_start, date_range_end):
        qstr = """DELETE FROM trips_alts 
                    WHERE user_id IN ({0})
                    AND start_time >= '{1}' AND end_time <= '{2}';
                """.format(ids_to_process, DateTime_to_Text(date_range_start), DateTime_to_Text(date_range_end))
        log(["delete_trips():: qstr for removing old rows before storing new ones:", qstr])
        res, db_res = self.db_command.ExecuteSQL(qstr)
        log(["result:", res])
        log("")        
        return res

    def delete_trips_and_alternatives(self, date_range_start, date_range_end):
        qstr = """DELETE FROM trips_alts 
                    WHERE true
                    AND start_time >= '{}' AND end_time <= '{}';
                """.format(DateTime_to_Text(date_range_start), DateTime_to_Text(date_range_end))
        log(["delete_trips_and_alternatives():: qstr for removing old rows before storing new ones:", qstr])
        res, db_res = self.db_command.ExecuteSQL(qstr)
        log(["result:", res])
        log("")        
        return res

    def delete_trips_by_id(self, ids_to_process, trip_id_start, trip_id_end):
        qstr = """DELETE FROM trips_alts 
                    WHERE user_id IN ({0})
                    AND id >= '{1}' AND id <= '{2}';
                """.format(ids_to_process, trip_id_start, trip_id_end)
        log(["delete_trips():: qstr for removing old rows before storing new ones:", qstr])
        res, db_res = self.db_command.ExecuteSQL(qstr)
        log(["result:", res])
        log("")
        return res

    def HACK_delete_ebike_trips(self, ids_to_process, date_range_start, date_range_end):
        qstr = """DELETE FROM trips_alts 
                    WHERE user_id IN ({0})
                    AND start_time >= '{1}' AND end_time <= '{2}'
                    AND plan_id > 0
                    AND mainmode = 'EBICYCLE';
                """.format(ids_to_process, DateTime_to_Text(date_range_start), DateTime_to_Text(date_range_end))
        log(["delete_trips():: qstr for removing old rows before storing new ones:", qstr])
        res, db_res = self.db_command.ExecuteSQL(qstr)
        log(["result:", res])
        log("")
        return res


    def load_trips(self, ids_to_process, date_range_start, date_range_end,  timeofday_start,  timeofday_end, timeofday_start2,  timeofday_end2, min_od_distance, od_d_diff_coeff):        
        # TODO: refine more if needed here
        qstr = """SELECT user_id, device_id, id, plan_id, start_time, end_time, ST_AsGeoJSON(origin) as origin, ST_AsGeoJSON(destination) as destination, 
                        multimodal_summary, duration, cost, calories, emission, comfort, distance, 
                        time_by_mode, cost_by_mode, calories_by_mode, emission_by_mode, distance_by_mode,
                        mainmode, 
                        start_time_for_plan, notes, od_distance
                    FROM trips_alts  
                    WHERE (user_id, id) IN
                    ( SELECT user_id, id FROM trips_alts 
                      WHERE user_id IN({0}) AND plan_id = 0 
                      AND start_time >= '{1}' AND end_time <= '{2}'                       
                      AND ((start_time::time >= time {3} AND end_time::time <= time {4}) OR
                           (start_time::time >= time {5} AND end_time::time <= time {6}))
                      AND ST_Distance(origin, destination) > {7}
                      AND distance < {8} * ST_Distance(origin, destination)
                    )
                    ORDER BY user_id, id, plan_id;
                    """.format(ids_to_process, DateTime_to_Text(date_range_start), DateTime_to_Text(date_range_end), 
                               DateTime_to_SqlText(timeofday_start), DateTime_to_SqlText(timeofday_end), 
                               DateTime_to_SqlText(timeofday_start2), DateTime_to_SqlText(timeofday_end2), 
                               min_od_distance, od_d_diff_coeff)                                             
        log(["load_trips():: qstr:", qstr])
        log("")        
        res, trip_rows = self.db_command.ExecuteSQL(qstr)   
        
        total_trip_and_alt_count = trip_rows.rowcount
        
        trips = []
        if trip_rows.rowcount > 0:
            actualtrip = None
            for trip_row in trip_rows: 
                trip = Trip(trip_row)
                # OLD Code : Parse JSON into an object with attributes corresponding to dict keys
                # TODO: WARNING!!: (?) only works well if names of DB table columns are same as names of our Python Class attributes
                #   trip.__dict__= json.loads(trip_row['trip_as_json'])            
                                
                # TODO: IMPORTANT !!!: load trip legs * Needed??
                # ...
                
                # build the nested structure of 'trips' list in our program:
                if trip.plan_id == 0:
                    actualtrip = Trip()            
                    actualtrip = deepcopy(trip) # TODO: WARNING !!! is this neede?!!
                    trips.append(actualtrip)
                elif trip.plan_id > 0:
                    if actualtrip is not None:
                        actualtrip.alternative_trips.append(trip)                    
                # log(trip.user_id,  trip.id,  trip.plan_id,  trip.origin)
        
        return trips

    def load_observed_trips(self, date_from, date_to):
        qstr = """SELECT device_id as "device", user_id as "user", id as "trip", mainmode as "mode", multimodal_summary, 
            	start_time, end_time, 
            	st_y(geometry(origin)) olat, st_x(geometry(origin)) olon,
            	st_y(geometry(destination)) dlat, st_x(geometry(destination)) dlon,
            	duration, od_distance, distance_based_on_legs, distance, emission, 
            	time_by_mode, distance_by_mode, emission_by_mode,
            	CONCAT(st_y(st_astext(origin))::text , ',' , st_x(st_astext(origin))::text) origin,
            	CONCAT(st_y(st_astext(destination))::text , ',' , st_x(st_astext(destination))::text) destination,
            	EXTRACT (YEAR FROM start_time) AS year, EXTRACT (MONTH FROM start_time) AS month, EXTRACT (DAY FROM start_time) AS day,
            	EXTRACT (HOUR FROM start_time) AS hour_in_day,
                start_time_for_plan
            FROM trips_alts
            WHERE true
            
            AND plan_id = 0 -- Only to get the observed trips
            --AND plan_id > 0 -- Only to get the computed alternative trips
            
            --------- Mandatory Filters ------------
            AND duration > '00:00:00' 
            AND duration < '1 day' --TODO: Maybe due to the daylight saving?
            
            --------- Geographical Filters ---------:
            -- Helsinki region, only within the area (use AND): 
            AND point(geometry(origin)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
            AND point(geometry(destination)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
            -- Greater Jatkasaari rectangular boundaries, Trips from/to:
            --AND (point(geometry(origin)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)' 
            --OR point(geometry(destination)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)')
            
            ------- Date and Time Filters -----------:
            AND start_time >= '{}' AND start_time <= '{}'
            
            ORDER BY "user", trip, plan_id        
        """.format(str(date_from), str(date_to))        
                                           
        res, db_res = self.db_command.ExecuteSQL(qstr)
        
        if res and db_res.rowcount>0:
            trips_df = pd.DataFrame(db_res.fetchall())
            trips_df.columns = db_res.keys()
            print()
            print("load_observed_trips(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            trips_df = pd.DataFrame()
            print()
            print("load_observed_trips(): Loaded from DB, no records!")
            print()
    
        return trips_df
    
    def load_computed_trips(self, date_from, date_to):
        qstr = """SELECT device_id as "device", user_id as "user", id as "trip", mainmode as "mode", multimodal_summary, 
            	start_time, end_time, 
            	st_y(geometry(origin)) olat, st_x(geometry(origin)) olon,
            	st_y(geometry(destination)) dlat, st_x(geometry(destination)) dlon,
            	duration, od_distance, distance_based_on_legs, distance, emission, 
            	time_by_mode, distance_by_mode, emission_by_mode,
            	CONCAT(st_y(st_astext(origin))::text , ',' , st_x(st_astext(origin))::text) origin,
            	CONCAT(st_y(st_astext(destination))::text , ',' , st_x(st_astext(destination))::text) destination,
            	EXTRACT (YEAR FROM start_time) AS year, EXTRACT (MONTH FROM start_time) AS month, EXTRACT (DAY FROM start_time) AS day,
            	EXTRACT (HOUR FROM start_time) AS hour_in_day,
            	plan_id
            FROM trips_alts
            WHERE true
            
            --AND plan_id = 0 -- Only to get the observed trips
            AND plan_id > 0 -- Only to get the computed alternative trips
            
            --------- Mandatory Filters ------------
            AND duration > '00:00:00' AND duration < '1 day' --TODO: why there's such bugs?
            
            --------- Geographical Filters ---------:
            -- Helsinki region, only within the area (use AND): 
            AND point(geometry(origin)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
            AND point(geometry(destination)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
            -- Greater Jatkasaari rectangular boundaries, Trips from/to:
            --AND (point(geometry(origin)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)' 
            --OR point(geometry(destination)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)')
            
            ------- Date and Time Filters -----------:
            --AND start_time >= '2016-01-01 00:00:00' AND start_time <= '2019-04-01'
            AND start_time >= '{}' AND start_time <= '{}'
            
            ORDER BY "user", trip, plan_id        
        """.format(str(date_from), str(date_to))

        res, db_res = self.db_command.ExecuteSQL(qstr)
        
        if res and db_res.rowcount>0:
            trips_df = pd.DataFrame(db_res.fetchall())
            trips_df.columns = db_res.keys()
            print()
            print("load_computed_trips(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            trips_df = pd.DataFrame()
            print()
            print("load_computed_trips(): Loaded from DB, no records!")
            print()
    
        return trips_df
    
    def get_last_trip_end_time(self):
        qstr = """
            SELECT max(end_time) as max_end_time
            FROM trips_alts 
            WHERE plan_id = 0  -- Only to get the observed trips            
            """                                           
        res, db_res = self.db_command.ExecuteSQL(qstr)        
        if res and db_res.rowcount>0:
            for row in db_res:
                return row['max_end_time']
        else:
            return None
        
    def get_trip_legs(self, user_id, trip_starttime, trip_endtime):
        qstr = """
            SELECT user_id, legs.id as leg_id, time_start, time_end, modes.source
            FROM legs LEFT OUTER JOIN modes ON modes.leg = legs.id 
            WHERE true
            AND user_id = {}
            AND time_start >= '{}' AND time_end <= '{}'
            ORDER BY user_id, time_start,  -- IMPORTANT ORDER BY
            	CASE source
            	    WHEN 'USER' THEN 1
            	    WHEN 'LIVE' THEN 2 -- only for PT legs
            	    WHEN 'PLANNER' THEN 3
            	    --WHEN 'FILTERED' THEN 4 -- TODO
            	    ELSE 10
            	END;
                """.format(user_id, str(trip_starttime), 
                            str(trip_endtime + timedelta(seconds=1)) # IMPORTANT to shift forward the requested leg end-time, in case trip end-time's microsec was removed
                            )
        res, db_res = self.db_command.ExecuteSQL(qstr)
        if res and db_res.rowcount>0:
            return db_res
        else:
            return None
        
        
        
    def get_max_trip_id_per_user(self, date_range_start, date_range_end, ids_to_process=None):
        if ids_to_process is not None:
            raise Exception('Filtering based on ids_to_process, NOT implemented yet!')
        qstr = """
            SELECT l.user_id,
             		CASE max_trip_id IS NULL
            			WHEN true THEN 0 
            			ELSE max_trip_id 
             		END            
            FROM
            ( -- list of certain users with an activity within the desired dates, comes from this subquery
            	SELECT DISTINCT user_id
            	FROM legs            	
                WHERE time_start >= '{}' AND time_end <= '{}'
            ) l
            LEFT OUTER JOIN 
            ( -- absolute max trip_id of all users
            	SELECT user_id, max(id) as max_trip_id
            	FROM trips_alts        
            	GROUP BY user_id
            ) t ON (l.user_id = t.user_id)
            ORDER By l.user_id
            """.format(str(date_range_start), str(date_range_end))
        res, db_res = self.db_command.ExecuteSQL(qstr)                
        records_df = self._get_dataframe_from_dbres(res, db_res, 'get_max_trip_id_per_user')
        return records_df
        

    # =============================================================    
    def store_trips_without_alts(self, trips):   
        for trip in trips:
            self.store_trip(trip)

    def store_trips(self, ids_to_process, trips):        
        for trip in trips:
            self.store_trip(trip)
            for tripalt in trip.alternative_trips:
                self.store_trip(tripalt)        

    def store_trip_alternatives(self, trip):
        for tripalt in trip.alternative_trips:
            self.store_trip(tripalt)  
            
            
    def store_trips_alternatives(self, trips):            
        qstr_bacth = ''
        total_alts = 0
        for trip in trips:
            total_alts += len(trip.alternative_trips)
            for tripalt in trip.alternative_trips:
                qstr = self.store_trip_get_sql(tripalt)
                qstr_bacth += qstr
        
        res, db_res = self.db_command.ExecuteSQL(qstr_bacth) # Note: If db_command is transactional, re-raises the catched exception
        if not res:
            print("store_trips_alternatives():: FAILED!")
        return total_alts

           
    def store_trip_get_sql(self, trip):
        qstr = ""        
        try:
            qstr = """INSERT INTO trips_alts (user_id, device_id, id, plan_id, start_time, end_time, 
                   origin, destination, 
                   multimodal_summary, 
                   duration, cost, calories, emission, comfort, distance, time_by_mode, cost_by_mode, calories_by_mode, emission_by_mode, distance_by_mode, 
                   mainmode, start_time_for_plan, od_distance) 
                   VALUES ({0},{1},{2},{3},'{4}','{5}',
                   ST_GeomFromText('{6}'), ST_GeomFromText('{7}'),
                   '{8}',
                   '{9}',{10},{11},{12},{13},{14},
                   '{15}','{16}','{17}','{18}','{19}',
                   '{20}',
                   {21},{22}); """.format(
                   trip.user_id, trip.device_id, trip.id, trip.plan_id, DateTime_to_Text(trip.starttime), DateTime_to_Text(trip.endtime), 
                   pointRow_to_postgisPoint(trip.origin), pointRow_to_postgisPoint(trip.destination),
                   trip.multimodal_summary, 
                   DateTimeDelta_to_Text(trip.duration), 
                   round(trip.cost, 2), 
                   int(round(trip.calories)), 
                   round(trip.emission, 1),  # TODO, old: round(trip.emission/1000.0, 1), 
                   trip.comfort, 
                   round(trip.distance, 1),  # TODO
                   json.dumps(dict_timedelta_to_text(trip.duration_by_mode)),   #TODO, test and verify all following
                   json.dumps(round_dict_values(trip.cost_by_mode, 2)), 
                   json.dumps(round_dict_values(trip.calories_by_mode, 2)), 
                   json.dumps(round_dict_values(trip.emission_by_mode, 2)), 
                   json.dumps(round_dict_values(trip.distance_by_mode, 2)), 
                   trip.mainmode, 
                   DateTime_to_SqlText(trip.shifted_starttime_for_publictransport_tripplan), 
                   trip.od_distance
                   )
                   #round_dict_values(trip.duration_by_mode, 2), \
                   #round_dict_values(trip.cost_by_mode, 2),  round_dict_values(trip.calories_by_mode, 0), \
                   #round_dict_values(trip.emission_by_mode, 0), round_dict_values(trip.distance_by_mode, 0),\
                   #pointRow_to_geoText(trip.origin), pointRow_to_geoText(trip.destination)               
                   
            return qstr
        except Exception as e:
            print ("")
            print (">> store_trip_get_sql():: FAILED ------------------------------")
            print (">> For trip:", trip)
            print ("exception: ", e)
            print ("")
            raise #TODO NOTE critical .. so that BLL is able to rollback if needed *
    
    
    def store_trip(self, trip):
        # NOTE: example INSERT: insert into mytest (name) VALUES ('{''car'', ''walk''}'); 
        res = ""
        qstr = ""
        
        try:
            qstr = """INSERT INTO trips_alts (user_id, device_id, id, plan_id, start_time, end_time, 
                   origin, destination, 
                   multimodal_summary, 
                   duration, cost, calories, emission, comfort, distance, time_by_mode, cost_by_mode, calories_by_mode, emission_by_mode, distance_by_mode, 
                   mainmode, start_time_for_plan, od_distance) 
                   VALUES ({0},{1},{2},{3},'{4}','{5}',
                   ST_GeomFromText('{6}'), ST_GeomFromText('{7}'),
                   '{8}',
                   '{9}',{10},{11},{12},{13},{14},
                   '{15}','{16}','{17}','{18}','{19}',
                   '{20}',
                   {21},{22})""".format(
                   trip.user_id, trip.device_id, trip.id, trip.plan_id, DateTime_to_Text(trip.starttime), DateTime_to_Text(trip.endtime), 
                   pointRow_to_postgisPoint(trip.origin), pointRow_to_postgisPoint(trip.destination),
                   trip.multimodal_summary, 
                   DateTimeDelta_to_Text(trip.duration), 
                   round(trip.cost, 2), 
                   int(round(trip.calories)), 
                   round(trip.emission, 1),  # TODO, old: round(trip.emission/1000.0, 1), 
                   trip.comfort, 
                   round(trip.distance, 1),  # TODO
                   json.dumps(dict_timedelta_to_text(trip.duration_by_mode)),   #TODO, test and verify all following
                   json.dumps(round_dict_values(trip.cost_by_mode, 2)), 
                   json.dumps(round_dict_values(trip.calories_by_mode, 2)), 
                   json.dumps(round_dict_values(trip.emission_by_mode, 2)), 
                   json.dumps(round_dict_values(trip.distance_by_mode, 2)), 
                   trip.mainmode, 
                   DateTime_to_SqlText(trip.shifted_starttime_for_publictransport_tripplan), 
                   trip.od_distance
                   )
                   #round_dict_values(trip.duration_by_mode, 2), \
                   #round_dict_values(trip.cost_by_mode, 2),  round_dict_values(trip.calories_by_mode, 0), \
                   #round_dict_values(trip.emission_by_mode, 0), round_dict_values(trip.distance_by_mode, 0),\
                   #pointRow_to_geoText(trip.origin), pointRow_to_geoText(trip.destination)               
        except Exception as e:
            print ("")
            print (">> store_trip():: FAILED ------------------------------")
            print (">> trip to store:", trip)
            print ("exception: ", e)
            print ("")
            raise #TODO NOTE critical .. so that BLL is able to rollback if needed *
        
        try:
            res, db_res = self.db_command.ExecuteSQL(qstr)
        except Exception as e:
            print ("")
            print (">> store_trip():: FAILED ------------------------------")
            print (">> trip to store:", trip)
            print ("exception: ", e)
            print ("qstr: ", qstr)
            print ("")
            raise #TODO NOTE critical .. so that BLL is able to rollback if needed *
        log(["result:", str(res)])
        return res
        

    def delete_trips_to_legs(self, ids_to_process, date_range_start, date_range_end):
        qstr = """DELETE FROM trips_to_legs 
                    WHERE (user_id, trip_id, plan_id) IN
                    (SELECT user_id, id, plan_id FROM trips_alts
                     WHERE user_id IN ({0})
                     AND start_time >= '{1}' AND end_time <= '{2}'
                    );
                """.format(ids_to_process, DateTime_to_Text(date_range_start), DateTime_to_Text(date_range_end))
        log(["delete_trips_to_legs():: qstr for removing old rows before storing new ones:", qstr])
        res, db_res = self.db_command.ExecuteSQL(qstr)
        log(["result:", str(res)])
        log("")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def reset_trips_alts_flags(self, trips, flag_column_name, reset_value='false'):
        filter_str = ""
        for trip in trips: #reset flag of all plan_id (all alternatives of each trip)
            #example (2,237), (6, 237)
            filter_str = filter_str + "({}, {}), ".format(trip.user_id, trip.id)
        filter_str = filter_str[0:len(filter_str)-2]
            
        qstr = """UPDATE trips_alts SET {}={} 
                  WHERE (user_id, id) IN ({}); """.\
                  format(flag_column_name, reset_value, filter_str)        
        res, db_res = self.db_command.ExecuteSQL(qstr) 
        return res        
        
    def update_trips_alts_flags(self, fastest_choices, flag_column_name, new_value):
        filter_str = ""
        if fastest_choices == None or len(fastest_choices)==0:
            return False
            
        for trip in fastest_choices:
            #example (2,237,2), (2,237,3), (2,237,4), (6, 237)
            filter_str = filter_str + "({}, {}, {}), ".format(trip.user_id, trip.id, trip.plan_id)
        filter_str = filter_str[0:len(filter_str)-2]
            
        qstr = """UPDATE trips_alts SET {}={} 
                  WHERE (user_id, id, plan_id) IN ({}); """.\
                  format(flag_column_name, new_value, filter_str)        
        res, db_res = self.db_command.ExecuteSQL(qstr)        
        return res        
        
    def update_best_choices(self, trips):                        
        for trip in trips:            
            self.reset_trips_alts_flags([trip], 'fastest') # reset all trip-alts flags to ZERO            
            self.update_trips_alts_flags(trip.fastest_choices, 'fastest', 'true') # update according to results

    def update_trip_starttime_shifted_for_otp_query(self, trips):        
        qstr_bacth = ''
        for trip in trips:            
            qstr = """UPDATE trips_alts SET start_time_for_plan={}
                      WHERE user_id={} AND id={}
                      AND plan_id=0; """.\
                      format(DateTime_to_SqlText(trip.shifted_starttime_for_publictransport_tripplan),
                             trip.user_id, trip.id)
            qstr_bacth += qstr
        
        res, db_res = self.db_command.ExecuteSQL(qstr_bacth) 
        if not res:
            print("update_trip_starttime_shifted_for_otp_query():: FAILED!")
        return res




        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # find an origin/destination (od) previosuly detected and stored. match in certain proximity
    def find_trip_od_for_recorded_location(self, recorded_geoloc, distance_inaccuracy_threshold):        
        qstr = """SELECT geoloc 
                    FROM trip_origin_destinations  
                    WHERE ST_Distance(geoloc, ST_GeomFromText('{0}')) <= {1}
                    """.format(pointRow_to_postgisPoint(recorded_geoloc), distance_inaccuracy_threshold)  
        log(["find_trip_od_for_recorded_location():: qstr:", qstr])
        log("")
        res, trip_od_rows = self.db_command.ExecuteSQL(qstr)   
        
        if trip_od_rows.rowcount > 0:
            for trip_od_row in trip_od_rows: 
                return trip_od_row['geoloc']
        
        return None

    def store_trip_od_location(self, recorded_geoloc, distance_inaccuracy_threshold): 
        qstr = """INSERT INTO trip_origin_destinations (geoloc, distance_inaccuracy_threshold)
                        VALUES (ST_GeomFromText('{0}'), {1})
                        """.format(pointRow_to_postgisPoint(recorded_geoloc), distance_inaccuracy_threshold) 
        log(["store_trip_od_location:: qstr:", qstr])
        log("")
        
        res, db_res = self.db_command.ExecuteSQL(qstr)
        log(["result:", str(res)]) 
        return res
