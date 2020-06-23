
# logging helpers :
# 

#import logging
#logging.basicConfig(level=logging.DEBUG)
#logger = logging.getLogger(__name__)

import traceback

# generate extensive logs if required!
LOG_DETAILS = False
LOG_IMPORTANT = True
LOG_ERRORS = True
#LOG_ERROR_CALLSTACK = True

class Logger():
    __no_of_logged_exceptions = 0
    def __init__(self):
        pass
        
    @classmethod
    def reset_no_of_logged_exceptions(cls):
        cls.__no_of_logged_exceptions = 0
    @classmethod
    def _increase_no_of_logged_exceptions(cls):
        cls.__no_of_logged_exceptions += 1
    @classmethod
    def get_no_of_logged_exceptions(cls):
        return cls.__no_of_logged_exceptions


def logmultiple(params, nextline_for_each_param=False): # base multiple-param logging function
    if nextline_for_each_param:
        for param in params:
            print (param)
        else:
            print
    else:
        for param in params:
            print (param,)
        else:
            print    
#    log.info
#    log.warning
#    log.exception

def log(params):
    if LOG_DETAILS: logmultiple(params)
    
def logi(params, LOG_IMPORTANT_CUSTOM=True): # log important data or messages
    if LOG_IMPORTANT and LOG_IMPORTANT_CUSTOM: logmultiple(params)

def loge(params, nextline_for_each_param=False): # log errors and warnings
    if LOG_ERRORS: logmultiple(params, nextline_for_each_param)

def logexc(params, exception, extra_params = None, nextline_for_each_param = False): # log errors and warnings
    # convert the params input to a list (if not already a list)
    params_list = []
    if params is not None:
        params_list.append(params)    
        params_list.append(",")
    params_list.append("Exception: {}: {}".format(type(exception), str(exception)))    
    logmultiple(params_list, nextline_for_each_param)
    
    print (traceback.format_exc(10))
    
    if extra_params is not None:
        params_list = []
        params_list.append(extra_params)
        logmultiple(params_list, nextline_for_each_param)

    Logger._increase_no_of_logged_exceptions()
    
