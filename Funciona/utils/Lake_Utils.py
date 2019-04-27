import time
import string
import random
import urllib.request, urllib.error, urllib.parse
import re #regular expression library
from datetime import datetime
import os
import subprocess
import json
import hashlib
from unicodedata import normalize
import bz2
import base64
import lxml
from lxml.html.clean import Cleaner
from selenium import webdriver

from . import Lake_Exceptions as Exceptions
from . import Lake_Enum as Enums


def random_identifier(size=5):
    """Returns a random string consisting of 'size' letters from a-z and numbers from 0-9"""
    return''.join(random.choice(string.lowercase + ''.join([str(x) for x in range(10)])) for x in range(size))


def extract_rendered_html(driver):
    """Executes a javascript to extract the content within the <html> tag
    And returns a string packed inside an <html> tag"""
    html = driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
    return r'<html>'+html.encode('utf-8')+r'</html>'


def compress_bz2(file_data):
    compressed = bz2.compress(data=file_data)
    return compressed


def save_data(origin, query_name, timestamp, filename, data):
    """If the execution is working with an Execution_ID, we need to append it to the query name
    in order to allow the consolidation to work properly. A consolidator started with an
    execution_id will only consolidate the folders containing the such ID"""
    if timestamp is None:
        timestamp = datetime.now()
    date_time = datetime.strptime(timestamp, Enums.Defaults['TIMESTAMP_FORMAT'])
    filename =  './' + \
               origin + '/' + \
               query_name + '/' + \
               str(date_time.year) + '/' + \
               str(date_time.month) + '/' + \
               str(date_time.day) + '/' + \
               str(date_time.hour) + '/' + \
               filename

    try:
        os.makedirs(os.path.dirname(filename))
    except OSError as error:
        if 'File exists' in str(error) or '[Error 183]' in str(error):
            pass
        else:
            raise error
    finally:
        if isinstance(data, bytes):
            open_mode = "wb"
        else:
            open_mode = "w"
        with open (filename, open_mode) as output_file:
            if type(data) == dict:
                output_file.write(json.dumps(data))
            else:
                output_file.write(data)
        return filename


def generate_filename(record_name=[], ref_date=False, extension="html", status="", timestamp=""):
    """ Input: String destination_path, Dict record_name, String extension(DEFAULT: txt), status(DEFAULT: '')
        Output: String containing the complete path to be written to EFS"""
    sep = Enums.Defaults['VERSION_SEPARATOR']
    record_name = [x for x in record_name]
    file_name = sep.join(record_name)
    file_name = file_name.replace(' ', '_')
    _timestamp = timestamp or time.strftime(Enums.Defaults['TIMESTAMP_FORMAT'])

    # Insercao de DATA_REF no nome antes do timestamp
    if ref_date is True:
        if extension in ['csv', 'pdf', 'ods']:
            if type(record_name) is list:
                for i in record_name:
                    try:
                        int(i)
                    except ValueError:
                        raise ValueError("There is a foreign element in the array")
                if len(record_name) == 2:
                    if len(record_name[0]) in [2, 1]:
                        month = record_name[0]
                        year = record_name[1]
                    else:
                        month = record_name[1]
                        year = record_name[0]
                    date_ref = '01#@#' + month + '#@#' + year
                if len(record_name) == 1:
                    date_ref = '01#@#01#@#' + record_name[0]

            elif type(record_name) is dict:
                date_ref = '01#@#' + record_name['month'] + '#@#' + record_name['year']
        return file_name + sep + status + sep + date_ref + sep + "test" + "." + extension
    else:
        return file_name + sep + status + sep + "test" + '.' + extension


def _get_datetime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


def clean_html(html_text,
            javascript=True,
            scripts=True,
            style=True,
            embedded=True,
            links=True,
            forms=True,
            frames=True,
            comments=True,
            annoying_tags=True,
            meta=True,
            safe_attrs_only=True,
            remove_unknown_tags=True,
            processing_instructions=True
            ):
    """Clean all the javascript and styles from the HTML returning the string with only the html content"""
    # True = Remove | False = Keep
    cleaner = Cleaner()
    cleaner.javascript = javascript  # This is True because we want to activate the javascript filter
    cleaner.scripts = scripts  # This is True because we want to activate the scripts filter
    cleaner.style = style
    cleaner.embedded = embedded
    cleaner.links = links
    cleaner.forms = forms
    cleaner.frames = frames
    cleaner.comments = comments
    cleaner.page_structure = False # Keep page structure
    cleaner.annoying_tags = annoying_tags
    cleaner.meta = meta
    cleaner.safe_attrs_only = safe_attrs_only
    cleaner.remove_unknown_tags = remove_unknown_tags
    cleaner.processing_instructions = processing_instructions
    clean_content = cleaner.clean_html(lxml.html.fromstring(html_text))
    return lxml.html.tostring(clean_content)

def load_parameters(file_name):
    full_path = os.path.realpath(file_name)

    with open(full_path,'r') as query_file:
        hydra_query_trimmed = query_file.read().replace('\n','')
        start_metadata = hydra_query_trimmed.find('<#@#HydraMetadata#@#>')+len('<#@#HydraMetadata#@#>')
        end_metadata = hydra_query_trimmed.find('</#@#HydraMetadata#@#>')

        try:
            hydra_metadata = json.loads(hydra_query_trimmed[start_metadata:end_metadata])
        except ValueError as error:
            raise Exception('Please provide a file with a correct HydraMetaData')
        
        Enums.environ_variables.update(hydra_metadata)

        Enums.QUERY_VERSIONS.update({hydra_metadata['query_name']:hydra_metadata['version']})

        # building input data and properties to pass down to the query
        query_properties = {"timeout":int(Enums.environ_variables['timeout'])}

        if Enums.environ_variables['selenium_usage'] == "true":
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            # if ('chromedriver' in os.listdir('/usr/local/bin')) or ('chromedriver' in os.listdir('/usr/local/bin')):
            #     driver = webdriver.Chrome(options=chrome_options)
            #     query_properties['driver'] = driver
            if os.path.isfile('./chromedriver'):
                driver = webdriver.Chrome(executable_path='./chromedriver',options=chrome_options)
                query_properties['driver'] = driver
            else:
                raise Exception("CHROME DRIVER NOT FOUND: Please download the chromedriver and place it on the hydra root directory")

        return query_properties