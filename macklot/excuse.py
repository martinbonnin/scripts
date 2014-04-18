import requests
from lxml import etree
import pdb;

def get():
    try:
        r = requests.get('http://programmingexcuses.com/')
        parser = etree.HTMLParser()
        tree   = etree.fromstring(r.text, parser);
        #pdb.set_trace();
        return tree.findall(".//a")[0].text
    except Exception as e:
        return "I don't always give excuses but when I do, it's because of a " + str(e) + " exception";
    
