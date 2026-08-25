from rdflib import Graph, BNode, Literal, URIRef, Namespace
from rdflib.namespace import RDFS, PROV, RDF, XSD
import os
import time
from Util.Classes import Ontology, IncidenceList, abbreviate
from Util.NormalizationUtil import fits_ontology


def normalize(kg:Graph, on:Ontology, NS, abbr, nf1, nf2, nf3, nf4, kg_name, constraint_folder=None):
    prefix_dict = {str(NS): abbr, "http://www.w3.org/ns/prov#": "prov", "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf"}

    if nf4 and constraint_folder == None:
        ValueError("Please provide a constraint folder for 4KG-NF transformation.")
    print(kg.serialize())
    print(XSD)
    trace_graph = IncidenceList()
    trace_graph.add(NS["ontology-validation"], RDF.type, PROV.Activity)

    # ontology validation
    for s,p,o in kg:
        if p == RDF.type:
            # treat type statements strictly as metadata, retain in graph
            continue
        if not fits_ontology((s,p,o), on, kg, NS):
            # remove triple from kg
            kg.remove((s,p,o))


            # trace graph: note that triple was removed
            embedded_triple = f"<<{abbreviate(s, abbr, prefix_dict)}, {abbreviate(p, abbr, prefix_dict)}, {abbreviate(o, abbr, prefix_dict)}>>"
            trace_graph.add(embedded_triple, PROV.invalidated, NS['ontology-validation'])


    # if nf1:
    #     normalize_nf1(kg, trace_graph, NS)
    # if nf2:
    #     normalize_nf2(kg, on, trace_graph)
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


def normalize_nf1(kg:Graph, trace_graph:Graph, prefix):
    # find all blank nodes and handle them
    handled = set()
    for s, p, o in kg:
        if type(s) == BNode:
            s in handled or not handle_bnode(s, kg, prefix) and handled.add(s)
        if type(o) == BNode and s != o:
            o in handled or not handle_bnode(o, kg, prefix) and handled.add(o)
    
    def handle_bnode(b, kg, prefix):
        triples_to_remove = []



        # if node has rdfs:label, use this as name
        labels = []
        for label in kg.objects(b, URIRef("http://www.w3.org/2000/01/rdf-schema#label")):
            labels.append(label)

            # information from label is transferred to node-name, deleting triple
            kg.remove((b, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), label))

        new_name = "_".join(str(l) for l in labels)

        # elif node has a type, call it <type><# of bnode>
        if not new_name:
            types = []
            for t in kg.objects(b, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")):
                types.append(t)
            
            new_name = "_".join(str(t) for t in types)
            if new_name:
                new_name = new_name + f"_{time.time()}"

        # elif just change prefix from _ to namespace-prefix.
        # possibility: try to derive type by the bnodes connecting properties.
        if not new_name:
            new_name = str(b)
            


        # for all: find and remove all triples with bnode, add triples with new name
        for s, p, o in kg:
            if s == b or o == b:
                triples_to_remove.append((s,p,o))
        for s, p, o in triples_to_remove:
            kg.remove((s, p, o))
            new_s = URIRef(f"{prefix}{new_name}") if s == b else s
            new_o = URIRef(f"{prefix}{new_name}") if o == b else o
            kg.add((new_s, p, new_o))

            # TODO capture traces

def normalize_nf2(kg:Graph, on:Ontology, trace_graph:Graph):
    for p in on.properties:
        pass
    pass

def normalize_nf3():
    pass

def normalize_nf4():
    pass