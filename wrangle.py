# -*- coding: utf-8 -*-
"""
Created on Wed Aug 16 17:26:14 2017

@author: Mamadou DIALLO
"""

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
from collections import defaultdict
import cerberus
import schema

SCHEMA = schema.Schema

OSM_PATH = "Nanterre.osm"
SAMPLE_PATH = "SampleNanterre.osm"
NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

# Make sure the fields order in the csvs matches 
# the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

# Pattern 1: lower case
LOWER = re.compile(r'^([a-z]|_)*$')
# Pattern 2: Lower case with colon
LOWER_COLON = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
# Pattern 3: Special caracters
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
# Pattern 4: Get last word 
street_type_re = re.compile(r'\S+\.?$', re.IGNORECASE)
# Patter 5: first word of a sentence
STREET_TYPE2_RE = re.compile(r'^\S+',re.IGNORECASE)
street_types = defaultdict(int)

# Pattern 7: phone number
phonenumber_re = re.compile(r'^((\+)33|0)(.*)[1-9](.*)(\d{2}(.*)){4}$')

# Expected street types: It is not comprehensive list: to be completed
expected = [u'Aire', u'Allée', u'Avenue',u'Boulevard', u'Chemin', u'Cours', \
            u'Esplanade',u'Ile',u'Impasse',u'Jardins',u'Passage',u'Place',\
            u'Quai',u'Résidence', u'Route', u'Rue',u'Square', u'Terrasse']

# UPDATE THIS VARIABLE: Mapping streets types
mapping = { u'allée': u'Allée',
           u'avenue': u'Avenue',
           u'boulevard':u'Boulevard',
           u'cours':u'Cours',
           u'place':u'Place',
           u'Pl':u'Place',
           u'quai':u'Quai',
           u'rue': u'Rue',
           u'RUE': u'Rue',
           u'Residence':u'Résidence',
           u'terrasse':u'Terrasse'}

# expected house number complement
expected_housenb = ['bis','ter','quater']

# mapping of house number complement
bis_ter_quater = {
  'B' : "bis",
  'T' : "ter",
  'Q' : "quater",
  "Bis" : "bis",
  "BIS" : "bis",
  "Ter" : "ter",
  "TER" : "ter",
  "quat": "quater",
  "Quat": "quater",
  "QUAT": "quater",
  "Quater" : "quater",
  "QUATER" : "quater"
}

# house numbers complement
housenumber_re = re.compile(r'([0-9]+)(\s*)([A-Za-z]*)', re.IGNORECASE)
house_numbers = defaultdict(int)


