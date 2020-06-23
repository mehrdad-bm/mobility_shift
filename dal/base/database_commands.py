from sqlalchemy.sql import text

from commonlayer.logger import (logexc)

class DatabaseCommands:
    def __init__(self):
        print ("DatabaseCommands base class constructor")

    def _log_exception (self, method_name, qstr, exception):
        if method_name is None:
            method_name = "DatabaseCommands::???()"
        logexc(">> (!) EXCEPTION catched in {}: DB Command FAILED ......................".format(method_name), 
              exception,
              [">> qstr:", qstr, "......................................................"],
              True)
