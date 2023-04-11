
import json
import http.client
import os
import traceback

class MSPileupClient():


    def __init__(self, url):

        self.CERT_FILE = os.getenv('X509_USER_PROXY')
        self.KEY_FILE = os.getenv('X509_USER_PROXY')
        self.url = url

    def getByPileupName(self, pileupName):
        """
        Queries ReqMgr through a HTTP GET method
        in every request manager query
        url: the instance used, i.e. url='cmsweb.cern.ch'
        request: the request suffix url
        retries: number of retries
        """
        endpoint = "/ms-pileup/data/pileup?pileupName="
        headers = {"Accept": "application/json"}

        try:
            conn = http.client.HTTPSConnection(self.url, cert_file=self.CERT_FILE, key_file=self.KEY_FILE)
        except Exception as e:
            print ("Exception while establishing https connection")
            print (str(e))
            return None

        try:

            r1 = conn.request("GET", endpoint + pileupName, headers=headers)
            r2 = conn.getresponse()
            response = json.loads(r2.read())
        except Exception as e:
            print ("Exception while getting response from MSPileup")
            print (str(e))
            return None

        return response

    def createPileupDocument(self, params):
        endpoint = "/ms-pileup/data/pileup"
        headers = {"Accept": "application/json"}

        try:
            conn = http.client.HTTPSConnection(self.url, cert_file=self.CERT_FILE, key_file=self.KEY_FILE)
        except Exception as e:
            print ("Pileup document creation failed: Exception while establishing https connection")
            print (str(e))
            return None

        try:
            conn.request("POST", endpoint, params, headers)
            response = conn.getresponse()
            data = response.read()
            conn.close()
            return data
        except Exception as e:
            print ("Pileup document creation failed: Exception while PUT request")
            print (str(e))
            traceback.print_stack()
            print(repr(traceback.extract_stack()))
            print(repr(traceback.format_stack()))
            return None