###
# OBJECTIVE: Parse first Elements of the file
##                      
def parse_firtElements(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    count = 0
    print "root:"
    print root.tag, root.attrib

    for child in root:
        print count, ":",child.tag, child.attrib
        if count == 10:
            break
        count +=1

###
# OBJECTIVE: 
# iterative parsing to process the map file and
# find out not only what tags are there, but also how many, to get the
# feeling on how much of which data you can expect to have in the map.
###
def count_tags(filename):
        # The Dictionary of the tag list in input file.
        # Initialisation
        tagsList = {}
        # scan input file
        with open(filename, "r") as f:
            # for each line
            for line in f:
                try:
                    val = line.split()[0]
                    # we do not consider the header
                    if line.startswith("<?xml"):
                        continue
                    # we do not consider the closing tag
                    elif val.startswith('</'):
                        continue
                    # get the tag
                    elif val.startswith('<'):
                        # get the tag name
                        tg = val.split('<')[1]
                        # count tag name if it already exits
                        if tg in tagsList:
                            tagsList[tg] += 1
                        # create the tag name when met the first time
                        # count set to 1
                        else:
                            tagsList[tg] = 1

                except ValueError:
                    continue

        return tagsList


###
# OBJECTIVE: is it a street type?
#    
def is_street_name(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == "addr:street")

###
# OBJECTIVE: is it house number?
###
def is_house_number(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == "addr:housenumber")

###
# OBJECTIVE: audit house number type for a given element
###
def audit_house_number_type(house_numbers, house_number): 
     # multiple housenumber are separated by coma... need to check each individuals one against  
     # the housenumber regular expression.
     num_match = housenumber_re.search(house_number)
     if num_match: 
         wd = num_match.group(3)
         if wd not in expected_housenb:
             house_numbers[wd].add(wd)
 
       
###
# OBJECTIVE: audit house number type for each element
###
def audit_house_number(filename):
    # multiple housenumber are separated by coma... need to check each individuals one against 
    # the housenumber regular expression. As Appt keyword could be followed by a list numbers separated by a coma
    # a first check for any housenumber starting with Appt will done before the other split and check
    house_numbers = defaultdict(set)
    for event, elem in ET.iterparse(filename, events=("start",)):
            if elem.tag == "node" or elem.tag == "way":
                  for tag in elem.iter("tag"):
                      if is_house_number(tag):
                          audit_house_number_type(house_numbers, tag.attrib['v'])
    
    return house_numbers


###
# OBJECTIVE: update the value of house number
###
def update_housenb(nb, mapping):
    m = housenumber_re.search(nb)
    if m:
        complement = m.group(3)
        if complement in mapping:
            n = m.group(1)
            #print n+' '+mapping[complement]
            return n+' '+mapping[complement]
        else:
            return nb

    else:
        return nb

   
###
# OBJECTIVE: is it a phone number?
#    
def is_phone(elem):
    return (elem.tag == "tag") and \
            ((elem.attrib['k'] == "phone") or \
             (elem.attrib['k'] == "contact:phone") or \
             (elem.attrib['k'] == "contact:mobile"))

###
# OBJECTIVE: update the value of street
###
def update_name(name, mapping):

    # YOUR CODE HERE
    m = STREET_TYPE2_RE.search(name)
    if m:
        str = m.group()
        if str in mapping:
            t = STREET_TYPE2_RE.split(name)
            return mapping[str]+t[-1]
        else:
            return name

    else:
        m = name
        return m


###
# OBJECTIVE: audit street types for a given element
###        
def audit_street_type(street_types, street_name):
    m = STREET_TYPE2_RE.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)
            #street_types[street_type] += 1


###
# OBJECTIVE: audit street types for each element
###        
def auditStreetType(filename):
    osm_file = open(filename, "r")
    street_types = defaultdict(set)
    #for event, elem in ET.iterparse(osm_file):
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])

    osm_file.close()
    return street_types

###
#OBJECTIVE: audit phone numbers
###        
def audit_phone(filename):
      phone_len = defaultdict(list)

      for event, elem in ET.iterparse(filename, events=("start",)):
            if elem.tag == "node" or elem.tag == "way":
                  for tag in elem.iter("tag"):
                        key = tag.attrib['k']
                        if key == 'phone':
                              phone_num = re.sub(r'[\+\(\)\-\s]', '', tag.attrib['v'])
                              phone_len[len(phone_num)].append(tag.attrib['v'])

      return phone_len


###
# OBJECTIVE: update phone numbers
### 
def update_phone(phone_num):
    import string
    whitelist = string.letters + string.digits + ' ' + '+'+';'
    new_s = ''
    for char in phone_num:
        if char == ' ':
            new_s += ''
        elif char in whitelist:
            new_s += char
        else:
            new_s += ''
    new_s = new_s.strip()
    if new_s[:4]=='0033':
        new_s = '+33'+new_s[4:]
    elif new_s[:1]=='0':
        new_s = '+33'+new_s[1:]
      
    # change format for readability
    if len(new_s) == 4:
        # special phone numbers
        phone_num_parts = []
        phone_num_parts.append(new_s)
        return ''.join(phone_num_parts) 
    else:
        # regular phone numbers
        phone_num_parts = []
        phone_num_parts.append(new_s[:3])
        phone_num_parts.append(' ')
        phone_num_parts.append(new_s[3:4])
        phone_num_parts.append(' ')
        phone_num_parts.append(new_s[4:6])
        phone_num_parts.append(' ')
        phone_num_parts.append(new_s[6:8])
        phone_num_parts.append(' ')
        phone_num_parts.append(new_s[8:10])
        phone_num_parts.append(' ')
        phone_num_parts.append(new_s[10:12])
        return ''.join(phone_num_parts)   
        
