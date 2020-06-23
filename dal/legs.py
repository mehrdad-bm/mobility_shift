# ~~~ this class/file should be in package (namespace) DAL ~~~

from commonlayer.common_helper_class import CommonHelper 
from dal.base.table_interface import TableInterface
import pandas as pd

class Legs(TableInterface):    
    # Load legs, and choose the best (first priority) mode detected for each leg among USER, LIVE, PLANNER mode detection sources
    def load_legs(self, ids_to_process, date_range_start, date_range_end):        
#        qstr = "SELECT id, user_id, device_id, time_start, time_end, ST_AsGeoJSON(coordinate_start) as origin, ST_AsGeoJSON(coordinate_end) destination, " \
#                "activity, line_type, line_name, line_source, time_end - time_start as duration " \
#                "FROM legs WHERE user_id IN({0}) AND time_start >= '{1}' AND time_end <= '{2}' "\
#                "ORDER BY user_id, time_start ;".format(ids_to_process, str(date_range_start), str(date_range_end))
#                # TODO! IMPORTANT ... REMOVE : Order by device_id
        if ids_to_process is None or len(ids_to_process)==0:
            qstr = """
                SELECT legs.id as id, user_id, device_id, time_start, time_end, 
                        ST_AsGeoJSON(coordinate_start) as origin, ST_AsGeoJSON(coordinate_end) destination,
                        	CONCAT('(', st_y(st_astext(coordinate_start))::text , ',' , st_x(st_astext(coordinate_start))::text, ')') origin_tuple,
                        	CONCAT('(', st_y(st_astext(coordinate_end))::text , ',' , st_x(st_astext(coordinate_end))::text, ')') destination_tuple,	                        
                        	st_y(geometry(coordinate_start)) olat, st_x(geometry(coordinate_start)) olon,
                        	st_y(geometry(coordinate_end)) dlat, st_x(geometry(coordinate_end)) dlon,                            
                        activity, modes.mode as line_type, line as line_name, source as line_source, time_end - time_start as duration,
                        km as distance_km
                FROM legs LEFT OUTER JOIN modes ON modes.leg = legs.id 
                WHERE time_start >= '{}' AND time_end <= '{}'
                ORDER BY user_id, time_start,  -- IMPORTANT ORDER BY
                        CASE source
                            WHEN 'USER' THEN 1
                            WHEN 'LIVE' THEN 2 -- only for PT legs
                            WHEN 'PLANNER' THEN 3
                            --WHEN 'FILTERED' THEN 4 -- TODO
                            ELSE 10
                        END;
                """.format(str(date_range_start), str(date_range_end))
        else:
            qstr = """
                SELECT legs.id as id, user_id, device_id, time_start, time_end, 
                        ST_AsGeoJSON(coordinate_start) as origin, ST_AsGeoJSON(coordinate_end) destination,
                        activity, modes.mode as line_type, line as line_name, source as line_source, time_end - time_start as duration
                FROM legs LEFT OUTER JOIN modes ON modes.leg = legs.id 
                WHERE user_id IN({}) 
                AND time_start >= '{}' AND time_end <= '{}'
                ORDER BY user_id, time_start, 
                        CASE source
                            WHEN 'USER' THEN 1
                            WHEN 'LIVE' THEN 2 -- only for PT legs
                            WHEN 'PLANNER' THEN 3
                            --WHEN 'FILTERED' THEN 4 -- TODO
                            ELSE 10
                        END;
                """.format(ids_to_process, str(date_range_start), str(date_range_end))                
        res, legs = self.db_command.ExecuteSQL(qstr)
        return legs


    def get_leg_points(self, leg):
        qstr = """
            SELECT time, ST_AsGeoJSON(coordinate) as coo, activity, line_type, line_name 
            FROM device_data_filtered 
            WHERE user_id = {0} 
            AND time>='{1}' AND time<='{2}'
            ORDER BY time;
        """.format(leg['user_id'], str(leg['time_start']), str(leg['time_end']))            
        res, leg_points = self.db_command.ExecuteSQL(qstr)
        return leg_points

    def get_leg_median_points(self, leg):
        qstr = """
            SELECT * FROM
            (
            	SELECT *, round(avg(row_number) over()) as middle_row
            	FROM(
            	    SELECT --user_id, id, waypoint_id,
                		time, ST_AsGeoJSON(coordinate) as coo, activity, line_type, line_name,
                        st_y(geometry(coordinate)) lat, st_x(geometry(coordinate)) lon,                        
                        row_number() over()
            	    FROM device_data_filtered 
            	    WHERE user_id = {0}
            	    AND time>='{1}' AND time<='{2}'
            	    ORDER BY time
            	) t
            ) tt
            WHERE true
            AND row_number = middle_row;
        """.format(leg['user_id'], str(leg['time_start']), str(leg['time_end']))            
        res, db_res = self.db_command.ExecuteSQL(qstr, LOG_IMPORTANT_CUSTOM=False)
        
        point = {'lat':0, 'lon':0}        
        if res and db_res.rowcount>0:
            for row in db_res: 
                point['lat'] = row['lat']
                point['lon'] = row['lon']
        else:
            print()
            print("get_leg_median_points(): Loaded from DB, no records!")
            print()
                
        return (point['lat'], point['lon'])

    def get_leg_points_selection(self, leg):
        qstr = """
            SELECT * FROM
            (
            	SELECT *, round(avg(row_number) over()) as middle_row, max(row_number) over() as last_row
            	FROM
                (
        			Select *, row_number() over() 
        			FROM
        			(
        			    SELECT --user_id, id, waypoint_id,
        				time, ST_AsGeoJSON(coordinate) as coo, activity, line_type, line_name,
        				st_y(geometry(coordinate)) lat, st_x(geometry(coordinate)) lon			
        			    FROM device_data_filtered 
                	    WHERE user_id = {0}
                	    AND time>='{1}' AND time<='{2}'
        			    ORDER BY time
        			) ti
            	) t
            ) tt
            WHERE true
            AND (row_number = middle_row OR row_number = 1 OR row_number = last_row) 
            ORDER BY row_number;
        """.format(leg['user_id'], str(leg['time_start']), str(leg['time_end']))            
        res, db_res = self.db_command.ExecuteSQL(qstr, LOG_IMPORTANT_CUSTOM=False)
        
        points = list()
        if res and db_res.rowcount>0:
            for row in db_res: 
                points.append((row['lat'], row['lon']))
        else:
            print()
            print("get_leg_points_selection(): Loaded from DB, no records!")
            print()
                
        return points

    # Load legs, and choose the best (first priority) mode detected for each leg among USER, LIVE, PLANNER mode detection sources
    def load_observed_trip_to_legs(self):        
        qstr = """
                SELECT user_id as "user", trip_id as "trip", plan_id, leg_id
                FROM  trips_to_legs
                WHERE plan_id = 0
                ORDER by user_id, trip_id
                ;
                """
        res, db_res = self.db_command.ExecuteSQL(qstr)

        if res and db_res.rowcount>0:
            records_df = pd.DataFrame(db_res.fetchall())
            records_df.columns = db_res.keys()
            print()
            print("load_observed_trip_to_legs(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            records_df = pd.DataFrame()
            print()
            print("load_observed_trip_to_legs(): Loaded from DB, no records!")
            print()
    
        return records_df


    def load_observed_legs(self):        
        qstr = """
            SELECT * FROM
            (
                SELECT 
                    devices.user_id as user_id, 
                    legs.user_id user_id_in_leg,                         
                    legs.device_id, 
                    legs.id as leg_id, 
            	time_start, time_end, 
            	CONCAT('(', st_y(st_astext(coordinate_start))::text , ',' , st_x(st_astext(coordinate_start))::text, ')') origin,
            	CONCAT('(', st_y(st_astext(coordinate_end))::text , ',' , st_x(st_astext(coordinate_end))::text, ')') destination,	
            	st_y(geometry(coordinate_start)) olat, st_x(geometry(coordinate_start)) olon,
            	st_y(geometry(coordinate_end)) dlat, st_x(geometry(coordinate_end)) dlon,                
            	activity, modes.mode as line_type, line as line_name, source, time_end - time_start as duration,
            	km,
                CASE source
            	  WHEN 'USER' THEN 1
            	  WHEN 'LIVE' THEN 2 -- only for PT legs
            	  WHEN 'PLANNER' THEN 3 -- only for PT legs ?
            	  --WHEN 'FILTERED' THEN 4 -- TODO
            	  ELSE 10
            	END as source_order
                FROM legs LEFT OUTER JOIN modes ON modes.leg = legs.id 
            	INNER JOIN devices ON devices.id = legs.device_id
            ) t
            WHERE true
            ORDER BY user_id, time_start, source_order
            """
       
        res, db_res = self.db_command.ExecuteSQL(qstr)

        if res and db_res.rowcount>0:
            records_df = pd.DataFrame(db_res.fetchall())
            records_df.columns = db_res.keys()
            print()
            print("load_observed_legs(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            records_df = pd.DataFrame()
            print()
            print("load_observed_legs(): Loaded from DB, no records!")
            print()
    
        return records_df

    
    def load_observed_movement_legs(self):        
        qstr = """
            SELECT * FROM
            (
                SELECT 
                    devices.user_id as user_id, 
                    legs.user_id user_id_in_leg,                         
                    legs.device_id, 
                    legs.id as leg_id, 
            	time_start, time_end, 
            	CONCAT('(', st_y(st_astext(coordinate_start))::text , ',' , st_x(st_astext(coordinate_start))::text, ')') origin,
            	CONCAT('(', st_y(st_astext(coordinate_end))::text , ',' , st_x(st_astext(coordinate_end))::text, ')') destination,	
            	st_y(geometry(coordinate_start)) olat, st_x(geometry(coordinate_start)) olon,
            	st_y(geometry(coordinate_end)) dlat, st_x(geometry(coordinate_end)) dlon,
            	activity, modes.mode as line_type, line as line_name, source, time_end - time_start as duration,
            	km,
                CASE source
            	  WHEN 'USER' THEN 1
            	  WHEN 'LIVE' THEN 2 -- only for PT legs
            	  WHEN 'PLANNER' THEN 3 -- only for PT legs ?
            	  --WHEN 'FILTERED' THEN 4 -- TODO
            	  ELSE 10
            	END as source_order
                FROM legs LEFT OUTER JOIN modes ON modes.leg = legs.id 
            	INNER JOIN devices ON devices.id = legs.device_id
                WHERE true
                AND activity != 'STILL'
            ) t
            WHERE true
            --AND source = 'FILTERED'
            --AND source_order = 10
            ORDER BY user_id, time_start, source_order
            """
       
        res, db_res = self.db_command.ExecuteSQL(qstr)

        if res and db_res.rowcount>0:
            records_df = pd.DataFrame(db_res.fetchall())
            records_df.columns = db_res.keys()
            print()
            print("load_observed_movement_legs(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            records_df = pd.DataFrame()
            print()
            print("load_observed_movement_legs(): Loaded from DB, no records!")
            print()
    
        return records_df
        