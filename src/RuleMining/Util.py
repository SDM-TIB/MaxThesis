import random
import numpy as np
from itertools import combinations 
from RuleMining.Classes import Path, Rule, P_map, IncidenceList, Ontology, is_literal_comp
import time

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




    """help function for parseOntology"""
    def checkForType(e):
        return e.__contains__("type") or e == "a"

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
        out = e
        if e[0] == "<":
            split = e.split("/")
            out = split[len(split)-1]

        # e uses prefix abbreviation
        else:
            split = e.split(":")
            if split[len(split)-2] in ("rdf", "rdfs", "owl"):
                out = f"{split[len(split)-2]}:{split[len(split)-1]}"

            else:
                out = split[len(split)-1]
        while out[len(out)-1] in (">",",",";"):
            out = out[:-1]
        return out
        
    """Handles a block(file segment until next '.' --> everything belonging to the last stated subject) from an ontology file, adds the extracted information to the given Ontology object"""
    def addOntologyBlock(block:list[str], ontology:Ontology, prefix):
        s = block[0]
        current_i = 1
        max_i = len(block)
        domain = set()
        range = set()
        super = set()
        types = set()
        isClass = False
        isProperty = False
        while current_i < max_i:
            p = block[current_i]
            current_i += 1
            o = block[current_i]
            current_i += 1

            if checkForType(p):
                types.add(o)

                while current_i < max_i:

                    if block[current_i] == ";":
                        break
                    if block[current_i] == ",":
                        current_i += 1
                        continue

                    o = block[current_i]

                    types.add(o)
                    current_i += 1

                if checkForClass(types):
                    isClass = True

                if checkForProperty(types):
                    isProperty = True


            elif checkForSubClass(p):
                isClass = True
                super.add(o)
                while current_i < max_i:

                    if block[current_i] == ";":
                        break
                    if block[current_i] == ",":
                        current_i += 1
                        continue

                    o = block[current_i]

                    super.add(o)
                    current_i += 1


                
            elif checkForDomain(p):
                domain.add(o)
                while current_i < max_i:

                    if block[current_i] == ";":
                        break
                    if block[current_i] == ",":
                        current_i += 1
                        continue

                    o = block[current_i]

                    domain.add(o)
                    current_i += 1
                
            elif checkForRange(p):
                range.add(o)
                while current_i < max_i:

                    if block[current_i] == ";":
                        break
                    if block[current_i] == ",":
                        current_i += 1
                        continue

                    o = block[current_i]

                    range.add(o)
                    current_i += 1
            else:
                # irrelevant predicate, skip to next one
                while current_i < max_i and block[current_i] != ";":
                    current_i += 1
            

            # each of the if clauses ends on a current_i where block[current_i] == ";" or >= max_i
            # setting current_i to next predicate
            current_i += 1

        # add collected info to ontology
        if isClass:
            if super:
                for sup in super:
                    ontology.addClass(prefix, extractName(s), extractName(sup))
            else:
                ontology.addClass(prefix, extractName(s))
            
        if isProperty:
            ontology.addProperty(prefix, extractName(s), {extractName(e) for e in domain}, {extractName(e) for e in range})



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
                    if e[len(e)-1] == ".":
                        # all triples for current subject are finished
                        block_end = True
                        if len(e) > 1:
                            block.append(e[0:len(e)-1])
                        break
                    
                    if e[len(e)-1] == ",":
                        if len(e) > 1:
                            block.append(e[0:len(e)-1])
                        block.append(",")                    
                    elif e[len(e)-1] == ";":
                        if len(e) > 1:
                            block.append(e[0:len(e)-1])
                        block.append(";")
                    else:
                        block.append(e)

                if block_end:
                    addOntologyBlock(block, ontology, prefix)
                    block = []
                    block_end = False


def check_preds_in_graph(neg_predicate_mappings, kg:IncidenceList):
    for p in neg_predicate_mappings.values():
        if p not in kg.edges:
            kg.edges[p] = set()


"""remove prefix from triple"""
def tripleRemovePrefix(triple:tuple[str], prefix:str):    
    if triple[2][0] == "<":
    # object is an entity
        return (triple[0].removeprefix("<").removeprefix(f"{prefix}").removesuffix(">"), 
                triple[1].removeprefix("<").removeprefix(f"{prefix}").removesuffix(">"), 
                triple[2].removeprefix("<").removeprefix(f"{prefix}").removesuffix(">"))
    else:
        # object is literal
        return (triple[0].removeprefix("<").removeprefix(f"{prefix}").removesuffix(">"), 
                triple[1].removeprefix("<").removeprefix(f"{prefix}").removesuffix(">"), 
                triple[2])

