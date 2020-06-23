import json
import requests
import urllib.error
#import urllib2

from commonlayer.logger import (log, logexc, loge)
from commonlayer.networking import Networking

class WebNetworking(Networking):
    
    def send_http_get(self, apiurl, querystr = None,  verify_certificate = False):
        # Notes for urllib2: 
        #   GET request with urllib2: If you do not pass the data argument, urllib2 uses a GET request (you can encode the data in URL itself)
        #   POST request with urllib2: Just as easy as GET, simply passing (encoded) request data as an extra parameter
        #params = urllib.urlencode(querystr)
        
        apiurl_with_query = apiurl
        params = querystr
        if params is not None and params != '':
            apiurl_with_query += "?" + params
        #log(["params:", params])
        #log(["apiurl_with_query:", apiurl_with_query, "verify_certificate:", verify_certificate])

        response = None
        res = False
        e = None
        exception_type = ""
        try:
            #response = urllib2.urlopen(apiurl_with_query)
            log(["send_http_get():", apiurl_with_query])
            
            response = requests.get(apiurl_with_query, verify=verify_certificate) # //TODO: possible security issue! verify=True works from python command line !!!!
            response.close()
            if response.status_code == 200: #TODO: does it happen that status_code is NOT CHANGED??
                res = True
        except urllib.error.HTTPError as e:
            exception_type = "urllib.error.HTTPError"
        except requests.exceptions.ConnectionError as e:
            exception_type = "requests.exceptions.ConnectionError"
        except Exception as e:
            exception_type = "Exception"
        finally:
            pass # TODO, don't like the idea of finally changing program exec and exception raise path (use later, maybe)
        
        if res:
            response_str = response.content            
        elif e is not None:
            response_str = "(!) EXCEPTION catched (class_type: {}) in WebNetworking::send_http_get(): ".format(exception_type)
            if response is not None:
                logexc(response_str, e, [", apiurl_with_query: ", apiurl_with_query, ", response content_type:", response.headers['content-type']])
            else:
                logexc(response_str, e, [", apiurl_with_query: ", apiurl_with_query])       
        else:
            response_str = "! error in send_http_get(), res=False, response.status_code={}".format(response.status_code)
            loge(["! error in send_http_get(), res=False, response.status_code="], response.status_code)
            pass #probably http error occured (eg status code != 200)
                
        return res, response_str
    
    # TODO: WARNING! IMPORTANT - Remove following OLD code and refactor other files to use new one
    def HttpRequestWithGET(self, apiurl, querystr=None,  verify_certificate = False):
        # Notes for urllib2: 
        #   GET request with urllib2: If you do not pass the data argument, urllib2 uses a GET request (you can encode the data in URL itself)
        #   POST request with urllib2: Just as easy as GET, simply passing (encoded) request data as an extra parameter
        #params = urllib.urlencode(querystr)
        
        apiurl_with_query = apiurl
        params = querystr
        if params is not None and params != '':
            apiurl_with_query += "?" + params
        #log(["params:", params])
        #log(["apiurl_with_query:", apiurl_with_query, "verify_certificate:", verify_certificate])

        response_data_collection = None
        res = False
        e = None
        exception_type = ""
        try:
            #response = urllib2.urlopen(apiurl_with_query)            
            response = requests.get(apiurl_with_query, verify=verify_certificate) # //TODO: possible security issue! verify=True works from python command line !!!!
            response_data_collection = json.loads(response.content) # response.content is in JSON format (text)
            response.close()
            res = True
        except urllib.error.HTTPError as e:
            exception_type = "urllib2.HTTPError"
        except requests.exceptions.ConnectionError as e:
            exception_type = "requests.exceptions.ConnectionError"
        except Exception as e:
            exception_type = "Exception"
        finally:
            pass # TODO, don't like the idea of finally changing program exec and exception raise path (use later, maybe)
        
        if not res:
            response_data_collection = {"error": {"id":0, "msg":"", "message":""}}            
            response_data_collection["error"]["message"] = exception_type            
            response_data_collection["error"]["msg"] = str(e)
            logexc("(!) EXCEPTION catched (class_type: {}) in HttpRequestWithGET(): ".format(exception_type), 
                    e, 
                    [", apiurl_with_query: ", apiurl_with_query])
                
        return res, response_data_collection
