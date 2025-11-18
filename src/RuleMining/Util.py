import numpy as np
from itertools import combinations
from RuleMining.Classes import Path, Rule, P_map, IncidenceList, Ontology, dfs

########################################
# filling custom datastructures
########################################

"""parse a graph from nt file into IncidenceList"""
def parseGraph(ntFilePath, graph:IncidenceList, prefix=""):
    with open(ntFilePath, 'r', encoding='utf-8') as file:
        for row in file:
            triple = tripleRemovePrefix(row.split()[0:3], prefix)
            graph.add(triple[0], triple[1], triple[2])

"""parse a .ttl ontology into Ontology Type"""
def parseOntology(ontology_file:str, ontology:Ontology, prefix:str=""):
    with open(ontology_file, 'r', encoding='utf-8') as file:
        block_end = False
        block = []
        for row in file:
            r = row.split()
            if r:
                # skip prefix declarations and comments
                if r[0][0] == "@" or r[0][0] == "#":
                   continue

                for e in r:
                    if e == ".":
                        # all triples for current subject are finished
                        block_end = True
                    block.append(e)

                if block_end:
                    addOntologyBlock(block, ontology, prefix)
                    block = []
                    block_end = False

"""help function for parseOntology"""
def checkForType(e):
    return e.__contains__("type")

"""help function for parseOntology"""
def checkForClass(types):
    for t in types:
        if t.__contains__("Class"):
            return True
    return False

"""help function for parseOntology"""
def checkForSubClass(e):
    return e.__contains__("subClassOf")

"""help function for parseOntology"""
def checkForProperty(types):
    for t in types:
        if t.__contains__("Property"):
            return True
    return False


"""help function for parseOntology"""
def checkForRange(e):
    return e.__contains__("range")

"""help function for parseOntology"""
def checkForDomain(e):
    return e.__contains__("domain")

"""help function for parseOntology"""
def extractName(e):
    # e is whole uri
    if e[0] == "<":
        split = e.split("/")
    # e uses prefix abbreviation
    else:
        split = e.split(":")
    out = split[len(split)-1]
    while out[len(out)-1] in (">",",",";"):
        out = out[:-1]
    return out
    
            
    return

"""help function for parseOntology;
classify triple and add to ontology"""
def addOntologyBlock(block:list[str], ontology:Ontology, prefix):
    s, p, o = block[0:3]
    if checkForType(p):
    # next item is type of s

        types = set()
        types.add(o)
        for next_i in range(3, len(block)):
            if block[next_i] == ";":
                break
            if block[next_i] == ",":
                continue
            types.add(block[next_i])

        if checkForClass(types):
        # s is a class

            ontology.addClass(prefix, s)
            for next_i in range(3 + len(types), len(block)):
                if checkForSubClass(block[next_i]):
                    i = 1
                    # add all objects given for subClassOf
                    while True:
                        ontology.addClass(prefix, s, extractName(block[next_i + i]))
                        i += 1
                        if not block[next_i + i][len(block[next_i + i])-1] == ",":
                            break

        if checkForProperty(types):
            d, r = set(), set()
            for next_i in range(3 + len(types), len(block)-1):
                if checkForDomain(block[next_i]):
                    i = 1
                    # add all objects given for domain
                    while True:
                        d.add(block[next_i +  i])
                        i += 1
                        if not block[next_i + i][len(block[next_i + i])-1] == ",":
                            break
                if checkForRange(block[next_i]):
                    i = 1
                    # add all objects given for range
                    while True:
                        r.add(block[next_i + i])
                        i += 1
                        if not block[next_i + i][len(block[next_i + i])-1] == ",":
                            break

            
            ontology.addProperty(prefix, s, {extractName(e) for e in d}, {extractName(e) for e in r})

"""remove prefix from triple"""
def tripleRemovePrefix(triple:tuple[str], prefix:str):        
    return (triple[0].removeprefix("<").removeprefix(f"{prefix}").removesuffix(">"), 
            triple[1].removeprefix("<").removeprefix(f"{prefix}").removesuffix(">"), 
            triple[2].removeprefix("<").removeprefix(f"{prefix}").removesuffix(">"))

"""add prefix to triple"""
def tripleAddPrefix(triple:tuple[str], prefix:str):        
    return (f"<{prefix}{triple[0]}>",f"<{prefix}{triple[1]}>",f"<{prefix}{triple[2]}>")




##############################
# RuDiK util/math
##############################


