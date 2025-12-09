import random
import numpy as np
from itertools import combinations
from RuleMining.Classes import Path, Rule, P_map, IncidenceList, Ontology, dfs, is_literal_comp

########################################
# filling custom datastructures
########################################

# TODO refactor every dict call in project to use get()

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


def instantiate(rule:Rule, kg:IncidenceList, entity_dict, pmap):
    # TODO similar to instantiable(), but form and return paths here
    pass
 

"""checks if triples that result from instanciating a certain entity are in the kg
    e: entity value 
    c: connection tuple that represents all instances of e in the rule
    entity_dict: dict: var in rule -> entity in graph"""
def valid_entity_instanciation(e, c, r:Rule, entity_dict, pmap:P_map, kg:IncidenceList):
    
    if not is_literal(e) and len(kg.nodes[e]) < len(c):
        # except for literals, entities cannot appear more often in rule than the amount of triples they're apart of, in which the otherr variable isn't dangling!!!
        # TODO try to see if this check makes it faster, need to add that triples where the other var is dangling don't count bc that can be the same triple as one alrready used...
        # return False
        pass
    for var in c:

        found = False

        if var in r.head:
            continue
        else:
            # next is ok to use b/c there is exactly one appearance per var
            triple = next(t for t in r.body if var in t)


        if triple[0] == var:
            # check only if triple will be completed by instantiating entity
            if triple[2] in entity_dict:
                pair = (e, entity_dict[triple[2]])
            else:
                continue


        else:
            # check only if triple will be completed by instantiating entity
            if triple[0] in entity_dict:
                pair = (entity_dict[triple[0]], e)
            else:
                continue

        if is_literal_comp(triple[1]):
            found = is_valid_comp((pair[0], triple[1], pair[1]))
        else:
            for p in pmap.new_preds(triple[1]):
                ed = kg.edges.get(p)
                if ed and pair in ed:
                    # triple exists for current var
                    found = True
                    break

        if not found:
            # instanciation does not work with this variable
            return False
    return True



"""
checks if a rule where some variables may already be instantiated, can be fully instantiated over the kg
"""
# TODO this goes through all combinations chronologically, backtracking algorithm might be faster,
def instantiable(rule:Rule, kg:IncidenceList, pmap:P_map, entity_dict):
    
    # no given instanciations, start with head
    if not entity_dict:
        s,p,o = next(t for t in rule.body if not is_literal_comp(t[1]))
        c = {s}
        for con in rule.connections:
            if s in con:
                c = con
                break

        preds = pmap.new_preds(p)
        if preds == None:
                raise ValueError("unknown predicate in rule.")
            
        possible_s = set()
        for pr in preds:
            possible_s.update(pair[0] for pair in kg.edges[pr])
        for s in possible_s:
            entity_dict = {}
            for var in c:
                entity_dict[var] = s
            if instantiable(rule, kg, pmap, entity_dict):
                return True
        return False
    
    for triple in rule.body:
    # find dangling triple


        is_s = triple[0] in entity_dict
        is_o = triple[2] in entity_dict

        if is_literal_comp(triple[1]) and is_s and is_o:
            if not is_valid_comp((entity_dict[triple[0]], triple[1], entity_dict[triple[2]])):
                return False

        if is_s != is_o:
            preds = pmap.new_preds(triple[1])
            if preds == None:
                raise ValueError("unknown predicate in rule.")
            
            edges = set()
            for pr in preds:
                ed = kg.edges.get(pr)
                if ed:
                    edges.update(ed) 


            # find all instances for var that is not instantiated yet and recurse
            if is_s:
            # need to instantiate object

                s = entity_dict[triple[0]]

                if is_literal_comp(triple[1]):
                    s_type = literal_type(s)
                    possible_o = {l for l in kg.nodes.keys() if is_literal(l) and s_type == literal_type(l)}
                else:
                    possible_o = {pair[1] for pair in edges if pair[0] == s} 

                # if no instances for triple, rule is not instantiable along current path
                if not possible_o:
                    return False
                
                # get o-connections
                c = {triple[2]}
                for con in rule.connections:
                    if triple[2] in con:
                        c = con
                        break
                
                for o in possible_o:
                    if not valid_entity_instanciation(o, c, rule, entity_dict, pmap, kg):
                        continue
                    new_entity_dict = dict(entity_dict)
                    for var in c:
                        new_entity_dict[var] = o
                    if instantiable(rule, kg, pmap, new_entity_dict):
                        return True
                    
                return False
                
            else:
            # need to instantiate subject
                o = entity_dict[triple[2]]
                if is_literal_comp(triple[1]):
                    o_type = literal_type(o)
                    possible_s = {l for l in kg.nodes.keys() if is_literal(l) and o_type == literal_type(l)}
                else:
                    possible_s = {pair[0] for pair in edges if pair[1] == o} 

                # if no instances for triple, rule is not instantiable along current path
                if not possible_s:
                    return False
                
                # get s-connections
                c = {triple[0]}
                for  con in rule.connections:
                    if triple[0] in con:
                        c = con
                        break

                for s in possible_s:
                    if not valid_entity_instanciation(s, c, rule, entity_dict, pmap, kg):
                        continue
                    new_entity_dict = dict(entity_dict)
                    for var in c:
                        new_entity_dict[var] = s
                    if instantiable(rule, kg, pmap, new_entity_dict):
                        return True
                return False
            


    # no dangling triples, all instanciated -> assumes body is completely connected 
    return True


