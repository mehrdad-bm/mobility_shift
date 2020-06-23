from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from commonlayer.logger import logexc

class DatabaseSession:
    def __init__(self, db_engine):
        self.db_engine = db_engine        
        # create a configured "Session" class
        Session = sessionmaker(autocommit=False, autoflush=False, bind=self.db_engine)
        # create a Session
        self.session = Session() #NOTE: a new transaction will begin as soon as the first DB query is sent (remeber ot commit it!)

    def __del__(self):    
        self.session.close() #TODO: right thing to do?

    def execute(self, qstr):
        db_res = self.session.execute(text(qstr)) # transaction starts here, if not started before
        return db_res
        
    def start_transaction(self):
        # TODO: maybe close or commit previously forgotten session ?
        pass
        
    def commit_transaction(self):
        try:
            self.session.commit()
        except Exception as e:
            logexc(["DatabaseSession::commit_transaction() FAILED ..................", 
             "EXCEPTION catched: "], e, 
             "......................................................", True)

    def rollback_transaction(self):
        try:
            self.session.rollback()
        except Exception as e:
            logexc(["DatabaseSession::rollback_transaction() FAILED ..................", 
             "EXCEPTION catched: "], e, 
             "......................................................", True)
