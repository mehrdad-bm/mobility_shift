from sqlalchemy.sql import text

from commonlayer.logger import (log, logi, logexc)
from dal.base.database_commands import DatabaseCommands

class DatabaseCommandsTransactional (DatabaseCommands):
    def __init__(self, session):
        self.session = session #NOTE: a new transaction will begin as soon as the first DB query is sent (remeber ot commit it!)

    def ExecuteSQL(self, query_string):
        qstr = query_string        
        log(["DatabaseCommandsTransactional::ExecuteSQL() qstr:", qstr])
            
        db_res = None
        res = False            
        try:
            db_res = self.session.execute(qstr) # transaction starts here, if not started before
            res = True
        except Exception as e: 
            self._log_exception("DatabaseCommandsTransactional::ExecuteSQL()", qstr, str(e))            
            raise e #TODO NOTE! Crucial; So that it is passed eventually to BLL level that will call rollback() if needed
            # TODO: But, for an easier approach, shouldn't this function itself Rollback the transaction??
                
        return res, db_res
    