"""
ckecks if a rules body covers a given example (pair of entities)
"""
def covers(r:Rule, kg, ex, pmap):

    # initialise, get occurences of target vars
    t_1 = r.head[0]
    t_2 = r.head[2]
    # bools if t_1 or t_2 have been handled already, used for avoiding unnessecary computations
    b1 = False
    b2 = False
    entity_dict = {}

    # find vars that connect to head and instantiate them with the example pairtwitch

    for c in r.connections:
        if not b1 and  t_1 in c:
            b1 = True
            if b2:
                # this is only relevant if there is a body atom between the head entities
                if not valid_entity_instanciation(ex[0], c, r, entity_dict, pmap, kg):
                    return False
            for var in c:
                entity_dict[var] = ex[0]
            
        if not b2 and t_2 in c:
            b2 = True
            if b1:
                # this is only relevant if there is a body atom between the head entities
                if not valid_entity_instanciation(ex[1], c, r, entity_dict, pmap, kg):
                    return False
            for var in c:
                entity_dict[var] = ex[1]


        if b1 and b2:
            break

    # check if instantiation is possible with example pair as targets 
    return instantiable(r, kg, pmap, entity_dict)

"""
covarage of a rule/rules over set
"""
def cov(r:Rule, kg, ex_set:set, pmap:P_map):
    c = set()
    if type(r) == Rule:
        for ex in ex_set:
            if covers(r, kg, ex, pmap):
                c.add(ex)
    elif type(r) == list and r and type(r[0])== Rule:
        ex_set_copy = ex_set.copy()
        for rule in r:
            c.update(cov(rule, kg, ex_set_copy,pmap))

            # remove examples that are already covered, to avoid checking them again
            ex_set_copy = ex_set_copy - c
    else:
        raise ValueError("r must be type Rule or list[Rule]")
    return c

"""
unbounded coverage of rules over set
"""
def uncov(r:Rule, kg, ex_set:set, pmap):
    if type(r) == Rule:
        u_r = unbind(r)
    elif type(r) == list and r and type(r[0]) == Rule:
        u_r = [unbind(rule) for rule in r]
    return cov(u_r,kg, ex_set,  pmap)


"""
coverage of r over g
"""
def cov_g(r, g, rule_dict):
    # TODO special case, just check dict entries for each rule and see the heads of the paths and compare to g
    c = set()
    if type(r) == Rule:
        for path in rule_dict[r]:
            c.add((path.head[0], path.head[2]))

    elif type(r) == list and r and type(r[0]) == Rule:
        g_copy = g.copy()
        for rule in r:
            c.update(cov_g(rule, g_copy, rule_dict))
    else:
        raise ValueError("r must be type Rule or list[Rule]")
    return c

