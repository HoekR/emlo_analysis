# -*- coding: utf-8 -*-
"""
Created on Fri May  5 10:52:57 2017

@author: rikhoekstra
"""
import requests
import os
import re
from unicodecsv import DictWriter
from lxml import etree 

hein = """	ING Book Service 01_158
ING Book Service 02_163
ING Book Service 03_169
ING Book Service 04_177
ING Book Service 05_183
ING Book Service 06_189
ING Book Service 07_194
ING Book Service 08_198
ING Book Service 09_204
ING Book Service 10_207
ING Book Service 11_214
ING Book Service 12_221
ING Book Service 13_224
ING Book Service 14_226
ING Book Service 15_227
ING Book Service 16_240
ING Book Service 17_243
ING Book Service 18_244
ING Book Service 19_247
"""

ah = re.sub('\n\s?ING Book Service ', '\n,', hein)
hein.replace('\tING Book Service ', '')


input = ah.split('\n,')
input = [i.strip() for i in input]


outdir = '/Users/rikhoekstra/Downloads/heinsius_brieven'

baseurl = 'http://resources.huygens.knaw.nl/retroapp/service_heinsius/%s/TableOfContents'

for item in input:
    url = baseurl % item
    doc = requests.get(url)
    fl = doc.content
    outfl = open(os.path.join(outdir, item + '.xml'), 'w')
    outfl.write(fl)
    outfl.close()


def parsefl(items):
    rows = []
    fieldnames = ['n', 
              'page',
              'from',
              'to',
              'd',
              'm',
              'y']
    for i in items:
        row = {}
        ch = i.getchildren()
        for e in ch:
            if e.tag in ['n', 'page']:
                row[e.tag] = e.text
            elif e.tag == 'title':
                for t in e.getchildren():
                    if t.tag == 'date':
                        for d in t.getchildren():
                            row[d.tag] = d.text
                    else:
                        row[t.tag] = t.text
        for k in row.keys():
            if k not in fieldnames:
                del row[k]
        rows.append(row)
    return rows


outrows = []
for fl in os.listdir(outdir):
    if os.path.splitext(fl)[1] == '.xml':
        infl = os.path.join(outdir, fl)
        doc = etree.parse(infl)
        root = doc.getroot()
        items = [item for item in root if item.tag == 'item']    
        result = parsefl(items)
        outrows.extend(result)
    
fieldnames = ['n', 
              'page',
              'from',
              'to',
              'd',
              'm',
              'y']
              
outfl = os.path.join(outdir, 'heinbrieven.csv')

out = open(outfl, 'w')

w = DictWriter(out, fieldnames)
w.writeheader()
w.writerows(outrows)
out.close()