"""add prefix to triple"""
def tripleAddPrefix(triple:tuple[str], prefix:str):        
    return (f"{prefix}{triple[0]}",f"{prefix}{triple[1]}",f"{prefix}{triple[2]}")




##############################
# RuDiK util/math
##############################

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
        if atom[0] in target_vars or atom[2] in target_vars:
            out.body.add(atom)

    return out


"""
coverage of r over g
"""
def cov_g(r, rule_dict, R_out_dict):
    # special case, just check dict entries for each rule and see the heads of the paths and compare to g
    c = set()
    if not r:
        return c
    if type(r) == Rule:
        if r in rule_dict:
            for path in rule_dict[r]:
                c.add((path.head[0], path.head[2]))
        elif r in R_out_dict:
            for path in R_out_dict[r]:
                c.add((path.head[0], path.head[2]))  
        else: 
            raise ValueError("unknown rule")  
    elif type(r) == list and r and type(r[0]) == Rule:
        for rule in r:
            c.update(cov_g(rule, rule_dict, R_out_dict))
    else:
        raise ValueError("r must be type Rule or list[Rule]")
    
    return c


def patterns_in_graph(rule:Rule, triple_patterns, name_dict, kg:IncidenceList, pmap:P_map):
    #print(f"call with {triple_patterns} and dict {name_dict}")

    # init: pick 1st triple pattern:
    # for all possible triples, create a solution object: pick head-s triple pattern

        # II. while unhadled triple patterns:
                # - pick next triple pattern --> prioritise patterns partly instantiated in solution objects
                # - for all solution objects, keep and extend the ones that fit
                # - if no solution objects --> FALSE

        # --> TRUE

    if not triple_patterns:
        return True

    # init 
    # find 1st pattern
    handled_triple_patterns = set()
    current_pattern = None

    for pattern in triple_patterns:
        if pattern[0] in name_dict:
            if pattern[2] in name_dict:
                if not triple_exists((name_dict[pattern[0]], name_dict[pattern[2]]), pattern[1], kg, pmap):
                    return False
                else: 
                    handled_triple_patterns.add(pattern)
                    if handled_triple_patterns == triple_patterns:
                        return True
                    continue
            current_pattern = pattern
            pattern_i = 0
            pattern_j = 2
            break
        if pattern[2] in name_dict:
            current_pattern = pattern
            pattern_i = 2
            pattern_j = 0
            # TODO check if faster without this break, also in parallel place later, idea: there are objects with a lot of connections e.g. "male", not so much subjects
            break
    if not current_pattern:
        current_pattern = pattern


    #print(f"pick pattern {current_pattern}")
    new_dict = {}
    solutions = []
    new_entities = set()
    new_connections = rule.get_connections(current_pattern[pattern_j])

    for p in kg.nodes[name_dict[current_pattern[pattern_i]]]:
        if pmap.original_pred(p) == current_pattern[1] and p not in pmap.neg_predicate_mappings:
            for pair in kg.edges[p]:
                if pair[int(pattern_i/2)] == name_dict[current_pattern[pattern_i]]:
                    new_entities.add(pair[int(pattern_j/2)])

    #print(f"found these entities {new_entities}")

    for e in new_entities:
        for var in new_connections:
            new_dict[var] = e
        solutions.append(name_dict | new_dict)
    handled_triple_patterns.add(current_pattern)
    if not solutions:
        return False
    if handled_triple_patterns == triple_patterns:
        return True

    #print(f"createtd solutions: {solutions}")
    while True:
        # - pick next triple pattern --> prioritise patterns partly instantiated in solution objects
        #print(f"\n+++start while {handled_triple_patterns}")
        current_pattern = None
        for pattern in triple_patterns:
            if pattern in handled_triple_patterns:
                continue

            # each solution has the same set of keys
            current_solution = solutions[0]
            if pattern[0] in current_solution:
                if pattern[2] in current_solution:
                    remaining_solutions = []
                    for sol in solutions:
                        if triple_exists((sol[pattern[0]], sol[pattern[2]]), pattern[1], kg, pmap):
                            remaining_solutions.append(sol)
                    if not remaining_solutions:
                        return False
                    else: 
                        solutions = remaining_solutions
                        handled_triple_patterns.add(pattern)
                        #print(f"add to handled {pattern}")
                        if handled_triple_patterns == triple_patterns:
                            #print(f"return true with {solutions}")
                            return True
                        continue
                current_pattern = pattern
                pattern_i = 0
                pattern_j = 2
                break
            if pattern[2] in current_solution:
                current_pattern = pattern
                pattern_i = 2
                pattern_j = 0
                break

        if not current_pattern:
            current_pattern = pattern


        # - for all solution objects, keep and extend the ones that fit 
        # --> all erroneous solutions are already removed, extend now
        new_connections = rule.get_connections(current_pattern[pattern_j])
        new_dict.clear()
        new_solutions = []
        for sol in solutions:
            # if a solution is not expandable, it is not added to new solutions
            new_entities.clear()
            for p in kg.nodes[sol[current_pattern[pattern_i]]]:
                if pmap.original_pred(p) == current_pattern[1]:
                    for pair in kg.edges[p]:
                        if pair[int(pattern_i/2)] == sol[current_pattern[pattern_i]]:
                            new_entities.add(pair[int(pattern_j/2)])
            for e in new_entities:
                for var in new_connections:
                    new_dict[var] = e
                new_solutions.append(sol | new_dict)

        if not new_solutions:
            return False
        handled_triple_patterns.add(current_pattern)
        if handled_triple_patterns == triple_patterns:
            return True
        solutions = new_solutions
        #print(f"got these solutions left {solutions}")