"""
unbounded coverage of r over g
"""
def uncov_g(r, g, rule_dict):
    if type(r) == Rule:
        u_r = unbind(r)
    elif type(r) == list and r and type(r[0]) == Rule:
        u_r = [unbind(rule) for rule in r]
    return cov_g(u_r, g, rule_dict)



"""estimated marginal weight"""
def est_m_weight(r:Rule, R_out:list[Rule], rule_dict, kg, g:set, v:set, alpha:float, beta:float, pmap):
    cardinality_cov_r_out_v = len(cov(R_out, kg, v, pmap))
    uncov_r_out_v = uncov(R_out, kg, v, pmap)
    uncov_r_v = uncov(r, kg, v, pmap)
    cardinality_uncov_r_out_r_v = len(set.union(uncov_r_out_v, uncov_r_v))
    cardinality_uncov_r_out_v = len(uncov_r_out_v)
    # TODO check if still correct

    if not cardinality_cov_r_out_v:
    # if this is zero we know the beta part is zerro, the divisors will also be zero resulting in error, thus removing beta part altogether
            out = -alpha * ((len(cov_g(r, g, rule_dict) - cov_g(R_out, g, rule_dict)))/len(g))

    out = -alpha * ((len(cov_g(r, g, rule_dict) - cov_g(R_out, g, rule_dict)))/len(g)) + beta * ((cardinality_cov_r_out_v / cardinality_uncov_r_out_r_v) - (cardinality_cov_r_out_v / cardinality_uncov_r_out_v))

    print(cov_g(r, g, rule_dict))
    print(cov_g(R_out, g, rule_dict))
    print(len(g))
    print(cardinality_cov_r_out_v)
    print(cov(R_out, kg, v, pmap))
    print(cardinality_uncov_r_out_r_v)
    print(uncov(r, kg, v, pmap))
    print(cardinality_uncov_r_out_v)
    print(uncov(R_out, kg, v, pmap))
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

    #########
    # DEFINITION knot: graph entity with more than one triple --> each connection tuple represents one knot
    #########


    # iterate over atoms, fuse connection tuples that are connected by handled atoms
    for atom in r.body:

        # get all vars s and o are connected to
        s_c = next((c for c in con if atom[0] in c), None)
        o_c = next((c for c in con if atom[2] in c ), None)
        
        # atom isn't connected to body
        if not s_c and not o_c:
            return False
        
        if len(con) > 1:
            # fuse connections, if s_c and o_c are the same, nothing happens, no two knots are being connected...
            if s_c and o_c:
                if s_c != o_c:

                    # if it's a literal comparison "=" , s and o must be the same literal
                    if atom[1] == "=":
                        return False
                    con.remove(s_c)
                    con.remove(o_c)
                    con.add(tuple(set(s_c).union(set(o_c))))


    if len(con) != 1: 
    # all connected knots are fused --> there is am unconnected subgraph
        return False

    return True

def is_valid_comp(triple):
    if not is_literal_comp(triple[1]) or (literal_type(triple[0]) != literal_type(triple[2])):
        return False  
    # TODO maybe ensure s and o are object of same predicate
    
    if triple[1] == "=":
        if triple[0] != triple[2]:
            return False
    if triple[1] == "<":
        if triple[0] >= triple[2]:
            return False
        
    return True

# checks if an entity is allowed in a certain triple using ontology, for literal comparisons, is_valid_comp() is returned
def fits_domain_range(entity, triple, ontology:Ontology, kg:IncidenceList, pmap:P_map, type_predicate):
    # print("CALL")
    if entity not in triple:
        raise ValueError("Entity not in triple.")
    

    check_domain = False
    check_range = False
    literal = False

    if is_literal(entity):
        literal = True

    if literal and is_valid_comp(triple):
        return True
    if is_literal_comp(triple[1]):
        # it is a literal comp, but it is not valid as checked before
        return False
    

    if entity == triple[0]:
        if literal:
            # literal comparisons have been handled before, subject cannot be literal
            return False
        check_domain = True
    if entity == triple[2]:
        check_range = True

    
    
    original = pmap.original_pred(triple[1])

    if triple[1] in ontology.properties:
        domain_range = ontology.properties[triple[1]]
    elif original in ontology.properties:
        domain_range = ontology.properties[original]
    else:
        return False
        

    if literal:
        types_r = domain_range[1]
        literal_t = literal_type(entity)

        for t in types_r:
            if derivable(literal_t, t, ontology.literal_hierarchy):
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
def literal_type(l:str):
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
def is_literal(e:str):
    # TODO make this check better
    return e.__contains__("\"")
        
