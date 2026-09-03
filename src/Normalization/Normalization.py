from rdflib import Graph, BNode, Literal, URIRef, Namespace
from rdflib.namespace import RDFS, PROV, RDF, XSD
import os
import time
from Util.Classes import Ontology, IncidenceList, abbreviate
from Util.NormalizationUtil import fits_ontology


def normalize(kg:Graph, on:Ontology, NS, abbr, nf1, nf2, nf3, nf4, kg_name, constraint_folder=None):

    # setup common prefixes and extend ontology for normalization-traces
    prefix_dict = {str(NS): abbr, "http://www.w3.org/ns/prov#": "prov", "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf", "http://www.w3.org/ns/rdf-star#": "rdf-star"}
    on.addClass("", "NF1-tranformation", "prov:Activity")
    on.addClass("", "NF2-tranformation", "prov:Activity")
    on.addClass("", "NF3-tranformation", "prov:Activity")
    on.addClass("", "NF4-tranformation", "prov:Activity")

    if nf4 and constraint_folder == None:
        ValueError("Please provide a constraint folder for 4KG-NF transformation.")
    print(kg.serialize())
    print(XSD)
    trace_graph = IncidenceList()
    trace_graph.add(NS["ontology-validation"], RDF.type, PROV.Activity)

    # # ontology validation
    # for s,p,o in kg:
    #     if p == RDF.type:
    #         # treat type statements strictly as metadata, retain in graph
    #         continue
    #     # TODO common properties from rdfs etc need to be accepted
    #     if not fits_ontology((s,p,o), on, kg, NS):
    #         # remove triple from kg
    #         kg.remove((s,p,o))


    #         # trace graph: note that triple was removed
    #         embedded_triple = f"<<{abbreviate(s, abbr, prefix_dict)}, {abbreviate(p, abbr, prefix_dict)}, {abbreviate(o, abbr, prefix_dict)}>>"
    #         trace_graph.add(embedded_triple, RDF.type, "http://www.w3.org/ns/rdf-star#triple")
    #         trace_graph.add(embedded_triple, PROV.invalidated, NS['ontology-validation'])


    if nf1:
        normalize_nf1(kg, trace_graph, NS, abbr, prefix_dict)
    # if nf2:
    #   normalize_nf2(kg, on, trace_graph, NS, abbr, prefix_dict, )
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


def normalize_nf1(kg:Graph, trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict):

    def handle_bnode(b, kg:Graph, trace_graph:IncidenceList, prefix:Namespace, abbr, prefix_dict):
        triples_to_remove = []



        # if node has rdfs:label, use this as name
        labels = []
        for label in kg.objects(b, URIRef("http://www.w3.org/2000/01/rdf-schema#label")):
            labels.append(label)

            # information from label is transferred to node-name, deleting triple
            kg.remove((b, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), label))

        new_name = "_".join(str(l) for l in labels)
        new_name = new_name.replace(" ", "_")
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



    trace_graph.add(prefix["nf1-transformation"], RDF.type, PROV.Activity)
    trace_graph.add(prefix["nf1-transformation"], RDF.type, prefix["NF1-transformation"])

    # find all blank nodes and handle them
    handled = set()
    for s, p, o in kg:
        if type(s) == BNode:
            s in handled or not handle_bnode(s, kg, trace_graph, prefix, abbr, prefix_dict) and handled.add(s)
        if type(o) == BNode and s != o:
            o in handled or not handle_bnode(o, kg, trace_graph, prefix, abbr, prefix_dict) and handled.add(o)
    



def normalize_nf2(kg:Graph, on:Ontology, trace_graph:Graph, prefix:Namespace, abbr, prefix_dict):
    # 1. identify ambiguous proerties
    for p in on.properties.keys():
        pass
        


    # 2. create new unambigous versions (adapt/"normalize" ontology?)

    # 3. for every ambiguos property instance, replace by unambiguous versiion




def normalize_nf3():
    pass

def normalize_nf4():
    pass