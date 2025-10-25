from rdflib import Graph, URIRef, BNode, Literal, Namespace
import numpy as np
from Classes import Path, Rule, P_map





"""
estimated marginal weight
"""
def est_m_weight(r:Rule, R_out:list[Rule], kg:Graph, g:set, v:set, alpha:float, beta:float):
    cov_r_out_v = cov(R_out, kg, v)

    return -alpha * (len(cov([r], kg, g) - cov(R_out, kg, g))/len(g)) + beta * (cov_r_out_v / uncov(R_out.append(r), kg, v) - cov_r_out_v / uncov(R_out, kg, v))


"""
covarage of rules over set
"""
def cov(rules:list[Rule], kg:Graph, ex_set:set):
    return 


"""
unbounded coverage of rules over set
"""
def uncov(rules:list[Rule], kg:Graph, ex_set:set):
    rules = {unbind(r) for r in rules}
    return cov(kg, ex_set, rules)



"""
unbinds a rule body
"""
def unbind(r:Rule):
    newvar = 99
    for atom in r.body:
        #remove if no target vars in atom
        if atom[0] != "?a" and atom[0] != "?b" and atom[2] != "?a" and atom[2] != "?b":
            r.body.remove(atom)
        #if one var is non target, replace with unique name
        elif atom[0] != "?a" and atom[0] != "?b":
            atom[0] = f"?{chr(newvar)}"
            newvar += 1
        elif atom[2] != "?a" and atom[2] != "?b":
            atom[2] = f"?{chr(newvar)}"
            newvar += 1
    return r


"""
check if a (sub)rule is a valid rule
"""
def is_valid(r:Rule):
    len_r = len(r.body)

    # must connect head entities


    #atoms must be transitively connected

    return True

#TODO help function check type using ontology
def fits_domain_range():
    return


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
