import numpy as np
from RuleMining.Classes import Path, Rule, P_map, IncidenceList, Ontology

########################################
# filling custom datastructures
########################################

"""parse a graph from nt file into IncidenceList"""
def parseGraph(ntFilePath, graph:IncidenceList, prefix=""):
    with open(ntFilePath, 'r', encoding='utf-8') as file:
        for row in file:
            triple = tripleRemovePrefix(row.split()[0:3], prefix)
            graph.add(triple[1], triple[0], triple[2])

"""parse a .ttl ontology into Ontology Type"""
def parseOntology(ontology_file:str, ontology:Ontology, prefix:str=""):
    with open(ontology_file, 'r', encoding='utf-8') as file:
        block_end = False
        block = []
        for row in file:
            r = row.split()
            if r:
                if r[0][0] == "@" or r[0][0] == "#":
                   continue

                for e in r:
                    if e == ".":
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
def checkForClass(e):
    return e.__contains__("Class")

"""help function for parseOntology"""
def checkForSubClass(e):
    return e.__contains__("subClassOf")

"""help function for parseOntology"""
def checkForProperty(e):
    return e.__contains__("Property")

"""help function for parseOntology"""
def checkForRange(e):
    return e.__contains__("range")

"""help function for parseOntology"""
def checkForDomain(e):
    return e.__contains__("domain")

"""help function to parseOntology"""
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
def addOntologyBlock(block:list[str], ontology, prefix):
    s, p, o = block[0:3]
    if checkForType(p):
        if checkForClass(o):
            foundSC = False
            ontology.addClass(prefix, s)
            for next_i in range(3, len(block)):
                if checkForSubClass(block[next_i]):
                    i = 1
                    # add all objects given for subClassOf
                    while True:
                        ontology.addClass(prefix, s, extractName(block[next_i + i]))
                        i += 1
                        if not block[next_i + i][len(block[next_i + i])-1] == ",":
                            break

        if o:
            d, r = set(), set()
            for next_i in range(3, len(block)-1):
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
                    # add all objects given for domain
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
    return cov(kg, ex_set, rules)


"""
unbinds a rule body
"""
def unbind(r:Rule):
    newvar = 99
    for atom in r.body:
        #remove if no target vars in atom
        # TODO
        #if one var is non target, replace with unique name
        pass
    return r

"""
check if a (sub)rule is a valid rule
"""
def is_valid(r:Rule):
    len_r = len(r.body)

    # must connect head entities
    #TODO

    #atoms must be transitively connected

    return True


#TODO help function check type using ontology
def fits_domain_range():
    return






###################################
# predicate mappings
###################################

"""
 get a predicates predecessor, for a negative_pred get post-normalization positive predicate, for that, get original predicate
"""
def original_pred(new_pred:str, predicate_mappings:dict):
    if new_pred in predicate_mappings:
        return predicate_mappings[new_pred]
    return ""


"""
get post normalization predicates from their pre-normalization predecessor
"""
def new_preds(original_pred:str, predicate_mappings:dict):
    return {k for k, v in predicate_mappings.items() if v == original_pred}


"""
get existing negative variants of post-normalization predicates
"""
def neg_preds(new_preds:dict, neg_predicate_mappings:dict):
    return {k for k, v in neg_predicate_mappings.items() if v in new_preds}



#########################################
# example generation
#########################################

"""get distributed examples for given predicates, limited by count"""
def getExamples(kg:IncidenceList, preds:set, count:int):
    out = set()
    eligible_preds = preds.copy()
    diff = count - len(out)

    while len(out) < count and eligible_preds:
        max_i = int(diff/len(eligible_preds) + 1)  

        eligible_preds_copy = eligible_preds.copy()
        for p in eligible_preds_copy:
            l = len(kg.edges[p])
            if l <= (max_i + 1):
                eligible_preds.remove(p)
            
            # add even share of elements per predicate
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
def getExamplesLCWA(kg:IncidenceList, preds:set, count:int):
    out = set()
    eligible_preds = preds.copy()
    diff = count - len(out)

    while len(out) < count and eligible_preds:
        max_i = int(diff/len(eligible_preds) + 1)  

        eligible_preds_copy = eligible_preds.copy()
        for p in eligible_preds_copy:

            
            i = 0
            for n in kg.edges[p]:

                # TODO find object in neighbourhood that fits domain but doesnt have the relation with subject

                i += 1
                if i > max_i:
                    break
                
        diff = count - len(out)

    for _ in range(-diff):
        out.pop()
    return out

