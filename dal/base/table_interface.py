
import pandas as pd

class TableInterface:
    def __init__(self, db_command):
        self.db_command = db_command

    def _get_delete_macthed_count(self, res, db_query_res):
        if res:
            return db_query_res.rowcount
        else:
            return 0

    def _get_dataframe_from_dbres(self, res, db_res, calling_function_name):
        
        if res and db_res.rowcount>0:
            records_df = pd.DataFrame(db_res.fetchall())
            records_df.columns = db_res.keys()
            print()
            print(calling_function_name + "(): Loaded from DB,",db_res.rowcount,"records")
            print()
        else:
            records_df = pd.DataFrame()
            print()
            print(calling_function_name+"(): Loaded from DB, no records!")
            print()
    
        return records_df