def covers_example(rule:Rule, example:tuple[str, str], kg:IncidenceList, pmap:P_map):

# I: in triple patterns, find connected groups, for each:

    # call subfunction:
        # init: pick 1st triple pattern:
            # for all possible triples, create a solution object: pick head-s triple pattern

        # II. while unhadled triple patterns:
                # - pick next triple pattern --> prioritise patterns partly instantiated in solution objects
                # - for all solution objects, keep and extend the ones that fit
                # - if no solution objects --> FALSE

        # --> TRUE



    c_head_s = rule.get_connections(rule.head[0])
    name_dict_s = {var:example[0] for var in c_head_s}
    

    if rule.head[2] in c_head_s:
        if example[0] != example[1]:
            # ex s and o must be the same if rule.head s and o are
            return False
        c_head_o = c_head_s
        # head s=o, so everything is connected
        return patterns_in_graph(rule, rule.body, name_dict_s, kg, pmap)
    c_head_o = rule.get_connections(rule.head[2])
    name_dict_o = {var:example[1] for var in c_head_o}

    if not c_head_o:
        # nothing connected to head o, so everything to head s

        return  patterns_in_graph(rule, rule.body, name_dict_s, kg, pmap)

    # find out if there are two unconnected groups of patterns
    head_s_connected_patterns = set()
    var_queue = {c_head_s}
    vars_checked = set()
    while True:
        vars_to_check = var_queue.pop()
        for triple_pattern in rule.body:
            if triple_pattern in head_s_connected_patterns:
                continue

            if triple_pattern[0] in vars_to_check:
                head_s_connected_patterns.add(triple_pattern)
                if triple_pattern[2] not in vars_to_check and not any(c for c in vars_checked if triple_pattern[2] in c):
                    var_queue.add(rule.get_connections(triple_pattern[2]))

            if triple_pattern[2] in vars_to_check:
                head_s_connected_patterns.add(triple_pattern)
                if not any(c for c in vars_checked if triple_pattern[0] in c):
                    var_queue.add(rule.get_connections(triple_pattern[0]))

        vars_checked.add(vars_to_check)
        if not var_queue:
            break
    

    if len(head_s_connected_patterns) != len(rule.body):
        # there are two groups of patterns, start with head o group
        if not patterns_in_graph(rule, rule.body - head_s_connected_patterns, name_dict_o, kg, pmap):
            return False

    # check everything connected to head s
    return patterns_in_graph(rule, head_s_connected_patterns, name_dict_s|name_dict_o, kg, pmap)


def triple_exists(pair, original_p, kg:IncidenceList, pmap:P_map):
    s, o = pair
    for object_pred in kg.nodes[o]:
        if pmap.original_pred(object_pred) == original_p:
            if pair in kg.edges[object_pred]:
                return True
    return False


