from rdflib import Graph, BNode, Literal, URIRef, Namespace
from rdflib.namespace import RDFS, PROV, RDF, XSD
import os
import time
from Util.Classes import Ontology, IncidenceList, abbreviate, removePrefix
from Util.NormalizationUtil import fits_ontology, is_valid_uri_component
from itertools import count


def normalize(kg:Graph, on:Ontology, prefix, abbr, nf1, nf2, nf3, nf4, kg_name, constraint_folder=None, bnode_name=None):
    # check inputs
    if bnode_name and type(bnode_name) != str:
        ValueError("bnode_name must be a string.")
    if not is_valid_uri_component(bnode_name):
        ValueError("bnode_name must be conform with RFC 3986.")
    if nf4 and constraint_folder == None:
        ValueError("Please provide a constraint folder for 4KG-NF transformation.")


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
            embedded_triple = f"<<{abbreviate(s, abbr, prefix_dict)}, {abbreviate(p, abbr, prefix_dict)}, {abbreviate(o, abbr, prefix_dict)}>>"
            trace_graph.add(embedded_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
            trace_graph.add(embedded_triple, PROV.wasInvalidatedBy, prefix['ontology-validation'])

    print(kg.serialize())
    #nf2 = False
    if nf1:
        normalize_nf1(kg, trace_graph, prefix, abbr, prefix_dict, bnode_name)
        print(kg.serialize())
    if nf2:
      normalize_nf2(kg, on, trace_graph, ontology_trace_graph, prefix, abbr, prefix_dict)
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
        triples_to_remove = set(kg.triples((b, None, None)))
        triples_to_remove.update(kg.triples((None, None, b)))

        for s, p, o in triples_to_remove:
            kg.remove((s, p, o))

            # s is a blank node, therefore no prefix abbreviation
            embedded_old_triple = f"<<{s}, {abbreviate(p, abbr, prefix_dict)}, {abbreviate(o, abbr, prefix_dict)}>>"
            trace_graph.add(embedded_old_triple, PROV.wasInvalidatedBy, prefix["nf1-transformation"])
            trace_graph.add(embedded_old_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")


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
def normalize_nf2(kg:Graph, on:Ontology, trace_graph:Graph,  ontology_trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict):

    def find_new_property(s,o,kg,candidates, prefix):
        # need to keep possibility in mind, that s or o have multiple types --> multiple new properties
        out = []
        types_s =  set(kg.objects(s, RDF.type))
        types_o =  set(kg.objects(o, RDF.type))
        if s == prefix["Band1"]:
            print(types_s)
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

    print(property_dict)
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
    print(triple_dict)
    # remove all keys of triple_dict, add all (s, value, o)
    for t, new_props in triple_dict.items():
        s,p,o = t
        kg.remove(t)
        print(f"remove {t}\n")
        embedded_old_triple = f"<<{abbreviate(s, abbr, prefix_dict)}, {abbreviate(p, abbr, prefix_dict)}, {abbreviate(o, abbr, prefix_dict)}>>"
        trace_graph.add(embedded_old_triple, PROV.wasInvalidatedBy, nf2_activity)
        trace_graph.add(embedded_old_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")

        for new_prop in new_props:
            kg.add((s,prefix[new_prop],o))
            print(f"add {(s,prefix[new_prop],o)}\n")
            embedded_new_triple = f"<<{abbreviate(s, abbr, prefix_dict)}, {abbreviate(new_prop, abbr, prefix_dict)}, {abbreviate(o, abbr, prefix_dict)}>>"
            trace_graph.add(embedded_new_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
            trace_graph.add(embedded_new_triple, PROV.wasDerivedFrom, embedded_old_triple)
            trace_graph.add(embedded_new_triple, PROV.wasGeneratedBy, nf2_activity)


"""
normalizes a given KG into 3NF-KG according to the definition presented for VANILLA in https://doi.org/10.1016/j.knosys.2025.113939 .
"""
def normalize_nf3(kg:Graph, on:Ontology, trace_graph:Graph,  ontology_trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict):
    trace_graph.add(prefix["nf3-transformation"], RDF.type, PROV.Activity)
    trace_graph.add(prefix["nf3-transformation"], RDF.type, prefix["NF3-transformation"])

    violations = set()
    for s,p,o in kg:
        pass

"""
normalizes a given KG into 4NF-KG according to the definition presented for VANILLA in https://doi.org/10.1016/j.knosys.2025.113939 .
"""
def normalize_nf4(kg:Graph, on:Ontology, trace_graph:Graph,  ontology_trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict):

    # TODO one instance of NF4-transformation per constraint
    trace_graph.add(prefix["nf4-transformation"], RDF.type, PROV.Activity)
    trace_graph.add(prefix["nf4-transformation"], RDF.type, prefix["NF4-transformation"])
