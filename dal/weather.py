# ~~~ this class/file should be in package (namespace) DAL ~~~


from commonlayer.logger import (log, logi, loge)
from dal.base.table_interface import TableInterface
import pandas as pd

class Weather(TableInterface):

    def load_observed_weather(self):
        qstr = """
            SELECT time_observed::date weather_date, DATE_PART('hour', time_observed) as hour_in_day, 
            	temperature, windspeed_ms, precipitation_1h
            FROM weather_observations
            ORDER BY time_observed
            """
        
        res, db_res = self.db_command.ExecuteSQL(qstr)

        if res and db_res.rowcount>0:
            records_df = pd.DataFrame(db_res.fetchall())
            records_df.columns = db_res.keys()
            print()
            print("load_observed_weather(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            records_df = pd.DataFrame()
            print()
            print("load_observed_weather(): Loaded from DB, no records!")
            print()
    
        return records_df

    

 
    