def coverage(r, v, kg, pmap):
    out = set()
    for example_pair in v:
        if covers_example(r, example_pair, kg, pmap):
            out.add(example_pair)
    return out


def unbounded_coverage(r, v, kg, pmap):
    return coverage(unbind(r), v, kg, pmap)


def rulelist_call_coverage(r, v, kg, pmap, out:set):
    for example_pair in v:
        if example_pair in out:
            continue
        if covers_example(r, example_pair, kg, pmap):
            out.add(example_pair)


def rulelist_coverage(R, v, kg, pmap):
    out = set()
    for rule in R:    
        rulelist_call_coverage(rule, v, kg, pmap, out)
    return out


def rulelist_unbounded_coverage(R, v, kg, pmap):
    out = set()
    for rule in R:    
        rulelist_call_coverage(unbind(rule), v, kg, pmap, out)
    return out


"""estimated marginal weight"""
def est_m_weight(r:Rule, R_out_dict, rule_dict, kg:IncidenceList, g:set, v:set, alpha:float, beta:float, pmap:P_map, R_out_cov_v_cardinality:list, R_out_uncov_v:set):

    # contain only r_out
    R_out = list(R_out_dict.keys())

    # if there is no value pre saved, calculate it else use it
    if R_out_cov_v_cardinality[0] == None:
        cardinality_cov_r_out_v = len(rulelist_coverage(R_out, v,kg,  pmap))
        R_out_cov_v_cardinality[0] = cardinality_cov_r_out_v
    else:
        cardinality_cov_r_out_v = R_out_cov_v_cardinality[0]

    # if there is no value pre saved, calculate it else use it
    if R_out_uncov_v == None:
        uncov_r_out_v = rulelist_unbounded_coverage(R_out,  v,kg, pmap)

        R_out_uncov_v = uncov_r_out_v
    else:
        uncov_r_out_v = R_out_uncov_v

    cardinality_uncov_r_out_v = len(uncov_r_out_v)


    # no need to check for the examples already in uncov_r_out_v (--> (v - uncov_r_out_v)),  since uncov_r_v is only used in union 
    uncov_r_v = unbounded_coverage(r, (v - uncov_r_out_v), kg, pmap)
    cardinality_uncov_r_out_r_v = len(set.union(uncov_r_out_v, uncov_r_v))




    if not cardinality_cov_r_out_v:
    # if this is zero we know the beta part is zero, the divisors will also be zero resulting in error, thus removing beta part altogether
        return -alpha * ((len(cov_g(r, rule_dict, R_out_dict) - cov_g(R_out, rule_dict, R_out_dict)))/len(g))
    
    if not cardinality_uncov_r_out_r_v:
    # if this is zero there is division by zero in first fraction of beta part, setting it to zero
        return  -alpha * ((len(cov_g(r, rule_dict, R_out_dict) - cov_g(R_out, rule_dict, R_out_dict)))/len(g)) - beta * (cardinality_cov_r_out_v / cardinality_uncov_r_out_v)


    return -alpha * ((len(cov_g(r, rule_dict, R_out_dict) - cov_g(R_out, rule_dict, R_out_dict)))/len(g)) + beta * ((cardinality_cov_r_out_v / cardinality_uncov_r_out_r_v) - (cardinality_cov_r_out_v / cardinality_uncov_r_out_v))


"""
check if a (sub)rule is a valid rule, 
in its use context it is safe to assume all atoms are transitively connected
"""
def is_valid(r:Rule):
    for c in r.connections:
        if r.head[2] in c:
            if r.head[0] in c:
                # must be at least 4 vars in c, 2 are from head, need one more to go away and one to come back
                return len(c) >= 4
            return True
    return False


def is_valid_comp(triple, kg, pmap:P_map):
    if not is_literal_comp(triple[1]) or (literal_type(triple[0]) != literal_type(triple[2])):
        return False  
    
    if triple[1] == "=":
        if triple[0] != triple[2]:
            return False
    elif triple[1] == "<":
        if triple[0] >= triple[2]:
            return False
        
    return True