"""help function for fits_domain_range()
checks if literal_type can be derived from from t according to the Type hierachy provided."""
def derivable(literal_type, t, hierarchy):
    if literal_type == t:
        return True
    out = False

    if t in hierarchy:
        for st in hierarchy[t]:
            out = out or derivable(literal_type, st, hierarchy)
            if out:
                break


    return out



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
def getExamples(kg:IncidenceList, preds:set, count:int):
    out = set()
    eligible_preds = preds.copy()
    diff = count - len(out)


    # go through all predicates, get mean examples per predicate if possible
    # repeat with all predicates that still have unused instances left until count is met

    test = 0
    while len(out) < count and eligible_preds:
        max_i = int(diff/len(eligible_preds) + 1)  
        test += 1
        if test == 5:
            exit()
        eligible_preds_copy = eligible_preds.copy()
        for p in eligible_preds_copy:
            if not kg.edges.get(p):
                continue

            l = len(kg.edges.get(p)) 
            if l <= (max_i + 1):
                # if all instances of predicate will be used, remove
                eligible_preds.remove(p)
            
            # add even share of elements per predicate, if possible
            i = 0
            for n in kg.edges.get(p):
                if n not in out:
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
    # TODO is there a mistake, doesn't vanilla create new negative entity? here maybe thinking only predicate is negated
    preds = pmap.predicates
    out = set()
    eligible_preds = preds.copy()


    # TODO fix infinite loop
    loop_count = 0 

    # will hold all instances of target predicate, search from the connected entities
    eligible_edges = set()
    for p in preds:
        edges = kg.edges.get(p)
        if edges:
            eligible_edges.update(edges)

    diff = count - len(out)
    while len(out) < count and eligible_preds:
        print(f"LCWA while target {pmap.target}")
        max_i = int(diff /( 2 * len(eligible_preds)) + 1) 
        eligible_preds_copy = eligible_preds.copy()
        for p in eligible_preds_copy:
            if not kg.edges.get(p):
                continue
            l = len(kg.edges[p])
            if l <= (max_i):
                # if all instances of predicate will be used, remove
                eligible_preds.remove(p)

            i = 0
            for e in eligible_edges:
                # find object in neighbourhood that fits domain but doesnt have the relation with subject
                # n = (s, o) find s' and o' s.t. not exists p(s, o') and p(s', o)
                s = e[0]
                o = e[1]
                for f in eligible_edges:
                    # TODO ask if this is ok, recombining entities that have the relation, rather than combining one entity that has relation with one that may or may NOT have it
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

        # TODO remove after fix
        loop_count +=1
        if loop_count > 10:
            return out

        diff = count - len(out)
    for _ in range(-diff):
        out.pop()
    return out

"""get random pairs of entities that don't have target predicate"""
def getRandomNegExamples(kg:IncidenceList, preds:set, count:int, v=set()):
    ct = 1
    fact = 1

    # finding set size where |set X set| > count
    while fact <= count:
        ct+=1
        fact *= ct

    # this is somewhat arbitrary, goal is to remove some bias by having more entities in the set while managing computational work --> not going trhough all kg.nodes
    ct *= 2

    entities = []

    for e in kg.nodes:

        entities.append(e)
        ct += 1
        if ct >= count:
            break

    out = set()
    for i in range(count):
        pair = (random.choice(entities), random.choice(entities))
        if pair not in v:
            out.add(pair)
    return out