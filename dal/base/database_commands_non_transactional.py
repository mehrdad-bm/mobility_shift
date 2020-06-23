from sqlalchemy.sql import text

from commonlayer.logger import (log, logi, logexc)
from dal.base.database_commands import DatabaseCommands

class DatabaseCommandsNonTransactional (DatabaseCommands):
    def __init__(self, db_engine):
        self.db_engine = db_engine

    def ExecuteSQL(self, query_string, LOG_IMPORTANT_CUSTOM = True):
        qstr = query_string        
        log(["DatabaseCommands::ExecuteSQL() qstr:", qstr])
            
        db_res = None
        res = False
        try:
            db_res = self.db_engine.execute(text(qstr))
            res = True
        except Exception as e:
            self._log_exception("DatabaseCommandsNonTransactional::ExecuteSQL()", qstr, str(e))            
        return res, db_res