def fits_domain_range(entity, triple, ontology:Ontology, kg:IncidenceList, pmap:P_map, type_predicate):
    if entity not in triple:
        raise ValueError("Entity not in triple.")
    

    check_domain = False
    check_range = False
    literal = is_literal(entity)

    



    
    if is_literal_comp(triple[1]):
        if literal and is_valid_comp(triple):
            return True
        
        # it is a literal comp, but it is not valid as checked before
        return False
    
    

    if entity == triple[0]:
        if literal:
            # literal comparisons have been handled before, subject cannot be literal
            return False
        check_domain = True

    if entity == triple[2]:
        check_range = True

    
    p = triple[1] 
    original = pmap.original_pred(p)
    # depending on given predicate (old or new), this insures it is found in ontology
    if p in ontology.properties:
        domain_range = ontology.properties[p]
    elif original in ontology.properties:
        domain_range = ontology.properties[original]
    else:
        return False
        

    if literal:
        types = domain_range[1]
        literal_t = literal_type(entity)

        for t in types:
            if derivable(literal_t, t, ontology.literal_hierarchy):
                return True
        return False


    else:
        # get type predicate(s) the entity has 
        # TODO are constraints about type predicate allowed?
        entity_type_predicates = {tp for tp in kg.nodes[entity] if pmap.predicate_mappings.get(tp) == type_predicate}
        if not entity_type_predicates:
            # entity is missing type
            return False
        
        if check_domain and check_range:
            types_d = domain_range[0]
            types_r = domain_range[1]
            # get entity's types
            entity_types = set()
            fits_d = False
            fits_r = False
            for etp in entity_type_predicates:
                t = next(p for p in kg.edges[etp])[1]
                if not fits_d and t in types_d:
                    fits_d = True
                if not fits_r and t in types_r:
                    fits_r = True
                if fits_d and fits_r:
                    return True
                if t in ontology.classes:
                    entity_types.add(t)



            # no direct type match so far, check entitys supertypes
            all_entity_types = set()
            while entity_types:
                all_entity_types.update(ontology.classes[entity_types.pop()])



            if fits_r or types_r.intersection(all_entity_types):
                if fits_d or types_d.intersection(all_entity_types):
                    return True

            return False



        else:
            if check_domain: 
                types = domain_range[0]
            else:
                types = domain_range[1]

            # get entity's types
            entity_types = set()
            for etp in entity_type_predicates:
                t = next(p for p in kg.edges[etp])[1]
                if t in types:
                    return True
                if t in ontology.classes:
                    entity_types.add(t)



            # no direct type match so far, check entitys supertypes
            all_entity_types = set()
            while entity_types:
                all_entity_types.update(ontology.classes[entity_types.pop()])



            if types.intersection(all_entity_types):
                return True


            return False


"""help function for fits_domain_range()"""
def literal_type(l:str):
    temp = l.split("\"")[2]
    if temp:
        if temp.__contains__("<"):
            # with uri
            split = temp.split("/")
            return split[len(split)-1].removesuffix(">")
        else:
            if temp.__contains__(":"):
                # with prefix abbreviation
                return temp.split(":")[1]
    
    # no xsd type given
    return "anyType"

   
"""help function for fits_domain_range()"""
def is_literal(e:str):
    return e.__contains__("\"")
        
"""help function for fits_domain_range()
checks if literal_type can be derived from from t according to the Type hierachy provided."""
def derivable(literal_type, t, hierarchy):
    if literal_type == t:
        return True

    if t in hierarchy:
        for st in hierarchy[t]:
            if derivable(literal_type, st, hierarchy):
                return True

    return False



###################################
# predicate mappings
###################################
"""
get post normalization predicates from their pre-normalization predecessor via dict
"""
def new_preds(original_pred:str, map:dict):
    # map should be predicate mappings dict
    if type(map) == dict:
        return {k for k, v in map.items() if v == original_pred}
    return None

"""
get existing negative variants of post-normalization predicates via dict
"""
def neg_preds(new_preds:set, map):
    # map should be neg predicate mappings dict
    if type(map) == dict:
        return {k for k, v in map.items() if v in new_preds}
    return None


#########################################
# example generation
#########################################

