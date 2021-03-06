#!/usr/bin/env python3 

import pandas as pd
import ruamel.yaml
from ruamel.yaml import YAML
import glob
import re
from collections import defaultdict
import argparse
import os
from schema_utils import stripper


tosave = set()
noderows = 0
propertyrows = 0
def get_params():
    parser = argparse.ArgumentParser(description="name of directory containing yaml files, and TSV files.")
    parser.add_argument("-y", "--yamls", dest="yamls", required=True, help="Location of the yaml files")
    parser.add_argument("-t", "--tsvs", dest="tsvs", required=True, help="Destination of the tsv files")
    parser.add_argument("-d", "--dictionary", dest="data_dictionary", required=True, help="Name of the data dictionary")

    args = parser.parse_args()
    return args

def makedataframes():
    vrowtemplate = {'<node>': None,
    '<field>': None,
    '<description>': None,
    '<type>': None,
    '<terms>': None,
    '<pattern>': None,
    '<maximum>': None,
    '<minimum>': None,
    '<options1>': None,
    '<options2>': None,
    '<options3>': None,
    '<options4>': None,
    '<options5>': None,
    '<options6>': None,
    '<options7>': None,
    '<options8>': None}
    nrowtemplate = {'<node>': None,
 '<namespace>': None,
  '<title>': None,
  '<nodeTerms>': None,
   '<category>': None,
    '<submittable>': None,
     '<description>': None,
       '<additionalProperties>' : False,
       '<property_ref>': None,
         '<program>': None,
          '<project>': None,
          '<required>': None,
          '<link_name>': None,
           '<backref>': None,
            '<label>': None,
             '<target>': None,
              '<multiplicity>': None,
               '<link_required>': None,
                '<link_group_required>': None,
                 '<group_exclusive>': None}
    return pd.DataFrame(columns=nrowtemplate), pd.DataFrame(columns=vrowtemplate)


def lrefs_to_srefs(refs):
    """Converts a list of references into a string"""
    sref = ''
    for s in refs:
        if isinstance(s, dict):
            sref += s['$ref'] + " ,"
    return sref


def list2string(lis):
    """Converts a list of enums into a string seperated by |"""
    st = ''
    for s in lis:
        st += (s + ' | ')
    return st

def reqlist2string(rlis):
    """Convertes a list into comma separated string"""
    st = ''
    for s in rlis:
        st += (s + ', ')
    return st

def dlist2string(dlis):
    """Converts a list of dictionaries into a string sep by |"""
    st = ''
    for p, v, in dlis:
        s = ''
        s += (p + ' ' + v)
        st += (s + ' | ')
    return st


def enums_chunker(enums):
    """Takes the enums string and breaks it up into chunks of 32000 characters or less so that they can fit in
    the 32000 char limit of an Excel cell"""

    chunks =[]
    while len(enums) > 32000:
        chunk =enums[32000:]
        sep = chunk.index(' | ')
        chunks.append(enums[:32000+sep])
        enums = enums[32000+sep:]
    chunks.append(enums)
    return chunks


def has_subgroup(links):
    for l in links:
        if 'subgroup' in l.keys():
            return True
    return False

