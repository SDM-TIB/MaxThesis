from rdflib import Graph, BNode, Literal, URIRef, Namespace
from rdflib.namespace import RDFS, PROV, RDF, XSD
import os
import time
from Util.Classes import Ontology, IncidenceList, abbreviate, removePrefix
from Util.NormalizationUtil import fits_ontology, is_valid_uri_component
from itertools import count
from collections import defaultdict





# _:b1 <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Band> .
# _:b1 <http://example.org/hasAlbum> <http://example.org/The_Royal_Scam> .
# _:b2 <http://www.w3.org/2000/01/rdf-schema#label> "cool 70s band"^^<http://www.w3.org/2001/XMLSchema#string> .
# _:b2 <http://example.org/collaboratedWith> <http://example.org/Larry_Carlton> .
# <http://example.org/Larry_Carlton> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Solo_Artist> .
# _:b3 <http://example.org/hasAlbum> <http://example.org/Volcanic> .
# <http://example.org/Foreigner> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Artist> .
# <http://example.org/Foreigner> <http://example.org/hasAlbum> <http://example.org/Foreigner-4> .




def embed_triple(triple, abbr, prefix_dict):
    s,p,o = triple
    return f"<<{abbreviate(s, abbr, prefix_dict)}, {abbreviate(p, abbr, prefix_dict)}, {abbreviate(o, abbr, prefix_dict)}>>"