"""get distributed examples for given predicates, limited by count"""
def getExamples(kg:IncidenceList, preds:set, count:int, ontology, pmap, type_predicate):
    g = set()
    g_sub = set()
    eligible_preds = preds.copy()
    diff = count


    # go through all predicates, get even share of examples per predicate if possible
    # repeat with all predicates that still have unused instances left until count is met

    max_i = int(diff/len(eligible_preds) + 1)  

    eligible_preds_copy = eligible_preds.copy()
    for p in eligible_preds_copy:
        edges_p = kg.edges.get(p)
        if not edges_p:
            continue

        l = len(edges_p) 
        if l <= (max_i + 1):
            # if all instances of predicate will be used, remove
            eligible_preds.remove(p)
        
        # add even share of elements per predicate, if possible
        i = 0
        for n in edges_p:
            triple = (n[0], p, n[1])
            if triple not in g:
                if fits_domain_range(n[0], triple, ontology, kg, pmap, type_predicate) and fits_domain_range(n[1], triple, ontology, kg, pmap, type_predicate):
                    g.add(triple)
                    i += 1
                if i > max_i:
                    g_sub.add(triple)
                    if i > 2*max_i and len(g_sub) >= count:
                        break
            
        diff = count - len(g)

    for _ in range(-diff):
        g.pop()

    for _ in range(diff):
        if g_sub:
            g.add(g_sub.pop())
        else:
            break
    return g

"""get distributed negative examples for given predicates, by finding instances of negative predicates, limited by count"""
def getNegExamples(kg:IncidenceList, preds:set, count:int):
    if not preds:
        return set()
    v = set()
    v_sub = set()
    eligible_preds = preds.copy()
    diff = count


    # go through all predicates, get mean examples per predicate if possible

    l = len(v)
    max_i = int(diff/len(eligible_preds) + 1)  

    eligible_preds_copy = eligible_preds.copy()

    for p in eligible_preds_copy:
        edges_p = kg.edges.get(p)
        if not edges_p:
            continue

        l = len(edges_p) 
        if l <= (max_i + 1):
            # if all instances of predicate will be used, remove
            eligible_preds.remove(p)
        
        # add even share of elements per predicate, if possible
        i = 0
        for n in edges_p:
            pair = (n[0], n[1])
            if pair not in v:
                v.add(pair)
                i += 1
            if i > max_i:
                v_sub.add(pair)
                if i > 2*max_i and len(v_sub) >= count:
                    break
            
    diff = count - len(v)

    for _ in range(-diff):
        v.pop()
    for _ in range(diff):
        if v_sub:
            v.add(v_sub.pop())
        else:
            break
    return v

"""get negative examples for given predicates that satisfy the local closed world assumption, limited by count"""
def getExamplesLCWA(kg:IncidenceList, ontology:Ontology, pmap:P_map, count:int, type_predicate:str):

    preds = pmap.predicates
    out = set()

    # will hold all instances of target predicate
    forbidden_edges = set()
    subjects = set()
    objects = set()
    for p in preds:
        edges = kg.edges.get(p)
        if edges:
            forbidden_edges.update(edges)
            subjects.update({pair[0] for pair in edges})
            objects.update({pair[1] for pair in edges})
    
    subjects = list(subjects)
    objects = list(objects)
    for _ in range(3 * count):
        if len(out) >= count or not subjects or not objects:
            return out
        pair = (random.choice(subjects), random.choice(objects))
        if pair not in forbidden_edges:
            if fits_domain_range(pair[0], (pair[0], pmap.target, pair[1]), ontology, kg, pmap, type_predicate):
                if fits_domain_range(pair[1], (pair[0], pmap.target, pair[1]), ontology, kg, pmap, type_predicate):
                    out.add(pair)
                else:
                    objects.remove(pair[1])

            else:
                subjects.remove(pair[0])

        
    return out

"""get random pairs of entities that don't have target predicate"""
def getRandomNegExamples(kg:IncidenceList, preds:set, count:int, v=set()):
    ct = 1
    fact = 1

    forbidden_pairs = set()
    for p in preds:
        ed = kg.edges.get(p)
        if ed:
            forbidden_pairs.update(ed)


    # finding set size where |set X set| > count
    while fact <= count:
        ct+=1
        fact *= ct

    # this is somewhat arbitrary, goal is to remove some bias by having more distinct entities in the set while managing computational work --> not going through all kg.nodes
    ct *= 2

    entities = []

    for e in kg.nodes:

        entities.append(e)
        ct += 1
        if ct >= count:
            break

    out = set()
    for _ in range(3 * count):
        pair = (random.choice(entities), random.choice(entities))
        if pair not in v and pair not in forbidden_pairs:
            out.add(pair)
        if len(out) == count:
            return out
    return out