def getvarVals(props, frame):
    """Gets the fields and values from the properties portion of the yaml file and addes it to the dataframe. 
    
    Arguments:
        props {[dictionary]} -- [yaml properties]
        frame {[dataframe]} -- [properties dataframe]
    
    Returns:
        [dataframe] -- [The properties (variables) dataframe to be exported as a csv]
    """
    global propertyrows
    rows = []
    global tosave
    propd = defaultdict(lambda: None, props[1])
    for k in propd:
        if isinstance(k, dict):
            propd[k] = defaultdict(lambda: None, propd[k])

    for key in propd.keys():
    #     rows.append({'<node>': props[0],'<field>': key,'<description>': propd[key]['description'],'<type>':  propd[key]['type'],'<options>':  propd[key]['enum'],'<required>':  propd[key]['required'],'<terms>':  propd[key]['terms'], '<pattern>':  propd[key]['pattern'], '<maximum>':  propd[key]['maximum'], '<minimum>':  propd[key]['minimum']})
        if isinstance(key, str) and key == '$ref':
            continue
        row = {'<node>': None,
    '<field>': None,
    '<description>': None,
    '<type>': None,
    '<terms>': None,
     '<pattern>': None,
      '<maximum>': None,
       '<minimum>': None,
           '<options1>': None,
    '<options2>': None,
    '<options3>': None,
    '<options4>': None,
    '<options5>': None,
    '<options6>': None,
    '<options7>': None,
    '<options8>': None,
    }
        row['<node>'] = props[0]
        row['<field>'] = key
        if isinstance(propd[key], dict):
            row['<description>'] = propd[key].get('description')
        
        #For all implementations of enums
        if propd[key].get('enum') or propd[key].get('enumDef') or propd[key].get('enumTerms'):
            row['<type>'] = 'enum'
        else:
            row['<type>'] = propd[key].get('type')
      
        enums = propd[key].get('enum')
        numDef = propd[key].get('enumDef')
        numterms = propd[key].get('enumTerms')

        if enums is not None and numDef is not None:
            tosave.add(f"{args.yamls}" + f"{props[0]}.yaml")
            enumrefs = []
            for e in enums:
                pair = [e, []]
                for dic in numDef:
                    idd = stripper(dic.get('term_id'))
                    ename = e.lower().replace('/s', '_')
                    enumer = dic['enumeration'].lower().replace('/s', '_')
                    if ename == enumer and idd is not None:
                        pair[1].append(f"_terms.yaml#/{idd}")
                
                b = '{'
                for p in pair[1]:
                    b += (p + ', ')
                b += '}'
                pair[1] = b
                
                enumrefs.append(pair)
            
            chunks = enums_chunker(dlist2string(enumrefs))
            for chunk in range(len(chunks)):
                row[f'<options{chunk+1}>'] = stripper(chunks[chunk])
        
        elif enums is not None:
            chunks = enums_chunker(list2string(enums))
            for chunk in range(len(chunks)):
                row[f'<options{chunk+1}>'] = stripper(chunks[chunk])
             
 
        elif numterms is not None:
            enums = []
            for k, v in numterms.items():
                enum = k + ' ' + '{'
                if isinstance(v, list):
                    for ref in v:
                        r = (ref['$ref'] + ', ')
                        enum += r
                enum += '}'
                enums.append(enum)
            chunks = enums_chunker(list2string(enums))
            for chunk in range(len(chunks)):
                row[f'<options{chunk+1}>'] = stripper(chunks[chunk])

        t = propd[key].get('term')
        tdef = propd[key].get('termDef')
        trefs = propd[key].get('terms')
        rerefs = propd[key].get('$ref')
        if isinstance(t, dict):
            row['<terms>'] = t.get('$ref')
        elif isinstance(t, str):
            row['<terms>'] = stripper(t)
        elif tdef is not None:
            tosave.add(f"{args.yamls}" + f"{props[0]}.yaml")
            refs = []
            for n in tdef:
                try:
                    na = n.get('term_id')
                    if na is not None:
                        refs.append({'$ref': f"_terms.yaml#/{na}"})
                except AttributeError:
                    print(f"termDef {tdef} in property {key} of {props[0]} node should be a list of dictionaries")
            row['<terms>'] = stripper(lrefs_to_srefs(refs))
        elif trefs is not None:
            row['<terms>'] = stripper(lrefs_to_srefs(trefs))
        elif rerefs is not None:
            row['<terms>'] = stripper(rerefs)
       
        row['<maximum>'] = propd[key].get('maximum')
        
        row['<minimum>'] = propd[key].get('minimum')
        
        
        row['<pattern>'] = propd[key].get('pattern')
        
        rows.append(row)
    for r in rows:
        frame = frame.append(r, ignore_index = True)
        propertyrows += 1
    return frame


def get_linknames(dic):
    """Gets the names of links from links block so references can be made in properties list"""
    out = []
    links = dic['links']
    for link in links:
        if type(link) == dict:
            try:
                out.append(link['name'])
            except KeyError:
                for l in link['subgroup']:
                    out.append(l['name'])
    return out

def getrequired(node):
    n = node['id']
    reqs = {n : []}
    exclude = ['submitter_id', 'type', 'file_name', 'file_size', 'md5sum', 'data_format']
    for r in node['required']:
        if r not in exclude:
            reqs[node['id']].append(r)
    return reqs