"""estimated marginal weight"""
def est_m_weight(r:Rule, R_out:list[Rule], kg, g:set, v:set, alpha:float, beta:float):
    cov_r_out_v = cov(R_out, kg, v)

    return -alpha * (len(cov([r], kg, g) - cov(R_out, kg, g))/len(g)) + beta * (cov_r_out_v / uncov(R_out.append(r), kg, v) - cov_r_out_v / uncov(R_out, kg, v))


"""
covarage of rules over set
"""
def cov(rules:list[Rule], kg, ex_set:set):
    # TODO
    return 


"""
unbounded coverage of rules over set
"""
def uncov(rules:list[Rule], kg, ex_set:set):
    rules = {unbind(r) for r in rules}
    # TODO 
    return cov(kg, ex_set, rules)


"""
unbinds a rule body
"""
def unbind(r:Rule):
    out = Rule()
    out.head = r.head
    target_vars = set()
    s = r.head[0]
    o = r.head[2]
    for c in r.connections:
        if s in c or o in c:
            out.connections.add(c)
            for e in c:
                target_vars.add(e)

    for atom in r.body:
        if atom[0]  in target_vars or atom[2] in target_vars:
            out.body.add(atom)

    return out


"""
check if a (sub)rule is a valid rule
"""
def is_valid(r:Rule):

    # if head object isn't connected to anything, rule is invalid
    head_o_connected = False
    for c in r.connections:
        if r.head[2] in c:
            head_o_connected = True
            break

    if not head_o_connected:
        return False
    
    con = r.connections.copy()
    body = r.body.copy()
    first = True


    #########
    # DEFINITION knot: graph entity with more than one triple --> each connection tuple represents one knot
    #########


    for atom in r.body:
        # TODO test, there are mistakes

        s_c = next((c for c in con if atom[0] in c), None)
        
        o_c = next((c for c in con if atom[2] in c ), None)
        
        # atom isn't connected to body
        if not s_c and not o_c:
            return False
        
        if len(con) > 1:
            # atom connected to two knots, one is already known to be connected
            if s_c and o_c:
                con.remove(s_c)
                con.remove(o_c)

                con.add(tuple(set(s_c).union(set(o_c))))


    if len(con) != 1: 
    # all connected knots are deleted --> there is am unconnected subgraph
        return False

    return True

# checks if an entity is allowed in a certain triple using ontology 
def fits_domain_range(entity, triple, ontology:Ontology, kg:IncidenceList, pmap:P_map, type_predicate):
    check_domain = False
    check_range = False
    literal = False
    if isLiteral(entity):
        literal = True
    if entity == triple[0]:
        if literal:
            # subject cannot be literal
            return False
        check_domain = True
    if entity == triple[2]:
        check_range = True
    if entity not in triple:
        raise ValueError("Entity not in triple.")
    
    original = original_pred(triple[1], pmap)

    if triple[1] in ontology.properties:
        domain_range = ontology.properties[triple[1]]
    elif original in ontology.properties:
        domain_range = ontology.properties[original]
    else:
        return False
        

    if literal:
        types_r = domain_range[1]
        literal_type = literalType(entity)

        for t in types_r:
            if derivable(literal_type, t, ontology.literal_hierarchy):
                return True
        return False


    else:

        # get type predicate(s) the entity has 
        type_predicates = set()
        for k in pmap.predicate_mappings:
            if pmap.predicate_mappings[k] == type_predicate:
                type_predicates.add(k)
        if entity in kg.nodes:
            entity_type_predicates = type_predicates.intersection(kg.nodes[entity])
        else:
            raise ValueError("Entity is not in knowledge graph.")

        if check_domain: 
            types_d = set()
            types_d.update(domain_range[0])

        if check_range:
            types_r = set()
            types_r.update(domain_range[1])
    
        if not entity_type_predicates:
            # entity is missing type
            return False
        
        # get entity's types
        entity_types = set()
        for etp in entity_type_predicates:
            if etp in kg.edges:
                for e in kg.edges[etp]:
                    if e[0] == entity:
                        entity_types.add(e[1])



        # derive and add supertypes of entity
        all_entity_types = set()
        while entity_types:
            t = entity_types.pop()
            all_entity_types.add(t)
            if t in ontology.classes:
                entity_types.update(ontology.classes[t])

        if check_domain:
            if not types_d.intersection(all_entity_types):
                return False
        if check_range:
            if not types_r.intersection(all_entity_types):
                return False
        return True

        

"""help function for fits_domain_range()"""
def literalType(l:str):
    temp = l.split("\"")[2]
    if temp:
        if temp.__contains__("<"):
            # with uri
            split = temp.split("/")
            return split[len(split)-1]
        else:
            if temp.__contains__(":"):
                # with prefix abbreviation
                return temp.split(":")[1]
    
    # no xsd type given
    return "anyType"

   