def normalize(kg:Graph, on:Ontology, prefix, abbr, nf1, nf2, nf3, nf4, kg_name, bnode_name=None, negative_triple_dict=None):
    # check inputs
    if type(bnode_name) != str:
        ValueError("bnode_name must be a string.")
    if not is_valid_uri_component(bnode_name):
        ValueError("bnode_name must be conform with RFC 3986.")
    if nf4 and negative_triple_dict == None:
        Warning("No negative_triple_dict provided, nothing to be done for NF4.")


    # setup common prefixes and extend ontology for normalization-traces
    prefix_dict = {str(prefix): abbr, "http://www.w3.org/ns/prov#": "prov", "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf", "http://www.w3.org/ns/rdf-star#": "rdf-star", "http://www.w3.org/2000/01/rdf-schema#": "rdfs"}
    on.addClass("", "NF1-tranformation", "prov:Activity")
    on.addClass("", "NF2-tranformation", "prov:Activity")
    on.addClass("", "NF3-tranformation", "prov:Activity")
    on.addClass("", "NF4-tranformation", "prov:Activity")
    on.addClass("", "Ontology-validation", "prov:Activity")


    trace_graph = IncidenceList()
    trace_graph.add(prefix["ontology-validation"], RDF.type, PROV.Activity)
    trace_graph.add(prefix["ontology-validation"], RDF.type, prefix["Ontology-validation"] )

    ontology_trace_graph = IncidenceList()

    # ontology validation
    for s,p,o in kg:
        if p == RDF.type:
            # treat type statements strictly as metadata, retain in graph
            continue

        if not fits_ontology((s,p,o), on, kg, prefix, prefix_dict=prefix_dict):
            # remove triple from kg
            kg.remove((s,p,o))


            # trace graph: note that triple was removed
            embedded_triple = embed_triple((s,p,o), abbr, prefix_dict)
            trace_graph.add(embedded_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
            trace_graph.add(embedded_triple, PROV.wasInvalidatedBy, prefix['ontology-validation'])


    if nf4:
        # TODO collect faulty triples according to constraints, add to val_results dict
        pass

    if nf1:
        normalize_nf1(kg, trace_graph, prefix, abbr, prefix_dict, bnode_name)
    if nf2:
        normalize_nf2(kg, trace_graph, ontology_trace_graph, prefix, abbr, prefix_dict, on)
    if nf3:
        normalize_nf3(kg, trace_graph, ontology_trace_graph, prefix, abbr, prefix_dict, on)
    if nf4:
        normalize_nf4(kg, trace_graph, ontology_trace_graph, prefix, abbr, prefix_dict, negative_triple_dict, on)


    
    # write normalized graph to nt file, return path
    output_dir = f"./Data/Transformed_{kg_name}"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/Normalized_{kg_name}.nt"
    trace_file = f"{output_dir}/Traces_{kg_name}.nt"
    on_trace_file = f"{output_dir}/Traces_{kg_name}Ontology.nt"
    on_output_file = f"{output_dir}/Normalized_{kg_name}Ontology"
    
    print(f"Saving normalized KG to {output_file}...")
    kg.serialize(destination=output_file, format='nt')

    print(f"Saving normalization-traces to {trace_file}...")
    trace_graph.ttl(trace_file, prefix_dict, "ex")

    print(f"Saving normalized ontology to {on_output_file}...")
    on.ttl(on_output_file, prefix_dict, "ex")

    print(f"Saving ontology-traces to {on_trace_file}...")
    ontology_trace_graph.ttl(on_trace_file, prefix_dict, "ex")

    # TODO output normalized ontology

"""
normalizes a given KG into 1NF-KG according to the definition presented in https://doi.org/10.1016/j.knosys.2025.113939 .
renames blank nodes into unique entities, preferably by leveraging an existing label or the blank node's type(s).
"""
def normalize_nf1(kg:Graph, trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict, bnode_name):

    def handle_bnode(b, kg:Graph, trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict, bnode_name):
        triples_to_remove = []
        # if node has rdfs:label, use this as name
        labels = []
        for label in kg.objects(b, URIRef("http://www.w3.org/2000/01/rdf-schema#label")):
            labels.append(label)

            # information from label is transferred to node-name, deleting triple
            kg.remove((b, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), label))

        new_name = "_".join(str(l) for l in labels)
        new_name = new_name.replace(" ", "_")
        # elif node has a type, call it <type><# of type>
        if not new_name:
            types = []
            for t in kg.objects(b, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")):
                types.append(t)
            types.sort()
            new_name = "_".join(removePrefix(str(t), str(prefix)) for t in types)
            if new_name:
                if new_name not in type_counters.keys():
                    type_counters[new_name] = count(1)
                new_name = new_name + str(next(type_counters.get(new_name)))

        # elif just change prefix from _ to namespace-prefix.
        # possibility: try to derive type by the bnodes connecting properties.
        if not new_name:
            new_name = bnode_name + str(next(counter_bnode)) if bnode_name else str(b)
            


        # for all: find and remove all triples with bnode, add triples with new name
        triples_to_remove = set(kg.triples((b, None, None)))
        triples_to_remove.update(kg.triples((None, None, b)))

        for s, p, o in triples_to_remove:
            kg.remove((s, p, o))

            # s is a blank node, therefore no prefix abbreviation
            embedded_old_triple = embed_triple((s,p,o),abbr,prefix_dict)
            trace_graph.add(embedded_old_triple, PROV.wasInvalidatedBy, prefix["nf1-transformation"])
            trace_graph.add(embedded_old_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")


            new_s = URIRef(f"{prefix}{new_name}") if s == b else s
            new_o = URIRef(f"{prefix}{new_name}") if o == b else o
            kg.add((new_s, p, new_o))

            embedded_new_triple = embed_triple((new_s,p,new_o),abbr,prefix_dict)
            trace_graph.add(embedded_new_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
            trace_graph.add(embedded_new_triple, PROV.wasDerivedFrom, embedded_old_triple)
            trace_graph.add(embedded_new_triple, PROV.wasGeneratedBy, prefix["nf1-transformation"])

    type_counters = {}
    counter_bnode = count(1)

    trace_graph.add(prefix["nf1-transformation"], RDF.type, PROV.Activity)
    trace_graph.add(prefix["nf1-transformation"], RDF.type, prefix["NF1-transformation"])

    # find all blank nodes and handle them
    handled = set()
    for s, p, o in kg:
        if type(s) == BNode:
            s in handled or not handle_bnode(s, kg, trace_graph, prefix, abbr, prefix_dict, bnode_name) and handled.add(s)
        if type(o) == BNode and s != o:
            o in handled or not handle_bnode(o, kg, trace_graph, prefix, abbr, prefix_dict, bnode_name) and handled.add(o)
    


"""
normalizes a given KG into 2NF-KG according to the definition presented in https://doi.org/10.1016/j.knosys.2025.113939 .

Every property with two or more domain/range types is split into most granular versions. 
The ontology and all KG-triples with those properties are updated. 
"""
def normalize_nf2(kg:Graph, trace_graph:IncidenceList,  ontology_trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict, on:Ontology):

    def find_new_property(s,o,kg,candidates, prefix):
        # need to keep possibility in mind, that s or o have multiple types --> multiple new properties
        out = []
        types_s =  set(kg.objects(s, RDF.type))
        types_o =  set(kg.objects(o, RDF.type))
        for new_p,d,r in candidates:
            if prefix[d] in types_s and prefix[r] in types_o:
                out.append(new_p)
        return out

    
    nf2_activity = prefix["nf2-transformation"]
    trace_graph.add(nf2_activity, RDF.type, PROV.Activity)
    trace_graph.add(nf2_activity, RDF.type, prefix["NF2-transformation"])


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
    # TODO maybe change a bit, currently not referencing specific triples from ontology .ttl file, only referencing properties
    for prop, new_props in property_dict.items():
        on.removeProperty(prop)
        old_prop = abbreviate(prop, abbr, prefix_dict)

        ontology_trace_graph.add(old_prop, PROV.wasInvalidatedBy, nf2_activity)
        for new_prop in new_props:
            on.addProperty(str(prefix), new_prop[0], {new_prop[1]}, {new_prop[2]})
            ontology_trace_graph.add(new_prop[0], PROV.wasDerivedFrom, old_prop)
            ontology_trace_graph.add(new_prop[0], PROV.wasGeneratedBy, nf2_activity)

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
        trace_graph.add(embedded_old_triple, PROV.wasInvalidatedBy, nf2_activity)
        trace_graph.add(embedded_old_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")

        for new_prop in new_props:
            kg.add((s,prefix[new_prop],o))
            embedded_new_triple = embed_triple((s,new_prop,o),abbr,prefix_dict)
            trace_graph.add(embedded_new_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
            trace_graph.add(embedded_new_triple, PROV.wasDerivedFrom, embedded_old_triple)
            trace_graph.add(embedded_new_triple, PROV.wasGeneratedBy, nf2_activity)


"""
normalizes a given KG into 3NF-KG according to the definition presented in https://doi.org/10.1016/j.knosys.2025.113939 .
"""
def normalize_nf3(kg:Graph, trace_graph:IncidenceList,  ontology_trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict, on:Ontology=None):
    # note: nf3 is always nf 2, so it is possible to skip nf2-function and facilitate nf2 
    # using this function if we do not want to rely on an ontology
    # downside: no traces of nf 2 violations


    trace_graph.add(prefix["nf3-transformation"], RDF.type, PROV.Activity)
    trace_graph.add(prefix["nf3-transformation"], RDF.type, prefix["NF3-transformation"])

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

        trace_graph.add(embedded_old_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
        trace_graph.add(embedded_old_triple, PROV.wasInvalidatedBy, prefix["nf3-transformation"])

        trace_graph.add(embedded_new_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
        trace_graph.add(embedded_new_triple, PROV.wasGeneratedBy, prefix["nf3-transformation"])
        trace_graph.add(embedded_new_triple, PROV.wasDerivedFrom, embedded_old_triple)

        if on:
            short_p = removePrefix(abbreviate(p,abbr, prefix_dict),f"{abbr}:")
            if short_p == "rdf:type":
                on.addProperty(str(prefix), new_p, {"rdfs:Class"}, {"rdfs:Class"})
            else:
                on.addProperty(str(prefix), new_p, on.properties[short_p][0], on.properties[short_p][1])
            ontology_trace_graph.add(new_p, PROV.wasDerivedFrom, abbreviate(p,abbr,prefix_dict))
            ontology_trace_graph.add(new_p, PROV.wasGeneratedBy, prefix["nf3-transformation"])

    for s, p, o in kg:
        if  (s,p) in s_p_to_rename:
            stripped_p = abbreviate(p, abbr, prefix_dict).split(":")[1]
            stripped_o = abbreviate(o, abbr, prefix_dict).split(":")[1]
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

"""
normalizes a given KG into 4NF-KG according to the definition presented in https://doi.org/10.1016/j.knosys.2025.113939 .
"""
def normalize_nf4(kg:Graph, trace_graph:IncidenceList,  ontology_trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict, negative_triple_dict, on:Ontology=None):
    """finds version of a triple from the original KG at current normalization state of KG."""
    def update_triple(triple, kg:Graph, trace_graph:IncidenceList):
        # check if triple still up to date
        if triple in kg:
            return {triple}
        
        # triple has been invalidated by NF 1-3

        # note: this is somewhat unsophisticated
        # we know that after nf3 a triple will be changed at most three times, so we are following traces by 3 levels
        # TODO handle trace graph as IncidenceList not rdflib Graph
        out = set()
        start_embedded_triple = embed_triple(triple,abbr,prefix_dict)
        lvl1_embedded_triples = set()
        for s,_,_ in trace_graph.triples((None, PROV.wasDerivedFrom, start_embedded_triple)):
            lvl1_embedded_triples.add(s)
        if not lvl1_embedded_triples:
            # triple is gone and has no successors
            return None
        
        for current_t in lvl1_embedded_triples:
            if current_t in kg:
                # current_t exists, therefore no successors
                out.add(current_t)
                continue
            # check for successors
            lvl2_embedded_triples = set()
            for s,_,_ in trace_graph.triples((None, PROV.wasDerivedFrom, current_t)):
                lvl2_embedded_triples.add(s)

            for current_t in lvl2_embedded_triples:
                if current_t in kg:
                    out.add(current_t)
                    continue
                lvl3_embedded_triples = set()
                for s,_,_ in trace_graph.triples((None, PROV.wasDerivedFrom, current_t)):
                    # reached last lvl, everything here has to bwe in kg: if is for safety but should be redundant
                    if s in kg:
                        out.add(s)
                


    print(negative_triple_dict)
    for constraint in negative_triple_dict.keys():
        # go through all constraint-shapes
        name = removePrefix(constraint, prefix)
        trace_graph.add(prefix[f"nf4-transformation-{name}"], RDF.type, PROV.Activity)
        trace_graph.add(prefix[f"nf4-transformation-{name}"], RDF.type, prefix["NF4-transformation"])
        for triple in negative_triple_dict[constraint]:
            triples_to_negate = update_triple(triple,kg,trace_graph)
            print(triples_to_negate)
            if triples_to_negate:
                for t in triples_to_negate:
                    pass# TODO
        # iterate over triples to negate, create traces
