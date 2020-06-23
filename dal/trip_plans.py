#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 19 13:30:14 2020

@author: mehrdad
"""

# NOTE: This class/file is meant to be located in a data-access-layer (DAL) package/namespace

from commonlayer.common_helper_class import CommonHelper 
from dal.base.table_interface import TableInterface
import pandas as pd

class TripPlans(TableInterface):
                        
    def load_trip_plan(self, trip, mode, numItineraries, maxWalkDistance):
        qstr = """SELECT start_time, 
                                ST_AsText(origin) as origin, ST_AsText(destination) as destination, 
                                mode, max_walk_distance, no_of_itins, 
                                plan 
                            FROM trip_plans  
                            WHERE start_time = '{0}' AND 
                                origin = '{1}' AND destination = '{2}' AND
                                mode = '{3}' AND max_walk_distance = {4} AND no_of_itins = {5};
                            """.format(
                                CommonHelper.DateTime_to_Text(trip.starttime),  
                                CommonHelper.pointRow_to_postgisPoint(trip.origin), CommonHelper.pointRow_to_postgisPoint(trip.destination), 
                                mode,  maxWalkDistance,  numItineraries
                            )                    
        res, plan_rows = self.db_command.ExecuteSQL(qstr, LOG_IMPORTANT_CUSTOM = False)
        return res, plan_rows
                
    def store_trip_plan(self, trip, mode, numItineraries, maxWalkDistance,  plan):
        qstr = """INSERT INTO trip_plans (start_time, origin, destination, mode, max_walk_distance, no_of_itins, plan) 
                    VALUES ('{0}', 
                    ST_GeomFromText('{1}'), ST_GeomFromText('{2}'), 
                    '{3}',{4},{5},
                    '{6}' ); """.format(
                    CommonHelper.DateTime_to_Text(trip.starttime), 
                    CommonHelper.pointRow_to_postgisPoint(trip.origin), CommonHelper.pointRow_to_postgisPoint(trip.destination), 
                    mode, maxWalkDistance, numItineraries, 
                    CommonHelper.json_to_sqlstr(plan)
                    )        
        res, db_res = self.db_command.ExecuteSQL(qstr, LOG_IMPORTANT_CUSTOM=False)
        return res
        
    def delete_trip_plan(self, trip, mode, numItineraries, maxWalkDistance):
        qstr = """DELETE FROM trip_plans
                    WHERE start_time = '{0}' AND 
                        origin = '{1}' AND destination = '{2}' AND
                        mode = '{3}' AND max_walk_distance = {4} AND no_of_itins = {5};
                    """.format(
                        CommonHelper.DateTime_to_Text(trip.starttime),  
                        CommonHelper.pointRow_to_postgisPoint(trip.origin), CommonHelper.pointRow_to_postgisPoint(trip.destination), 
                        mode,  maxWalkDistance,  numItineraries
                    )
        res, db_res = self.db_command.ExecuteSQL(qstr, LOG_IMPORTANT_CUSTOM=False)
        return res, self._get_delete_macthed_count(res, db_res)


    def load_failed_OTP_plans(self):
        qstr = """
            SELECT user_id as "user", trip_id as "trip", t.start_time, 
            	--ST_AsText(t.origin) origin, ST_AsText(t.destination) destination, 
            	CONCAT('(', st_y(st_astext(tt.origin))::text , ',' , st_x(st_astext(tt.origin))::text, ')') plan_origin,
            	CONCAT('(', st_y(st_astext(tt.destination ))::text , ',' , st_x(st_astext(tt.destination))::text, ')') plan_destination,	
                
            	mode as mainmode, max_walk_distance, no_of_itins, plan
            FROM
            (
            	-- Observed trips with zero computed alternative (no walk, bike, PT) --
            	SELECT user_id, id as trip_id, 
            		start_time, origin, destination
            	From trips_alts 
            	WHERE plan_id = 0
                --------- Mandatory Filters ------------
                AND duration > '00:00:00' AND duration < '1 day' --TODO: why there's such bugs?
                
                --------- Geographical Filters ---------:
                -- Helsinki region, only within the area (use AND): 
                AND point(geometry(origin)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
                AND point(geometry(destination)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
                -- Greater Jatkasaari rectangular boundaries, Trips from/to:
                --AND (point(geometry(origin)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)' 
                --OR point(geometry(destination)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)')
                
            	AND (user_id, id) not in 
            	(
            		select user_id, id		
            		from trips_alts 
            		where plan_id > 0
            	)
            ) t 
            INNER JOIN (SELECT * FROM trip_plans) tt
            ON (tt.start_time = t.start_time AND tt.origin = t.origin AND tt.destination = t.destination)	
            ORDER BY user_id, trip_id, mode
            """
        
        res, db_res = self.db_command.ExecuteSQL(qstr)

        if res and db_res.rowcount>0:
            records_df = pd.DataFrame(db_res.fetchall())
            records_df.columns = db_res.keys()
            print()
            print("load_failed_OTP_computations(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            records_df = pd.DataFrame()
            print()
            print("load_failed_OTP_computations(): Loaded from DB, no records!")
            print()
    
        return records_df



    def load_trips_with_otp_plans(self, plan_mode):
        qstr = """
        SELECT user_id as "user", id as "trip"  
        FROM 
        (
            SELECT user_id, id, origin, destination, 
                	(CASE 
                		WHEN start_time_for_plan is null THEN start_time
                		ELSE start_time_for_plan
                	END) as otp_pt_query_start_time -- ONLY for PT OTP queries
        	From trips_alts 
        	where plan_id = 0 
            -- AND mainmode = '{0}'
        	    --------- Mandatory Filters ------------
        	    AND duration > '00:00:00' AND duration < '1 day' --TODO: why there's such bugs?
        	    
        	    --------- Geographical Filters ---------:
        	    -- Helsinki region, only within the area (use AND): 
        	    AND point(geometry(origin)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
        	    AND point(geometry(destination)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
        	    -- Greater Jatkasaari rectangular boundaries, Trips from/to:
        	    --AND (point(geometry(origin)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)' 
        	    --OR point(geometry(destination)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)')
    	) t
        
    	WHERE (t.otp_pt_query_start_time, t.origin, t.destination) in 
    	(
    		select start_time, origin, destination --, mode as plan_mode, max_walk_distance, no_of_itins, plan
    		from trip_plans
    		where mode = '{0}'
    	)    
        """.format(plan_mode)
        
        res, db_res = self.db_command.ExecuteSQL(qstr)

        if res and db_res.rowcount>0:
            records_df = pd.DataFrame(db_res.fetchall())
            records_df.columns = db_res.keys()
            print()
            print("load_trips_wtih_otp_plans(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            records_df = pd.DataFrame()
            print()
            print("load_trips_wtih_otp_plans(): Loaded from DB, no records!")
            print()
    
        return records_df
        
    
    def load_unrecorded_OTP_plans(self):
        qstr = """
            SELECT user_id as "user", trip_id as "trip", t.start_time, otp_pt_query_start_time, 
            	--ST_AsText(t.origin) origin, ST_AsText(t.destination) destination, 
            	CONCAT('(', st_y(st_astext(tt.origin))::text , ',' , st_x(st_astext(tt.origin))::text, ')') plan_origin,
            	CONCAT('(', st_y(st_astext(tt.destination ))::text , ',' , st_x(st_astext(tt.destination))::text, ')') plan_destination,	
                
            	mode as mainmode, max_walk_distance, no_of_itins, plan
            FROM
            (
            	-- Observed trips with zero computed alternative (no walk, bike, PT) --
            	SELECT user_id, id as trip_id, 
            		start_time, origin, destination
                	(CASE 
                		WHEN start_time_for_plan is null THEN start_time
                		ELSE start_time_for_plan
                	END) as otp_pt_query_start_time -- ONLY for PT OTP queries                                        
                    
            	From trips_alts 
            	WHERE plan_id = 0
                --------- Mandatory Filters ------------
                AND duration > '00:00:00' AND duration < '1 day' --TODO: why there's such bugs?
                
                --------- Geographical Filters ---------:
                -- Helsinki region, only within the area (use AND): 
                AND point(geometry(origin)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
                AND point(geometry(destination)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
                -- Greater Jatkasaari rectangular boundaries, Trips from/to:
                --AND (point(geometry(origin)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)' 
                --OR point(geometry(destination)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)')
                
            	AND (user_id, id) NOT IN 
            	(
            		SELECT user_id, id	
            		FROM trips_alts 
            		WHERE plan_id > 0
            	)
            ) t 
            INNER JOIN (SELECT * FROM trip_plans) tt
            ON (tt.start_time = t.otp_pt_query_start_time AND tt.origin = t.origin AND tt.destination = t.destination)	
            ORDER BY user_id, trip_id, mode
            """
        
        res, db_res = self.db_command.ExecuteSQL(qstr)

        if res and db_res.rowcount>0:
            records_df = pd.DataFrame(db_res.fetchall())
            records_df.columns = db_res.keys()
            print()
            print("load_failed_OTP_computations(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            records_df = pd.DataFrame()
            print()
            print("load_failed_OTP_computations(): Loaded from DB, no records!")
            print()
    
        return records_df
    
    
    def load_trips_and_OTP_plans(self, plan_mode):
#            	    --ST_AsText(t.origin) origin, ST_AsText(t.destination) destination, 
#            	    --CONCAT('(', st_y(st_astext(tt.origin))::text , ',' , st_x(st_astext(tt.origin))::text, ')') plan_origin,
#            	    --CONCAT('(', st_y(st_astext(tt.destination ))::text , ',' , st_x(st_astext(tt.destination))::text, ')') plan_destination,	                            	
        
        qstr = """
            SELECT user_id as "user", trip_id as "trip", t.start_time, otp_pt_query_start_time,                     
                    tt.mode as plan_mode, max_walk_distance, no_of_itins, plan
            FROM
            (
            	SELECT user_id, id as trip_id, 
            		start_time, origin, destination,
                	(CASE 
                		WHEN start_time_for_plan is null THEN start_time
                		ELSE start_time_for_plan
                	END) as otp_pt_query_start_time -- Applicable ONLY for PT OTP queries?
                    
            	From trips_alts
            	WHERE plan_id = 0
                --------- Mandatory Filters ------------
                AND duration > '00:00:00' AND duration < '1 day' --TODO: why there's such bugs?
                
                --------- Geographical Filters ---------:
                -- Helsinki region, only within the area (use AND): 
                AND point(geometry(origin)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
                AND point(geometry(destination)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
                -- Greater Jatkasaari rectangular boundaries, Trips from/to:
                --AND (point(geometry(origin)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)' 
                --OR point(geometry(destination)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)')                
            ) t 
            INNER JOIN 
            (
                SELECT * FROM trip_plans
                WHERE mode = '{0}'
            ) tt
            ON (tt.start_time = t.otp_pt_query_start_time AND tt.origin = t.origin AND tt.destination = t.destination)	
            ORDER BY user_id, trip_id, mode
            """.format(plan_mode)
        
        res, db_res = self.db_command.ExecuteSQL(qstr)

        records_df = self._get_dataframe_from_dbres(res, db_res, 'load_trips_OTP_plans')
        
#        if res and db_res.rowcount>0:
#            records_df = pd.DataFrame(db_res.fetchall())
#            records_df.columns = db_res.keys()
#            print()
#            print("load_trips_OTP_plans(): Loaded from DB,",db_res.rowcount,"records")
#            print()
#        else:
#            records_df = pd.DataFrame()
#            print()
#            print("load_trips_OTP_plans(): Loaded from DB, no records!")
#            print()
    
        return records_df    