"""help function for fits_domain_range()"""
def isLiteral(e:str):
    # TODO make this check better
    return e.__contains__("\"")
        
"""help function for fits_domain_range()
checks if literal_type can be derived from from t according to the Type hierachy provided."""
def derivable(literal_type, t, hierarchy):
    print(f"call derivable with {literal_type}, {t}")
    if literal_type == t:
        return True
    out = False

    if t in hierarchy:
        print(f"hier t {hierarchy[t]}")
        for st in hierarchy[t]:
            print(st)
            out = out or derivable(literal_type, st, hierarchy)
            if out:
                break

    print(f"CLOSE derivable with {literal_type}, {t}")

    return out




###################################
# predicate mappings
###################################

"""
get a predicates predecessor, for a negative_pred get post-normalization positive predicate, for that, get original predicate
"""
def original_pred(new_pred:str, pmap:P_map):
    if new_pred in pmap.predicate_mappings:
        return pmap.predicate_mappings[new_pred]
    if new_pred in pmap.neg_predicate_mappings:
        return pmap.predicate_mappings[pmap.neg_predicate_mappings[new_pred]]
    return ""


"""
get post normalization predicates from their pre-normalization predecessor
"""
def new_preds(original_pred:str, pmap):
    if type(pmap) == P_map:
        return {k for k, v in pmap.predicate_mappings.items() if v == original_pred}
    # pmap is predicate mappings dict
    return {k for k, v in pmap.items() if v == original_pred}



"""
get existing negative variants of post-normalization predicates
"""
def neg_preds(new_preds:dict, pmap):
    if type(pmap) == P_map:
        return {k for k, v in pmap.neg_predicate_mappings.items() if v in new_preds}
    # pmap is predicate mappings dict
    return {k for k, v in pmap.items() if v in new_preds}


#########################################
# example generation
#########################################

"""get distributed examples for given predicates, limited by count"""
def getExamples(kg:IncidenceList, preds:set, count:int):
    out = set()
    eligible_preds = preds.copy()
    diff = count - len(out)


    # go through all predicates, get mean examples per predicate if possible
    # repeat with all predicates that still have unused instances left until count is met
    while len(out) < count and eligible_preds:
        max_i = int(diff/len(eligible_preds) + 1)  

        eligible_preds_copy = eligible_preds.copy()
        for p in eligible_preds_copy:
            l = len(kg.edges[p])
            if l <= (max_i + 1):
                # if all instances of predicate will be used, remove
                eligible_preds.remove(p)
            
            # add even share of elements per predicate, if possible
            i = 0
            for n in kg.edges[p]:
                out.add(n)
                i += 1
                if i > max_i:
                    break
                
        diff = count - len(out)

    for _ in range(-diff):
        out.pop()
    return out

"""get negative examples for given predicates that satisfy the local closed world assumption, limited by count"""
def getExamplesLCWA(kg:IncidenceList, ontology:Ontology, pmap:P_map, count:int, type_predicate:str):
    preds = pmap.predicates
    out = set()
    eligible_preds = preds.copy()
    eligible_edges = set()
    for p in preds:
        eligible_edges.update(kg.edges[p])

    pri = True

    diff = count - len(out)

    while len(out) < count and eligible_preds:
        max_i = int(diff / 2 * len(eligible_preds) + 1) 

        eligible_preds_copy = eligible_preds.copy()
        for p in eligible_preds_copy:
            l = len(kg.edges[p])
            if l <= (max_i):
                # if all instances of predicate will be used, remove
                eligible_preds.remove(p)

            i = 0
            for e in eligible_edges:
                # print(f"hello{e}\n")
                # TODO find object in neighbourhood that fits domain but doesnt have the relation with subject
                # n = (s, o) find s' and o' s.t. not exists p(s, o') and p(s', o)
                s = e[0]
                o = e[1]
                for f in eligible_edges:
                
                    if (s, f[1]) not in eligible_edges and (s, f[1]) not in out and fits_domain_range(f[1], (s,p,f[1]), ontology, kg, pmap, type_predicate):
                        out.add((s, f[1]))
                        break

                for f in eligible_edges:
                    if (f[0], o) not in eligible_edges and (f[0], o) not in out and fits_domain_range(f[0], (f[0],p,s), ontology, kg, pmap, type_predicate):
                        out.add((f[0], o))
                        break

                i += 1
                if i > max_i:
                    break
                
        diff = count - len(out)

    for _ in range(-diff):
        out.pop()
    print(f"out {out}")
    return out

