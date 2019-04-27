"""
Welcome to NeuroLake Hydra! This is a simple query template for you to play and develop!
This little piece of code has one job, access a website on the internet and collect data.

You must implement all your code inside the 'query_execution' method. It will receive a dictionary
called 'input_data' containing the input to be used by the query and another dictionary
called 'properties' with some useful tools and information about how we want you to build the Hydra query.

"""
"""
<#@#HydraMetadata#@#>
{"version":"1.0.5",
"requirements":[],
"developer_contact":"raony.alves@neurotech.com.br",
"default_properties":{
    "block_threshold": 0.5,
    "execution_delay": 30,
    "driver_type": "URLLIB",
    "referrer":null,
    "max_retakes": 20,
    "input_delete_threshold": 14,
    "user_agent": [
      "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0"
    ],
    "timeout": 20
  },
"host": "http://www.transparencia.gov.br/api-de-dados/cnep?cnpjSancionado=",
"timeout":"50",
"selenium_usage":"false",
"query_name":"WEB012"}
</#@#HydraMetadata#@#>
"""
""" NeuroLake imports """
import utils.Lake_Utils as Utils
import utils.Lake_Exceptions as Exceptions
import utils.Lake_Enum as Enums

"""You should need at least these imports"""
import json
import time
import sys

"""Loading the metadata from this file into the environment. This is crucial for the correct execution"""
if 'pytest' in sys.modules:
    __query_properties__ = Utils.load_parameters(__file__)

"""Your own imports go down here"""
import requests

def get_target_host():
    return Enums.environ_variables['host']

def save_scraper_data(html_content, input_data):
    """This method is responsible for taking your HTML data and saving it according to our storage standards, we will apply
    some transfromations to ensure no excessive data is saved in our infrastructure"""
    file_timestamp = time.strftime(Enums.Defaults["TIMESTAMP_FORMAT"])
    cleaned_html = Utils.clean_html(html_content)

    Utils.save_data(Enums.SAVE_TARGETS['SCRAPER'],
                    Enums.environ_variables['query_name'],
                    file_timestamp,
                    Utils.generate_filename(list(input_data.values()),
                                            extension='html',
                                            status="SUCCESS",
                                            timestamp=file_timestamp),
                    html_content)
    return cleaned_html

def query_execution(input_data, properties):
    """query_execution method
    :param: input_data: Dictionary containing all the content to be searched in the data sources
    :param: properties: Dictionaty containing execution properties such as TIMEOUT, Proxy configurations, IP configurations etc."""

    # First, you need to retrieve the information from the source we passed to you. You can use the method 'get_target_host()'
    # to do so. Here, that method only accesses an environment variable.
    query_result = {}
    target_host = get_target_host()
    print(target_host)
    target_host += input_data.get("cnpj")
    result = requests.get(target_host)
    my_json = result.content.decode('utf-8').replace("'", '"')
    query_result['result'] = my_json
#    print(query_result)

    return query_result


def request(input_data, properties):
    file_timestamp = time.strftime(Enums.Defaults["TIMESTAMP_FORMAT"])

    print(("My parameters were: "+str(input_data)+" "+str(properties)))
    result = query_execution(input_data, properties)
    query_name = Enums.environ_variables['query_name']
    query_info = {}
    query_info['query_name'] = query_name
    query_info['query_version'] = Enums.QUERY_VERSIONS[query_name]
    query_info['query_input'] = input_data
    query_info['query_date'] = time.strftime(Enums.Defaults['TIMESTAMP_FORMAT'])
    query_info['file_timestamp'] = file_timestamp
    query_info.update(result)
    Utils.save_data(Enums.SAVE_TARGETS['PARSER'],
                    query_info['query_name'],
                    file_timestamp,
                    Utils.generate_filename(list(input_data.values()),
                                            extension='json',
                                            status="SUCCESS",
                                            timestamp=file_timestamp),
                    query_info)
    return result

def test_request():    
    # You can extend the properties from you file metadata
    my_test_properties = Utils.load_parameters(__file__)
    cnpjs = ["19823999000105", "60703923000131"]
    for c in cnpjs:
        result = request({"cnpj":c}, my_test_properties)
    assert type(my_test_properties) == dict
    # assert result["Nome de fantasia"] == "NEUROTECH"

