from rdflib import Graph, BNode, Literal, URIRef, Namespace
from rdflib.namespace import RDFS, PROV, RDF, XSD
import os
import time
from Util.Classes import Ontology, IncidenceList, abbreviate, removePrefix
from Util.NormalizationUtil import fits_ontology, is_valid_uri_component
from itertools import count


def normalize(kg:Graph, on:Ontology, NS, abbr, nf1, nf2, nf3, nf4, kg_name, constraint_folder=None, bnode_name=None):
    # check inputs
    if bnode_name and type(bnode_name) != str:
        ValueError("bnode_name must be a string.")
    if not is_valid_uri_component(bnode_name):
        ValueError("bnode_name must be conform with RFC 3986.")
    if nf4 and constraint_folder == None:
        ValueError("Please provide a constraint folder for 4KG-NF transformation.")


    # setup common prefixes and extend ontology for normalization-traces
    prefix_dict = {str(NS): abbr, "http://www.w3.org/ns/prov#": "prov", "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf", "http://www.w3.org/ns/rdf-star#": "rdf-star"}
    on.addClass("", "NF1-tranformation", "prov:Activity")
    on.addClass("", "NF2-tranformation", "prov:Activity")
    on.addClass("", "NF3-tranformation", "prov:Activity")
    on.addClass("", "NF4-tranformation", "prov:Activity")


    print(kg.serialize())
    print(XSD)
    trace_graph = IncidenceList()
    trace_graph.add(NS["ontology-validation"], RDF.type, PROV.Activity)

    # ontology validation
    print(on)
    for s,p,o in kg:
        if p == RDF.type:
            # treat type statements strictly as metadata, retain in graph
            continue

        if not fits_ontology((s,p,o), on, kg, NS, prefix_dict=prefix_dict):
            # remove triple from kg
            kg.remove((s,p,o))


            # trace graph: note that triple was removed
            embedded_triple = f"<<{abbreviate(s, abbr, prefix_dict)}, {abbreviate(p, abbr, prefix_dict)}, {abbreviate(o, abbr, prefix_dict)}>>"
            trace_graph.add(embedded_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
            trace_graph.add(embedded_triple, PROV.invalidated, NS['ontology-validation'])


    if nf1:
        normalize_nf1(kg, trace_graph, NS, abbr, prefix_dict, bnode_name)
    if nf2:
      normalize_nf2(kg, on, trace_graph, NS, abbr, prefix_dict, )
    # if nf3:
    #     normalize_nf3()
    # if nf4:
    #     normalize_nf4()


    
    # write normalized graph to nt file, return path
    output_dir = f"./Data/Transformed_{kg_name}"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/Normalized_{kg_name}.nt"
    trace_file = f"{output_dir}/Traces_{kg_name}.nt"
    
    print(f"Saving normalized KG to {output_file}...")
    kg.serialize(destination=output_file, format='nt')

    print(f"Saving normalization-traces to {trace_file}...")
    trace_graph.ttl(trace_file, prefix_dict, "ex")

"""
normalizes a given KG into 1NF-KG according to the definition presented for VANILLA in https://doi.org/10.1016/j.knosys.2025.113939 .
renames blank nodes into unique entities, preferably by leveraging an existing label or the blank nodes type(s).
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
        for s, p, o in kg:
            if s == b or o == b:
                triples_to_remove.append((s,p,o))
        for s, p, o in triples_to_remove:
            kg.remove((s, p, o))

        # s is a blank node, therefore no prefix abbreviation
        embedded_old_triple = f"<<{s}, {abbreviate(p, abbr, prefix_dict)}, {abbreviate(o, abbr, prefix_dict)}>>"
        trace_graph.add(embedded_old_triple, PROV.invalidated, prefix["nf1-transformation"])
        trace_graph.add(embedded_old_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
        print(abbreviate(s, abbr, prefix_dict))


        new_s = URIRef(f"{prefix}{new_name}") if s == b else s
        new_o = URIRef(f"{prefix}{new_name}") if o == b else o
        kg.add((new_s, p, new_o))

        embedded_new_triple = f"<<{abbreviate(new_s, abbr, prefix_dict)}, {abbreviate(p, abbr, prefix_dict)}, {abbreviate(new_o, abbr, prefix_dict)}>>"
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
normalizes a given KG into 2NF-KG according to the definition presented for VANILLA in https://doi.org/10.1016/j.knosys.2025.113939 .
"""
def normalize_nf2(kg:Graph, on:Ontology, trace_graph:Graph, prefix:Namespace, abbr, prefix_dict):
    # 1. identify ambiguous properties
    current_properties = set(on.properties.keys())
    for p in current_properties:
        sub_domains = set(on.properties[p][0])
        sub_ranges = set(on.properties[p][1])
        print(sub_domains)
        for d in  on.properties[p][0]:
            sub_domains.update(on.get_all_subtypes(d)) 
        for d in  on.properties[p][1]:
            sub_ranges.update(on.get_all_subtypes(d))
        # TODO: there is a mistake here, only the leaves of the class hierarchy are important here

        # still 1. and also: 2. create new unambigous versions (adapt/"normalize" ontology?); only rename where needed

        # for all linear combinations  (sub_domain x sub_range), we need a unique property.
        sub_domains = list(sub_domains)
        sub_ranges = list(sub_ranges)
        ld = len(sub_domains)
        lr = len(sub_ranges)

        print(on.get_all_subtypes("owl:Thing"))

        if ld > 1 and lr > 1:
            for i in range(ld):
                for j in range(lr):
                    pass
        elif ld > 1:
        # only rename with domain type
            for i in range(ld):
                pass
        elif lr > 1:
        # only rename with range type
            for i in range(lr):
                pass

        # 3. for every ambiguous property instance, replace by unambiguous version in KG, create traces



"""
normalizes a given KG into 3NF-KG according to the definition presented for VANILLA in https://doi.org/10.1016/j.knosys.2025.113939 .
"""
def normalize_nf3():
    pass

"""
normalizes a given KG into 4NF-KG according to the definition presented for VANILLA in https://doi.org/10.1016/j.knosys.2025.113939 .
"""
def normalize_nf4():
    pass