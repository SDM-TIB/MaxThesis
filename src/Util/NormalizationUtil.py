from Util.Classes import Path, Rule, P_map, IncidenceList, Ontology, is_literal_comp, removePrefix
from Util.Util import is_valid_comp, is_literal, derivable, literal_type
from rdflib import Graph, BNode, URIRef, Literal
from rdflib.namespace import RDF


"""checks wether a triple is correctly covered by given ontology."""
def fits_ontology(triple, ontology:Ontology, kg:Graph, prefix, type_predicate:URIRef=RDF.type):

    def check_entity(entity, allowed_types, on:Ontology, kg:Graph, prefix:str):
        entity_types = {removePrefix(str(t), prefix) for t in kg.objects(subject=URIRef(f"{prefix}{entity}"), predicate=type_predicate)}
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
    subject = removePrefix(s, prefix)
    predicate = removePrefix(p, prefix)
    object = removePrefix(o, prefix)

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
        literal_t = removePrefix(o.datatype, "http://www.w3.org/2001/XMLSchema#")
        for t in types_r:
            if not derivable(literal_t, t, ontology.literal_hierarchy):
                return False
    
    else:
        if not check_entity(object, types_r, ontology, kg, prefix):
            return False


    # check subject
    return check_entity(subject, types_d, ontology, kg, prefix)