###
# PURPOSE: count of empty values, leading or trailing space 
###
def empty_value(element, keys):
    # catch tags
    if element.tag == "tag":
        # get value
        str = element.get('v')
        if len(str.strip()) == 0:
            keys['empty'] += 1
        elif len(str.strip()) != len(str):
            keys['leading_trailing'] += 1
        else:
            keys['not_empty'] += 1
            
    return keys

###
# PURPOSE: is it empty value, leading or trailing space
#    
def is_empty(elem):
    str = elem.get('v')
    if len(str.strip()) == 0:
        # if empty
        ret = 2
    elif len(str.strip()) != len(str):
        # if leading or trailing space
        ret = 1
    else:
        # no issue
        ret= 0

    return ret
    
    
###
# PURPOSE: audit empty values, leading or trailing space  
###
def auditEmptyValues(filename):
    keys = {"empty": 0,"not_empty":0,"leading_trailing":0}
    for _, element in ET.iterparse(filename):
        keys = empty_value(element, keys)

    return keys

  
###
# PURPOSE  
###
def shape_element(element, node_attr_fields=NODE_FIELDS, \
                  way_attr_fields=WAY_FIELDS,\
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    # YOUR CODE HERE
    count = 0
    data = {}
    dt = {}
    if element.tag == 'node':
        node_attribs['id'] = element.attrib['id']
        node_attribs['lat'] = element.attrib['lat']
        node_attribs['lon'] = element.attrib['lon']
        node_attribs['user'] = element.attrib['user']
        node_attribs['uid'] = element.attrib['uid']
        node_attribs['version'] = element.attrib['version']
        node_attribs['changeset'] = element.attrib['changeset']
        node_attribs['timestamp'] = element.attrib['timestamp']
        #print "node_attribs:"
        #pprint.pprint(node_attribs)
        
        for sub in element:
            if sub.tag == 'tag':
                data = {
                    "id": None,
                    "key": None,
                    "value": None,
                    "type": None
                }                
                data["id"] = node_attribs['id']
                data["value"] = sub.attrib['v']
                str = sub.attrib['k']
                ret = is_empty(sub)
                if ret == 1:
                    #Correct leading or trailing space in value for element
                    data["value"] = data["value"].strip()                    
                elif ret == 2:
                    # empty tag to be skipped
                    continue                                    
                if is_street_name(sub):
                    #name = data["value"].upper()
                    name = data["value"]
                    better_name = update_name(name,mapping)
                    data["value"] = better_name
                elif is_house_number(sub):
                    nb = data["value"]
                    lst = filter(None, re.split("[,;\-]+", nb))
                    s = []
                    for item in lst:
                        s.append(update_housenb(item, bis_ter_quater))
                    better_nb = ';'.join(s)
                    data["value"] = better_nb
                elif is_phone(sub):
                    phone = data["value"]
                    lst = phone.split(';')
                    s = []
                    for item in lst:
                        s.append(update_phone(item))
                    ph = ';'.join(s)
                    data["value"] = ph
                        
                        
                if re.search(PROBLEMCHARS, str) != None:
                    print "PROBLEMS node_attribs:"
                    pprint.pprint(node_attribs)
                    continue
                elif re.search(LOWER_COLON, str) != None:
                    data["type"] = str.split(":")[0]
                    data["key"] = ":".join(str.split(":")[1:])
                else:
                    data["type"] = "regular"
                    data["key"] = str

                tags.append(data)  

        #print "tags:"
        #pprint.pprint(tags)        

        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        way_attribs['id'] = element.attrib['id']
        way_attribs['user'] = element.attrib['user']
        way_attribs['uid'] = element.attrib['uid']
        way_attribs['version'] = element.attrib['version']
        way_attribs['changeset'] = element.attrib['changeset']
        way_attribs['timestamp'] = element.attrib['timestamp']
        #print "way_attribs:"
        #pprint.pprint(way_attribs)

        for sub in element:
            if sub.tag == 'nd':
                dt = {
                    "id": None,
                    "node_id": None,
                    "position": []
                }                
                dt["id"] = way_attribs['id']
                dt["node_id"] = sub.attrib['ref']
                dt["position"] = count
                count +=1
                way_nodes.append(dt) 
            
            if sub.tag == 'tag':
                data = {
                    "id": None,
                    "key": None,
                    "value": None,
                    "type": None
                }                
                data["id"] = way_attribs['id']
                data["value"] = sub.attrib['v']
                str = sub.attrib['k']
                ret = is_empty(sub)
                if ret == 1:
                    #print "Correct leading or trailing space in value for element:"
                    data["value"] = data["value"].strip()                    
                elif ret == 2:
                    # empty tag to be skipped
                    continue                                    
                if is_street_name(sub):
                    #name = data["value"].upper()
                    name = data["value"]
                    better_name = update_name(name,mapping)
                    data["value"] = better_name
                elif is_house_number(sub):
                    nb = data["value"]
                    lst = filter(None, re.split("[,;\-]+", nb))
                    s = []
                    for item in lst:
                        s.append(update_housenb(item, bis_ter_quater))
                    better_nb = ';'.join(s)
                    data["value"] = better_nb
                elif is_phone(sub):
                    phone = data["value"]
                    lst = phone.split(';')
                    s = []
                    for item in lst:
                        s.append(update_phone(item))
                    ph = ';'.join(s)
                    data["value"] = ph
                        
                        
                if re.search(PROBLEMCHARS, str) != None:
                    print "PROBLEMS node_attribs:"
                    pprint.pprint(way_attribs)                    
                    continue
                elif re.search(LOWER_COLON, str) != None:
                    data["type"] = str.split(":")[0]
                    data["key"] = ":".join(str.split(":")[1:])
                else:
                    data["type"] = "regular"
                    data["key"] = str

                tags.append(data)  


        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}

# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()

def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))



###
# OBJECTIVE: Extend csv.DictWriter to handle Unicode input
### 
class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

###
# OBJECTIVE: Iteratively process each XML element and write to csv(s)
###             
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    # TIP: use of wb instead of w for avoiding blank line.
    # ISSUE with utf-8 encoding -> ANSI
    with codecs.open(NODES_PATH, mode='wb') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, mode='wb') as nodes_tags_file, \
         codecs.open(WAYS_PATH, mode='wb') as ways_file, \
         codecs.open(WAY_NODES_PATH, mode='wb') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, mode='wb') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])

# ================================================== #
#               Main Function                        #
# ================================================== #
def main():
    print "AUDIT OF EMPTY VALUES/TRAILING AND LEADING SPACE"
    keys = auditEmptyValues(OSM_PATH)
    pprint.pprint(keys)
 
    print "AUDIT HOUSENUMBERS"
    housenb_types = audit_house_number(OSM_PATH)
    pprint.pprint(housenb_types)
    
    print "LOOK AT FIRST ELEMENTS"
    parse_firtElements(OSM_PATH)
    
    print "COUNT TAGS"
    tags = count_tags(OSM_PATH)
    pprint.pprint(tags)
    
    print "AUDIT STREET TYPES"
    st_types = auditStreetType(OSM_PATH)
    pprint.pprint(dict(st_types))
    
    print "AUDIT PHONE NUMBERS"
    phone_ln = audit_phone(OSM_PATH)
    pprint.pprint(dict(phone_ln))

    print "PROCESSING"
    process_map(OSM_PATH, validate=False)
    print "END"

if __name__ == "__main__":
    main()