from rdflib import term

from Util.Classes import Path, Rule, P_map, IncidenceList, Ontology, is_literal_comp, removePrefix
from Util.Util import is_valid_comp, is_literal, derivable, literal_type
from rdflib import Graph, BNode, URIRef, Literal
from rdflib.namespace import RDF, RDFS
import re

"""checks wether a triple is correctly covered by given ontology."""
def fits_ontology(triple, ontology:Ontology, kg:Graph, prefix, type_predicate:URIRef=RDF.type):
    def check_entity(entity, allowed_types, on:Ontology, kg:Graph, prefix:str):
        # this is wrong, entity can be blank node ort have other prefix
        entity_name = URIRef(f"{prefix}{entity}") if not entity.__contains__(":") and not type(entity) == BNode else entity
        entity_types = {removePrefix(str(t), prefix) for t in kg.objects(subject=entity_name, predicate=type_predicate)}
        if not entity_types:
            return False

        if allowed_types.isdisjoint(entity_types):

            supertypes = set()
            for t in entity_types:
                supertypes.update(ontology.get_all_supertypes(t))

            if allowed_types.isdisjoint(supertypes):
                return False
        return True

    s, p, o = triple
    subject = removePrefix(s, prefix) if not type(s) == BNode else s
    predicate = removePrefix(p, prefix)
    object = removePrefix(o, prefix) if not type(o) == BNode else o
    accepted_namespaces = ["http://www.w3.org/ns/prov#", "prov", "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf", "http://www.w3.org/ns/rdf-star#", "rdf-star", "http://www.w3.org/2000/01/rdf-schema#", "rdfs", "http://www.w3.org/2002/07/owl#", "owl"]
    if any(str(p).startswith(pre) for pre in accepted_namespaces):
        # assume triples as true that use universal properties e.g. rdfs:label, focus on integrity of KG towards the given ontology
        # given that s and o have a type...
        print((s, RDF.type, None) in kg)
        if (s, RDF.type, None) in kg:
            if type(o) != Literal:
                if (o, RDF.type, None) in kg:
                    return True
                else:
                    print(s,p,o)
                    return False
            return True
        else:
            print(s,p,o)
            return False

    if is_literal_comp(predicate):
        if type(s) == Literal and type(o) == Literal and s.datatype == o.datatype:
            match predicate:
                case "=":
                    if not s.__eq__(o):
                        return False
                case "<":
                    if not s < o:
                        return False    
                case ">":
                    if not s > o:
                        return False
        
        # it is a literal comp, but it is not valid as checked before
        return False

    if type(s) == Literal:
            # literal comparisons have been handled before, subject cannot be literal
            return False

    
   
    if predicate in ontology.properties:
        domain_range = ontology.properties.get(predicate)
    else:
        return False

    if not domain_range:
        return False
    types_d = domain_range[0]
    types_r = domain_range[1]

    if not types_r or not types_d:
        return False

    # check object
    if type(o) == Literal:
        # if not o.datatype assume anyType
        if o.datatype:
            literal_t = removePrefix(o.datatype, "http://www.w3.org/2001/XMLSchema#")
            for t in types_r:
                if not derivable(literal_t, t, ontology.literal_hierarchy):
                    return False
    
    else:
        if not check_entity(object, types_r, ontology, kg, prefix):
            
            return False

    if o == term.URIRef('http://example.org/The_Royal_Scam'):
        print(check_entity(subject, types_d, ontology, kg, prefix))
    # check subject
    return check_entity(subject, types_d, ontology, kg, prefix)

def is_valid_uri_component(s):
    pattern = r'^[A-Za-z0-9\-._~]*$'
    return bool(re.match(pattern, s))

def remove_prefix_with_dict(element:str, prefix_dict):
    e = element.removeprefix("<").removesuffix(">")
    for prefix in prefix_dict.keys():
        if e.startswith(prefix):
            return e.removeprefix(prefix), prefix    
    for abbr in prefix_dict.values():
        if e.startswith(abbr):
            return e.removeprefix(abbr), abbr
    return element, ""