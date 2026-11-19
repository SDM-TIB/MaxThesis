from rdflib import Graph, BNode, Literal, URIRef, Namespace
from rdflib.namespace import RDFS, PROV, RDF, XSD, OWL
import os
import time
from Util.Classes import Ontology,IncidenceList, TraceGraph, abbreviate, removePrefix, full_uri
from Util.NormalizationUtil import *
from itertools import count
from collections import defaultdict




def embed_triple(triple, abbr, prefix_dict):
    s,p,o = triple
    return f"<<{abbreviate(s, abbr, prefix_dict)} {abbreviate(p, abbr, prefix_dict)} {abbreviate(o, abbr, prefix_dict)}>>"

def debed_triple(triple:str, prefix_dict:dict):
    uris = triple.removeprefix("<<").removesuffix(">>").split(" ")
    return (URIRef(full_uri((uris[0].strip()), prefix_dict)), URIRef(full_uri(uris[1].strip(), prefix_dict)), URIRef(full_uri(uris[2].strip(), prefix_dict)))

def normalize(kg:Graph, on:Ontology, prefix, abbr,prefix_dict,onto_valid, nf1, nf2, nf3, nf4, kg_name, bnode_name=None, negative_triple_dict=None):
    
    # check inputs
    if type(bnode_name) != str:
        ValueError("bnode_name must be a string.")
    if not is_valid_uri_component(bnode_name):
        ValueError("bnode_name must be conform with RFC 3986.")
    if nf4 and negative_triple_dict == None:
        Warning("No negative_triple_dict provided, nothing to be done for NF4.")
    nf1_log = None
    nf2_log = None
    nf3_log = None
    nf4_log = None
    onto_valid_log = 0

    nf1_time = 0
    nf2_time = 0
    nf3_time = 0
    nf4_time = 0

    # setup output directory
    output_dir = f"./Data/Transformed_{kg_name}"
    os.makedirs(output_dir, exist_ok=True)

    # setup common prefixes and extend ontology for normalization-traces
    # TODO maybe populate ontology with common things like rdf:Property a rdfs:Class
    on.addClass("", "NF1-tranformation", "prov:Activity")
    on.addClass("", "NF2-tranformation", "prov:Activity")
    on.addClass("", "NF3-tranformation", "prov:Activity")
    on.addClass("", "NF4-tranformation", "prov:Activity")
    on.addClass("", "Ontology-validation", "prov:Activity")
    for nf in ["NF1-transformation","NF2-transformation","NF3-transformation","NF4-transformation","Ontology-validation"]:
        on.graph.add((URIRef(nf), RDF.type, RDFS.Class))
        on.graph.add((URIRef(nf), RDFS.subClassOf, PROV.Activity))
    trace_graph = TraceGraph()
    trace_graph.add(f"{abbr}:ontology-validation", abbreviate(RDF.type,abbr,prefix_dict), abbreviate(PROV.Activity,abbr,prefix_dict))
    trace_graph.add(f"{abbr}:ontology-validation", abbreviate(RDF.type,abbr,prefix_dict), f"{abbr}:Ontology-validation" )

    ontology_trace_graph = TraceGraph()

    # ontology validation
    if onto_valid:
        for s,p,o in kg:
            if p == RDF.type:
                # treat type statements strictly as metadata, retain in graph
                continue
            if not fits_ontology((s,p,o), on, kg, prefix):
                # remove triple from kg
                kg.remove((s,p,o))

                onto_valid_log += 1

                # trace graph: note that triple was removed
                embedded_triple = embed_triple((s,p,o), abbr, prefix_dict)
                trace_graph.add(embedded_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")
                trace_graph.add(embedded_triple, abbreviate(PROV.wasInvalidatedBy,abbr,prefix_dict), f"{abbr}:ontology-validation")
    # TODO handle whitespaces in string objects during predicate object transformations
    if nf1:
        nf1_start = time.time()
        nf1_log = normalize_nf1(kg, trace_graph, prefix, abbr, prefix_dict, bnode_name)
        nf1_time = time.time() - nf1_start
        
        output_file = f"{output_dir}/1NF-{kg_name}.ttl"
        print(f"Saving 1NF-KG to {output_file}...")
        kg.serialize(destination=output_file, format='turtle')
    if nf2:
        nf2_start = time.time()
        nf2_log = normalize_nf2(kg, trace_graph, ontology_trace_graph, prefix, abbr, prefix_dict, on)
        nf2_time = time.time() - nf2_start
        
        output_file = f"{output_dir}/2NF-{kg_name}.ttl"
        print(f"Saving 2NF-KG to {output_file}...")
        kg.serialize(destination=output_file, format='turtle')
        on_output_file = f"{output_dir}/2NF-{kg_name}Ontology.ttl"
        print(f"Saving normalized ontology for 2NF-KG to {on_output_file}...")
        on.graph.serialize(destination=on_output_file, format="turtle")
    if nf3:
        nf3_start = time.time()
        nf3_log = normalize_nf3(kg, trace_graph, ontology_trace_graph, prefix, abbr, prefix_dict, on)
        nf3_time = time.time() - nf3_start

        
        output_file = f"{output_dir}/3NF-{kg_name}.ttl"
        print(f"Saving 3NF-KG to {output_file}...")
        kg.serialize(destination=output_file, format='turtle')
        on_output_file = f"{output_dir}/3NF-{kg_name}Ontology.ttl"
        print(f"Saving normalized ontology for 3NF-KG to {on_output_file}...")
        on.graph.serialize(destination=on_output_file, format="turtle")
    if nf4:
        nf4_start = time.time()
        nf4_log = normalize_nf4(kg, trace_graph, ontology_trace_graph, prefix, abbr, prefix_dict, negative_triple_dict, on)
        nf4_time = time.time() - nf4_start
        
        output_file = f"{output_dir}/4NF-{kg_name}.ttl"
        print(f"Saving 4NF-KG to {output_file}...")
        kg.serialize(destination=output_file, format='turtle')
        on_output_file = f"{output_dir}/4NF-{kg_name}Ontology.ttl"
        print(f"Saving ontology for 4NF-KG to {on_output_file}...")
        on.graph.serialize(destination=on_output_file, format="turtle")

    
    # write traces
    trace_file = f"{output_dir}/Traces_{kg_name}.ttl"
    on_trace_file = f"{output_dir}/Traces_{kg_name}Ontology.ttl"

    print(f"Saving normalization-traces to {trace_file}...")
    trace_graph.ttl(trace_file, prefix_dict, abbr)

    print(f"Saving ontology-traces to {on_trace_file}...")
    ontology_trace_graph.ttl(on_trace_file, prefix_dict, abbr)

    return onto_valid_log, nf1_log, nf2_log, nf3_log, nf4_log, nf1_time, nf2_time, nf3_time, nf4_time
"""
normalizes a given KG into 1NF-KG according to the definition presented in https://doi.org/10.1016/j.knosys.2025.113939 .
renames blank nodes into unique entities, preferably by leveraging an existing label or the blank node's type(s).
"""
def normalize_nf1(kg:Graph, trace_graph:TraceGraph, prefix:Namespace, abbr, prefix_dict, bnode_name):

    def handle_bnode(b, kg:Graph, trace_graph:TraceGraph, prefix:Namespace, abbr, prefix_dict, bnode_name):
        triples_to_remove = []
        # if node has rdfs:label, use this as name
        labels = []
        for label in kg.objects(b, URIRef("http://www.w3.org/2000/01/rdf-schema#label")):
            # information from label is transferred to node-name, deleting triple
            kg.remove((b, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), label))

            new_name = label.replace(" ","_")
            labels.append(new_name)
            embedded_old_triple = embed_triple((b, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), label),abbr,prefix_dict)
            trace_graph.add(embedded_old_triple, abbreviate(PROV.wasInvalidatedBy,abbr,prefix_dict), f"{abbr}:nf1-transformation")
            trace_graph.add(embedded_old_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")

        combined_labels = "_".join(str(l) for l in labels)
        # elif node has a type, call it <type><# of type>
        if not combined_labels:
            types = []
            for t in kg.objects(b, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")):
                types.append(t)
            types.sort()
            combined_labels = "_".join(removePrefix(str(t), str(prefix)) for t in types)
            if combined_labels:
                if combined_labels not in type_counters.keys():
                    type_counters[combined_labels] = count(1)
                combined_labels = combined_labels + str(next(type_counters.get(combined_labels)))

        # elif just change prefix from _ to namespace-prefix.
        # possibility: try to derive type by the bnodes connecting properties.
        if not combined_labels:
            combined_labels = bnode_name + str(next(counter_bnode)) if bnode_name else str(b)
            


        # for all: find and remove all triples with bnode, add triples with new name
        triples_to_remove = set(kg.triples((b, None, None)))
        triples_to_remove.update(kg.triples((None, None, b)))

        for s, p, o in triples_to_remove:
            kg.remove((s, p, o))

            # s is a blank node, therefore no prefix abbreviation
            embedded_old_triple = embed_triple((s,p,o),abbr,prefix_dict)
            trace_graph.add(embedded_old_triple, abbreviate(PROV.wasInvalidatedBy,abbr,prefix_dict), f"{abbr}:nf1-transformation")
            trace_graph.add(embedded_old_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")


            new_s = URIRef(f"{prefix}{combined_labels}") if s == b else s
            new_o = URIRef(f"{prefix}{combined_labels}") if o == b else o
            kg.add((new_s, p, new_o))

            embedded_new_triple = embed_triple((new_s,p,new_o),abbr,prefix_dict)
            trace_graph.add(embedded_new_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")
            trace_graph.add(embedded_new_triple, abbreviate(PROV.wasDerivedFrom,abbr,prefix_dict), embedded_old_triple)
            trace_graph.add(embedded_new_triple, abbreviate(PROV.wasGeneratedBy,abbr,prefix_dict), f"{abbr}:nf1-transformation")

    type_counters = {}
    counter_bnode = count(1)

    trace_graph.add(f"{abbr}:nf1-transformation", abbreviate(RDF.type,abbr,prefix_dict), abbreviate(PROV.Activity, abbr, prefix_dict))
    trace_graph.add(f"{abbr}:nf1-transformation", abbreviate(RDF.type,abbr,prefix_dict), f"{abbr}:NF1-transformation")

    # find all blank nodes and handle them
    handled = set()
    for s, p, o in kg:
        if type(s) == BNode:
            if s not in handled:
                handle_bnode(s, kg, trace_graph, prefix, abbr, prefix_dict, bnode_name)
                handled.add(s)
        if type(o) == BNode and s != o:
            if o not in handled:
                handle_bnode(o, kg, trace_graph, prefix, abbr, prefix_dict, bnode_name)
                handled.add(o)
    return len(handled)

"""
normalizes a given KG into 2NF-KG according to the definition presented in https://doi.org/10.1016/j.knosys.2025.113939 .

Every property with two or more domain/range types is split into most granular versions. 
The ontology and all KG-triples with those properties are updated. 
"""
def normalize_nf2(kg:Graph, trace_graph:TraceGraph,  ontology_trace_graph:TraceGraph, prefix:Namespace, abbr, prefix_dict, on:Ontology):

    def find_new_property(s,o,kg,candidates, prefix):
        # need to keep possibility in mind, that s or o have multiple types --> multiple new properties
        out = []
        types_s =  set(kg.objects(s, RDF.type))
        types_o =  set(kg.objects(o, RDF.type))
        for new_p,d,r in candidates:
            if prefix[d] in types_s and prefix[r] in types_o:
                out.append(new_p)
        return out

    
    nf2_activity = f"{abbr}:nf2-transformation"
    trace_graph.add(nf2_activity, abbreviate(RDF.type,abbr,prefix_dict), abbreviate(PROV.Activity,abbr,prefix_dict))
    trace_graph.add(nf2_activity, abbreviate(RDF.type,abbr,prefix_dict), f"{abbr}:NF2-transformation")


    # TODO: this ignores subtypes of datatypes. possibly add to split those up too, if sensible.


    # 1. identify ambiguous properties

    property_dict = {}

    current_properties = set(on.properties.keys())
    for p in current_properties:
        current_domain = on.properties[p][0]
        current_range = on.properties[p][1]
        sub_domains = set()
        sub_ranges = set()
        for d in  current_domain:
            sub_domains.update(on.get_final_subtypes(d)) 
        for d in  current_range:
            sub_ranges.update(on.get_final_subtypes(d))

        # still 1. and also: 2. create new unambigous versions (adapt/"normalize" ontology?); only rename where needed

        # for all linear combinations  (sub_domain x sub_range), we need a unique property.
        ld = len(sub_domains)
        lr = len(sub_ranges)

        # note: ld and lr are both >= 1
        # if ld = lr = 1 the property is unambiguous, nothing to do
        if ld == 1 and lr > 1:
                property_dict[p] = []
                d = sub_domains.pop()
                for r in sub_ranges:
                    property_dict[p].append((f"{p}_{r}", d,r))
        elif ld > 1 and lr == 1:
                property_dict[p] = []
                r = sub_ranges.pop()
                for d in sub_domains:
                    property_dict[p].append((f"{d}_{p}", d, r))
        elif ld > 1 and lr > 1:
                property_dict[p] = []
                for d in sub_domains:
                    for r in sub_ranges:
                        property_dict[p].append((f"{d}_{p}_{r}", d, r))

    # update ontology, create traces


    # 3. for every ambiguous property, replace by unambiguous version in ontology, create traces
 
    on_triples_to_remove = []
    on_triples_to_add = []
    for prop, new_props in property_dict.items():
        # remove old prop in ontology dicts and graph
        on.removeProperty(prop)
        old_prop = full_uri(prop, prefix_dict, prefix)
        
        for t in on.graph.triples((URIRef(old_prop), None, None)):
            on_triples_to_remove.append(t)
            embedded_old_triple = embed_triple(t, abbr, prefix_dict)
            ontology_trace_graph.add(embedded_old_triple, abbreviate(PROV.wasInvalidatedBy,abbr,prefix_dict), nf2_activity)

            for new_prop_info in new_props:
                new_prop, d, r = new_prop_info
                if t[1] == RDFS.domain:
                    new_triple = (URIRef(full_uri(new_prop, prefix_dict, prefix)), t[1], URIRef(full_uri(d,prefix_dict,prefix)))
                elif t[1] == RDFS.range:
                    new_triple = (URIRef(full_uri(new_prop, prefix_dict, prefix)), t[1], URIRef(full_uri(r,prefix_dict,prefix)))
                else:
                    new_triple = (URIRef(full_uri(new_prop, prefix_dict, prefix)), t[1], t[2])

                on_triples_to_add.append(new_triple)
                embedded_new_triple = embed_triple(new_triple, abbr, prefix_dict) 
                ontology_trace_graph.add(embedded_new_triple, abbreviate(PROV.wasDerivedFrom,abbr,prefix_dict), embedded_old_triple)
                ontology_trace_graph.add(embedded_new_triple, abbreviate(PROV.wasGeneratedBy,abbr,prefix_dict), nf2_activity)

        for t in on.graph.triples((None,None,old_prop)):
            on_triples_to_remove.append(t)
            embedded_old_triple = embed_triple(t, abbr, prefix_dict)
            ontology_trace_graph.add(embedded_old_triple, abbreviate(PROV.wasInvalidatedBy,abbr,prefix_dict), nf2_activity)

            for new_prop_info in new_props:
                new_prop, d, r = new_prop_info
                new_triple = (t[0], t[1], URIRef(full_uri(new_prop, prefix_dict, prefix)))
                on_triples_to_add.append(new_triple)
                embedded_new_triple = embed_triple(new_triple, abbr, prefix_dict) 
                ontology_trace_graph.add(embedded_new_triple, abbreviate(PROV.wasDerivedFrom, abbr, prefix_dict), embedded_old_triple)
                ontology_trace_graph.add(embedded_new_triple, abbreviate(PROV.wasGeneratedBy,abbr,prefix_dict), nf2_activity)

        for new_prop in new_props:
            on.addProperty(str(prefix), new_prop[0], {new_prop[1]}, {new_prop[2]})

    for t in on_triples_to_remove:
        on.graph.remove(t)

    for t in on_triples_to_add:
        on.graph.add(t)


    # 4. for every ambiguous property instance, replace by unambiguous version in KG, create traces
    triple_dict = {}
    for s, p, o in kg:
        p_name = removePrefix(p, str(prefix))
        if p_name not in property_dict:
            continue
        triple_dict[(s,p,o)] = find_new_property(s,o,kg,property_dict[p_name], prefix)
    
    # remove all keys of triple_dict, add all (s, value, o)
    for t, new_props in triple_dict.items():
        s,p,o = t
        kg.remove(t)
        embedded_old_triple = embed_triple((s,p,o),abbr,prefix_dict)
        trace_graph.add(embedded_old_triple, abbreviate(PROV.wasInvalidatedBy,abbr,prefix_dict), nf2_activity)
        trace_graph.add(embedded_old_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")

        for new_prop in new_props:
            kg.add((s,prefix[new_prop],o))
            embedded_new_triple = embed_triple((s,new_prop,o),abbr,prefix_dict)
            trace_graph.add(embedded_new_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")
            trace_graph.add(embedded_new_triple, abbreviate(PROV.wasDerivedFrom,abbr,prefix_dict), embedded_old_triple)
            trace_graph.add(embedded_new_triple, abbreviate(PROV.wasGeneratedBy,abbr,prefix_dict), nf2_activity)

    return len(triple_dict)
"""
normalizes a given KG into 3NF-KG according to the definition presented in https://doi.org/10.1016/j.knosys.2025.113939 .
"""
def normalize_nf3(kg:Graph, trace_graph:TraceGraph,  ontology_trace_graph:TraceGraph, prefix:Namespace, abbr, prefix_dict, on:Ontology=None):
    #    note: nf3 is always nf 2, so it is possible to skip nf2-function and facilitate nf2 
    #    using this function if we do not want to rely on an ontology
    #    downside: no traces of nf 2 violations


    trace_graph.add(f"{abbr}:nf3-transformation", abbreviate(RDF.type,abbr,prefix_dict), abbreviate(PROV.Activity,abbr,prefix_dict))
    trace_graph.add(f"{abbr}:nf3-transformation", abbreviate(RDF.type,abbr,prefix_dict), f"{abbr}:NF3-transformation")

    # setup
    sp_count = defaultdict(int)
    po_count = defaultdict(int)
    
    # 1. count appearances of same s,p or p,o
    for s, p, o in kg:
        if p == RDF.type:
            continue
        sp_count[(s, p)] += 1
        po_count[(p, o)] += 1

    # 2. count instances of s,p and p,o
    s_p_to_rename = set()
    p_o_to_rename = set()
    for (s, p), count in sp_count.items():
        if count > 1:
            s_p_to_rename.add((s,p))
    for (p, o), count in po_count.items():
        if count > 1:
            p_o_to_rename.add((p,o))
    
    # 3. rename and trace
    triples_to_add = []
    triples_to_remove = []

    def nf3_rename_and_trace(s,p,o,new_p):
        new_triple = (s,prefix[new_p],o)
        embedded_new_triple = embed_triple((s,new_p,o),abbr,prefix_dict)
        old_triple = (s, p, o)
        triples_to_remove.append(old_triple)
        triples_to_add.append(new_triple)
        embedded_old_triple = embed_triple((s,p,o),abbr,prefix_dict)

        trace_graph.add(embedded_old_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")
        trace_graph.add(embedded_old_triple, abbreviate(PROV.wasInvalidatedBy,abbr,prefix_dict), f"{abbr}:nf3-transformation")

        trace_graph.add(embedded_new_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")
        trace_graph.add(embedded_new_triple, abbreviate(PROV.wasGeneratedBy,abbr,prefix_dict), f"{abbr}:nf3-transformation")
        trace_graph.add(embedded_new_triple, abbreviate(PROV.wasDerivedFrom,abbr,prefix_dict), embedded_old_triple)

        if on:
            on_triples_to_add = []
            short_p = removePrefix(abbreviate(p,abbr, prefix_dict),f"{abbr}:")
            if short_p == "rdf:type":
                # TODO is correct?
                on.addProperty(str(prefix), new_p, {"rdfs:Class"}, {"rdfs:Class"})
                # TODO add statements for isproperty, domain, range
                on.graph.add()
            else:
                on.addProperty(str(prefix), new_p, on.properties[short_p][0], on.properties[short_p][1])
                for t in on.graph.triples((URIRef(p), None, None)):
                    new_t = (URIRef(full_uri(new_p, prefix_dict, prefix)), t[1],t[2])
                    on_triples_to_add.append(new_t)

                    embedded_old_triple = embed_triple(t,abbr,prefix_dict)
                    embedded_new_triple = embed_triple(new_t,abbr,prefix_dict)
                    ontology_trace_graph.add(embedded_new_triple, abbreviate(PROV.wasGeneratedBy,abbr,prefix_dict), f"{abbr}:nf3-transformation")
                    ontology_trace_graph.add(embedded_new_triple, abbreviate(PROV.wasDerivedFrom,abbr,prefix_dict), embedded_old_triple)

                for t in on.graph.triples((None,None,p)):
                    on_triples_to_add.append((t[0],t[1],URIRef(full_uri(new_p, prefix_dict, prefix))))
            for t in on_triples_to_add:
                on.graph.add(t)


    for s, p, o in kg:
        if  (s,p) in s_p_to_rename:
            stripped_p = abbreviate(p, abbr, prefix_dict).split(":")[1]
            stripped_o = abbreviate(o, abbr, prefix_dict).split(":")[1].replace(" ", "_")
            if  (p,o) in p_o_to_rename:
                stripped_s = abbreviate(s, abbr, prefix_dict).split(":")[1]
                new_p = f"{stripped_s}_{stripped_p}_{stripped_o}"
            else:
                new_p = f"{stripped_p}_{stripped_o}"
            nf3_rename_and_trace(s,p,o,new_p)
        elif  (p,o) in p_o_to_rename:
            stripped_s = abbreviate(s, abbr, prefix_dict).split(":")[1]
            stripped_p = abbreviate(p, abbr, prefix_dict).split(":")[1]
            new_p = f"{stripped_s}_{stripped_p}"
            nf3_rename_and_trace(s,p,o,new_p)

    # 4. update KG
    for triple in triples_to_remove:
        kg.remove(triple)

    for triple in triples_to_add:
        kg.add(triple)

    return len(triples_to_remove)
"""
normalizes a given KG into 4NF-KG according to the definition presented in https://doi.org/10.1016/j.knosys.2025.113939 .
"""
def normalize_nf4(kg:Graph, trace_graph:TraceGraph,  ontology_trace_graph:TraceGraph, prefix:Namespace, abbr, prefix_dict, negative_triple_dict, on:Ontology=None):
    """finds version of a triple from the original KG at current normalization state of KG."""
    def update_triple(triple, kg:Graph, trace_graph:TraceGraph, prefix_dict):
        # check if triple still up to date
        if triple in kg:
            return {triple}
        
        # triple has been invalidated by NF 1-3

        # note: this is somewhat unsophisticated
        # we know that after nf3 a triple will be changed at most three times, so we are following traces for 3 levels
        out = set()
        start_embedded_triple = embed_triple(triple,abbr,prefix_dict)
        lvl1_embedded_triples = set()

        for s,o in trace_graph.edges[abbreviate(PROV.wasDerivedFrom,abbr,prefix_dict)]:
            if o == start_embedded_triple:
                lvl1_embedded_triples.add(s)


        if not lvl1_embedded_triples:
            # triple is gone and has no successors
            return None
        
        for current_t in lvl1_embedded_triples:
            cur = debed_triple(current_t, prefix_dict)
            if cur in kg:
                # current_t exists, therefore no successors
                out.add((cur))
                continue
            # check for successors
            lvl2_embedded_triples = set()

            for s,o in trace_graph.edges[abbreviate(PROV.wasDerivedFrom,abbr,prefix_dict)]:
                if o == current_t:
                    lvl2_embedded_triples.add(s)

            for current_t in lvl2_embedded_triples:
                cur = debed_triple(current_t, prefix_dict)
                if cur in kg:
                    out.add(cur)
                    continue

                for s,o in trace_graph.edges[abbreviate(PROV.wasDerivedFrom,abbr,prefix_dict)]:
                    if o == current_t:
                        # reached last lvl, everything here has to bwe in kg: if is for safety but should be redundant
                        ds = debed_triple(s, prefix_dict)
                        if ds in kg:
                            out.add(ds)
        return out
                
    triples_to_negate = None
    for constraint in negative_triple_dict.keys():
        # go through all constraint-shapes
        activity = abbreviate(prefix[f"nf4-transformation-{removePrefix(constraint, prefix).removeprefix("shapes/")}"],abbr,prefix_dict)
        trace_graph.add(activity, abbreviate(RDF.type,abbr,prefix_dict), abbreviate(PROV.Activity,abbr,prefix_dict))
        trace_graph.add(activity, abbreviate(RDF.type,abbr,prefix_dict), abbreviate(prefix["NF4-transformation"],abbr,prefix_dict))
        for triple in negative_triple_dict[constraint]:
            triples_to_negate = update_triple(triple,kg,trace_graph, prefix_dict)
            if triples_to_negate:
                for t in triples_to_negate:
                    embedded_old_triple = embed_triple(t, abbr, prefix_dict)
                    p_name, p_prefix = remove_prefix_with_dict(t[1], prefix_dict)
                    o_name, o_prefix = remove_prefix_with_dict(t[2], prefix_dict)
                    new_triple = (t[0],URIRef(f"{p_prefix}NO_{p_name}"),URIRef(f"{o_prefix}NO_{o_name}"))
                    kg.remove(t)
                    kg.add(new_triple)
                    embedded_new_triple = embed_triple(new_triple, abbr, prefix_dict)
                    trace_graph.add(embedded_old_triple, abbreviate(PROV.wasInvalidatedBy,abbr,prefix_dict), activity)
                    trace_graph.add(embedded_old_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")
                    trace_graph.add(embedded_new_triple, abbreviate(RDF.type,abbr,prefix_dict), "rdf-star:triple")
                    trace_graph.add(embedded_new_triple, abbreviate(PROV.wasGeneratedBy,abbr,prefix_dict), activity)
                    trace_graph.add(embedded_new_triple, abbreviate(PROV.wasDerivedFrom,abbr,prefix_dict), embedded_old_triple)

    return len(triples_to_negate) if triples_to_negate else 0