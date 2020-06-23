# ~~~ this class/file should be in package (namespace) DAL ~~~


from commonlayer.common_helper_class import CommonHelper
from commonlayer.logger import (log, logi, loge)
from pyfiles.common_helpers import (pointRow_to_geoText, pointRow_to_postgisPoint, DateTimeDelta_to_Text, dict_to_sqlstr)
from dal.base.table_interface import TableInterface
import pandas as pd

class Users(TableInterface):

    def load_user_activity_stats(self
                                 #, from_date, to_date
                                 ):
        qstr = """
                SELECT user_id as "user", 
                		min(leg_date) as first_active_day, max(leg_date) as last_active_day,
                		max(leg_date) - min(leg_date)+ 1 as active_days_range, 
                		count(*) active_days, --days with at least one leg recorded
                		sum(leg_count) total_legs,
                		round(sum(leg_count)/count(*), 1) as avg_legs_per_active_day
                FROM (
                	SELECT 
                		legs.user_id, time_start::date as leg_date,
                		count(*) as leg_count
                	FROM legs INNER JOIN users ON (legs.user_id = users.id)
                		INNER JOIN devices ON (legs.user_id = devices.user_id AND legs.device_id = devices.id)
                	WHERE true
                	AND activity != 'STILL'
                	--AND time_start > '{0}'
                	--AND time_start < '{1}'
                	--AND devices.created > '2019-03-01 00:00:00' -- Activate this filter only if needed
                	--AND users.register_timestamp > '2019-03-01 00:00:00'	
                	-- Get only the legs with either Origin or Destination in the desired area: 
                
                    --------- Geographical Filters ---------:
                    -- Helsinki region, only within the area (use AND): 
                    --AND point(geometry(legs.coordinate_start)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
                    --AND point(geometry(legs.coordinate_start)) <@ box'(24.572978,60.100104)(25.216365, 60.336453)' -- Helsinki region rectangular boundaries			
                
                    -- Greater Jatkasaari rectangular boundaries, Trips from/to:
                    --AND (point(geometry(legs.coordinate_start)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)' 
                    --OR point(geometry(legs.coordinate_start)) <@ box'(24.895571, 60.145601)(24.931923, 60.168201)')
                    
                    -- Jätkäsaari region rectangular boundaries, Trips from/to:
                    --AND (point(geometry(legs.coordinate_start)) <@ box'(24.900635, 60.147222)(24.925655, 60.162214)' 
                    --OR point(geometry(legs.coordinate_end)) <@ box'(24.900635, 60.147222)(24.925655, 60.162214)')
                	                	
                	GROUP BY legs.user_id, time_start::date	
                	ORDER BY legs.user_id, time_start::date	
                ) tt
                GROUP BY user_id
                ORDER BY user_id        
                """#.format(from_date, to_date)
                                           
        res, db_res = self.db_command.ExecuteSQL(qstr)
        
        if res and db_res.rowcount>0:
            df = pd.DataFrame(db_res.fetchall())
            df.columns = db_res.keys()
            print()
            print("load_user_activity_stats(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            df = pd.DataFrame()
            print()
            print("load_user_activity_stats(): Loaded from DB, no records!")
            print()
    
        return df