def getnodevalues(node, frame):
    """Gets the values of the fields in the nodes schema, inputs their values into the row dictionary. Then appends dictionary to the 
    nodes dataframe.
    
    Arguments:
        node {[dictionary]} -- [The yaml file in dictionary form]
        frame {[dataframe]} -- [The dataframe that will be exported as a csv]
    
    Returns:
        [dataframe] -- [Returns a dataframe with the fields and their values from the node part of the yaml file]
    """
    global noderows
    row = {'<node>': node['id'], '<namespace>': node['namespace'], '<title>': node['title'], '<nodeTerms>': None, '<category>': node['category'], '<program>': node['program'], '<project>': node['project'], '<property_ref>': None, '<required>': stripper(reqlist2string(node['required'])), '<submittable>': node['submittable'], '<description>': node['description'],  '<additionalProperties>' : node['additionalProperties'], '<link_name>': None, '<backref>': None, '<label>': None, '<target>': None, '<multiplicity>': None, '<link_required>': None, '<link_group_required>': None, '<group_exclusive>': None}
    names = ''
    backrefs = ''
    labels = ''
    targets = ''
    multis = ''
    lreqs = ''
    
    if has_subgroup(node['links']):
        sname= []
        sbackref= []
        slabel= []
        starget= []
        smulti= []
        sreq = []
        try: 
            #By convention the last element in links list is the subgroup, if it exists
            for l in node['links'][-1]['subgroup']:
                sname.append(l['name'])
                sbackref.append(l['backref'])
                slabel.append(l['label'])
                starget.append(l['target_type'])
                smulti.append(l['multiplicity'])
                sreq.append(l['required'])
            names = names + str(sname)
            backrefs = backrefs + str(sbackref)
            labels = labels + str(slabel)
            targets = targets + str(starget)
            multis = multis + str(smulti)
            lreqs = lreqs + str(sreq)
            row['<group_exclusive>'] = node['links'][-1]['exclusive']
            row['<link_group_required>'] = node['links'][-1]['required']
        except KeyError:
            #If for some reason the subgroup is not the last element it should be the first
            for l in node['links'][0]['subgroup']:
                sname.append(l['name'])
                sbackref.append(l['backref'])
                slabel.append(l['label'])
                starget.append(l['target_type'])
                smulti.append(l['multiplicity'])
                sreq.append(l['required'])
            names = names + str(sname)
            backrefs = backrefs + str(sbackref)
            labels = labels + str(slabel)
            targets = targets + str(starget)
            multis = multis + str(smulti)
            lreqs = lreqs + str(sreq)
            row['<group_exclusive>'] = node['links'][0]['exclusive']
            row['<link_group_required>'] = node['links'][0]['required']
    
    for l in node['links']:
        try:
            names = names + "," + l['name']
            backrefs = backrefs+ "," +l['backref']
            labels = labels+ "," +l['label']
            targets = targets+ "," +l['target_type']
            multis = multis+ "," +l['multiplicity']
            lreqs = lreqs+ "," +str(l['required'])
        except KeyError:
            pass
    row['<link_name>'] = stripper(names)
    row['<backref>'] = stripper(backrefs)
    row['<label>'] = stripper(labels)
    row['<target>'] = stripper(targets)
    row['<multiplicity>'] = stripper(multis)
    row['<link_required>'] = stripper(lreqs)

    propref = node['properties'].get('$ref')
    if propref is not None:
        row['<property_ref>'] = propref
    nterms = node['<nodeTerms>']
    if nterms is not None:
        row['<nodeTerms>'] = lrefs_to_srefs(nterms)
    noderows += 1
    
    return frame.append(row, ignore_index = True)

def yamfilter(yam):
    """Filters out the yamls that will not be exported with the tool"""
    files = ['_settings', '_definitions', '_terms', 'project', 'program']
    for f in files:
        if f in yam:
            return False
    return True

if __name__ == "__main__":

    args = get_params()
        
    files = glob.glob(f'{args.yamls}*')
    yamfiles = [f for f in files if '.yaml' in f]
    
    filteredyams = list(filter(yamfilter, yamfiles))

    yaml= YAML(typ='safe')
    yamdics = []
    for y in filteredyams:
        with open(y) as yam:
            yamdics.append(defaultdict(lambda: None, yaml.load(yam)))
    for d in yamdics:
        linknames = get_linknames(d)
        todel = []

        for k in d['properties']:
            if k in linknames:
                todel.append(k)

        for l in linknames:
            de = d['properties'][l]
            if de is not None:
                del d['properties'][l]
    
    yamprops = [(y['id'], y['properties']) for y in yamdics]
    # for y in yamdics:
    #     del y['properties']
    
    ndf, vdf = makedataframes()

    if not os.path.exists(args.tsvs):
        os.mkdir(args.tsvs)



    #create the nodes tsv
    # required = []
    for dic in yamdics:
        ndf = getnodevalues(dic, ndf)
        # required.append(getrequired(dic))

    # rkeys = [list(k.keys())[0] for k in required]
    ndf.to_csv(f'{args.tsvs}/nodes_{args.data_dictionary}.tsv', sep= '\t', index = False, quoting = None)

    #create the properties tsv
    for dic in yamprops:
        vdf = getvarVals(dic, vdf)

    ##########Obsolete code due to removing required field from variables tsv
    # rows2req = []
    
    # for n in required:
    #     key = list(n.keys())[0]
    #     ns = vdf[vdf['<node>'] == key]
    #     for v in n[key]:
    #         rows2req.append(ns[ns['<field>'] == v].index.values.astype(int))

    # for ar in rows2req:
    #     if len(ar) == 1:
    #         reqrow = vdf.iloc[ar[0]]
    #         reqrow['<required>'] = True
            
    vdf.to_csv(f'{args.tsvs}/variables_{args.data_dictionary}.tsv', sep='\t', index=False, quoting=None)

    for fi in tosave:
        if fi in filteredyams:
            with open(fi) as saveyam:
                syam = saveyam.read()
                
            with open(f"{fi[:-5]}_archive.yaml", 'w') as saver:
                saver.write(syam)
    print(f"Completed with {noderows} nodes {propertyrows} properties added to {args.tsvs}nodes_{args.data_dictionary}.tsv and {args.tsvs}variables_{args.data_dictionary}.tsv")
    
    print(f"{len(tosave)} yaml files archived")     