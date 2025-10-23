from rdflib import Graph, URIRef, BNode, Literal, Namespace
import json
import csv
import numpy as np
import warnings


class Path:
    b:str
    path:list[str]

class Rule:
    cur_m_weight: float
    paths:list[Path]
    body: list[tuple[str]]


def original_pred(new_pred:str, predicate_mappings:dict):
    if new_pred in predicate_mappings:
        return predicate_mappings[new_pred]
    return ""

def new_preds(original_pred:str, predicate_mappings:dict):
    return {k for k, v in predicate_mappings.items() if v == original_pred}

def neg_preds(new_preds:dict, neg_predicate_mappings:dict):
    return {k for k, v in neg_predicate_mappings.items() if v in new_preds}


def mine_rules(transformed_kg:Graph, targets:set, transform_output_dir:str, ontology_path:str, rules_file:str, prefix:str, max_depth:int=3, set_size:int=100, 
               alpha:float=0.5, type_predicate:str="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"):
    """
    Mines rules for all original predicates of a normalized knowledge graph.
    
    Iterates over the original predicates, forming genereation and validation set for each.
    Then calls rule mining method for each predicate.

    Args:
        transformed_kg -- knowledge graph to mine rules for
        targets -- list of target predicates from the original kg to mine for
        transform_output_dir -- directory of normalization/validation result containing predicate mappings
        ontology_path -- path to given ontology
        prefix -- prefix
        max_depth -- max length of paths in graph corresponding to rule length
        set_size -- number of elements in G and V

    Returns:
        no return
        (but: produces a .csv file containing the mined rules)
    """

    if alpha > 1:
        warnings.warn(f"alpha must be in [0,1], switching to default value of 0.5.", UserWarning)
        alpha = 0.5
    beta = 1 - alpha

    print(f"computed beta as {beta}.\n")
    print(f"using <{type_predicate}> as type predicate.\n")

    # load predicate mappings
    with open(f"{transform_output_dir}/predicate_mappings.json", "r", encoding="utf-8") as p_map_file:
        predicate_mappings = json.load(p_map_file)
    with open(f"{transform_output_dir}/no_predicate_mappings.json", "r", encoding="utf-8") as np_map_file:
        neg_predicate_mappings = json.load(np_map_file)
    result = []


    for p in targets:
        print(f"creating input sets G and V for target predicate <{p}>...\n")

        # getting post normalization instances of target predicate and the negative instances from validation
        predicates = new_preds(p, predicate_mappings)
        neg_predicates = neg_preds(predicates, neg_predicate_mappings)


        # create positive examples
        filter_p = "||".join(f"?p = <{pred}>" for pred in predicates)
        g = []

        #TODO randomization needed but order by rand is too expensive
        query_g = f""" SELECT ?s ?o
                    WHERE {{
                    ?s ?p ?o .
                    FILTER ({filter_p})
                    }}
                    LIMIT {set_size}"""

        for row in transformed_kg.query(query_g):
            g.append(row)
            
        len_g = len(g)
        if len_g < set_size:
            warnings.warn(f"There aren't enough positive examples in the graph, proceeding with {len_g} examples.\n", UserWarning)        #create negative examples

        # TODO: maybe enable custom input for extra negative examples
        #create negative examples
        # first, get all constraint violating pairs

        filter_np = "||".join(f"?p = <{pred}>" for pred in neg_predicates)

        v = []
        if filter_np:
            query_v = f""" SELECT ?s ?o
                        WHERE {{
                        ?s ?p ?o .
                        FILTER ({filter_np})
                        }}
                        LIMIT {set_size}"""
        
            for row in transformed_kg.query(query_v):
                v.append(row)

        len_v = len(v)
        if len_v < set_size:
            warnings.warn(f"{len_v} examples found from constraint violations, selecting remaining {set_size - len_v} examples from graph.\n", UserWarning)
            # TODO incorporate LCWA --> negative examples must have the target predicate with other entities   
            if filter_np:
                not_filter = f"{filter_np} || {filter_p}"
                not_filter = not_filter.replace("=", "!=")
            else: 
                not_filter = filter_p.replace("=", "!=")
            # TODO if not enough add more random v-entries, maybe: allow custom input 
            query_v_fill = f""" SELECT ?s ?o
                            WHERE {{
                            ?s ?p ?o .
                            FILTER ({not_filter})
                            }}
                            LIMIT {set_size - len_v}"""
            
            for row in transformed_kg.query(query_v_fill):
                v.append(row)

        len_v = len(v)
        if len_v < set_size:
            warnings.warn(f"There aren't enough negative examples in the graph, proceeding with {len_v} examples.\n", UserWarning)   



        print(f"mining rules for target predicate <{p}>...\n")
        result.extend(mine_rules_for_target_predicate(np.array(g), np.array(v), p, predicates, neg_predicates, predicate_mappings, neg_predicate_mappings, g, transformed_kg, prefix, type_predicate, ontology_path, max_depth))

        print(f"----------result--------------\n{result}\n--------------------------------------\n")

    #TODO add result to csvs
    with open(rules_file, mode='w', newline='', encoding='utf-8') as datei:
        writer = csv.writer(datei)
        writer.writerows(result)

    return

def mine_rules_for_target_predicate(g:np.array, v:np.array, target:str, predicates:set, neg_predicates:set, predicate_mappings:dict, neg_predicate_mappings:dict,
                                    transformed_kg:Graph, prefix:str, type_predicate:str, ontology_path:str,  max_depth:int=3, alpha:float=0.5, beta:float=0.5):
    
    """
    Args:
        G -- generation set
        V -- validation set
        predicates -- all post normalization versions of the original predicates rules are mined for
        neg_predicates -- all post normalization negative versions of the original predicates rules are mined for
        predicate_mappings -- mapping of 
        transformed_kg -- knowledge graph to mine rules for
        ontology_path -- path to given ontology
        prefix -- prefix
        max_depth -- max length of paths in graph corresponding to rule length

    Returns:
        R_out -- mined rules for the target predicate
    """
    head = ("?a", target, "?b")
    kg = transformed_kg

    R_out = [Rule]

    #stores weight of R_out
    R_out_weight = -1.0

    #boolean that marks if R_out has changed since the last calculation of marginal weight
    R_out_changed = False

    #TODO Nf in RuDiK
    frontiers = {t[0] for t in g}


    #TODO potential (sub)rules (Qr in RuDiK)
    candidates = expand_ft(frontiers, kg, g)

    r = Rule()
    r.cur_m_weight = 2.0
    r.paths = [("","","")]
    r.body = [("?a","http://example.org/isGenre","?b")]
    print(f"----------g--------------\n{g}\n--------------------------------------\n")
    print(f"----------r--------------\n{r.body}\n--------------------------------------\n")
    #print(f"----------cov--------------\n{cov([r], kg, g)}\n--------------------------------------\n")




    # find most promising (sub)rule, the one with the lowest marginal weight
    for rule in candidates:
        rule.cur_m_weight = est_m_weight(rule, R_out, kg, g, v, alpha, beta, R_out_weight)
        if rule.cur_m_weight < r.cur_m_weight:
            r.cur_m_weight = rule.cur_m_weight
            r = rule


    # main loop
    while candidates and r.cur_m_weight < 0 and cov_cardinality(R_out, kg, g):
        
        candidates = candidates.remove(r)

        # if r is a valid rule, add it to solution
        if is_valid(r):
            R_out.append(r)
            R_out_changed = True

        # if r is not a valid rule, expand on it
        else:
            #expand r
            if len(r.body) < max_depth:
                #the last visited nodes in all search paths that correspond to r
                frontiers = ft(r)
                new_rules = expand_ft(frontiers, kg, g)
                candidates.append(new_rules)


        if R_out_changed:
            # TODO add mweight to head of each rule list
            r.cur_m_weight, R_out_weight = est_m_weight(r, R_out, kg, g, v, alpha, beta)
            for rule in candidates:
                rule.cur_m_weight = est_m_weight(rule, R_out, kg, g, v, alpha, beta)
                if rule.cur_m_weight < r.cur_m_weight:
                    r.cur_m_weight = rule.cur_m_weight
                    r = rule

        else:
            for new_rule in new_rules:
                if est_m_weight(new_rule, R_out, kg, g, v, alpha, beta) < est_m_weight(r, R_out, kg, g, v, alpha, beta):
                    r = new_rule




        R_out_changed = False

    #TODO rudik
    return R_out



#TODO check if a (sub)rule is a valid rule
def is_valid(r:Rule):
    len_r = len(r.body)

    if r.body[len_r-1][2] != "?b" or r.body[0][0] != "?a":
        return False

    #atoms must be transitively connected
    for i in range(len_r-1):
        if r.body[i][2] != r.body[i+1][0]:
            return False
    

    return True

#TODO help function check type using ontology
def fits_domain_range():
    return

#TODO help function expand_frontiers(list of current nodes)
def expand_ft(frontiers:set, kg:Graph, g:np.ndarray):
    # get all frontier nodes of the rule and edges


    # return rules generated by this


    return {}

#TODO calc frontiers of r
def ft(r:Rule):
    return {p[len(p)-1][2] for p in r.paths}






# estimated marginal weight
def est_m_weight(r:Rule, R_out:list[Rule], kg:Graph, g:set, v:set, alpha:float, beta:float):
    cov_r_out_v = cov(R_out, kg, v)
    print(f"------------Rout-----------{R_out}---------------")
    print(f"------------Rr-----------{R_out.append(r)}---------------")
    print(f"------------r-----------{r.body}---------------")

    return -alpha * (len(cov([r], kg, g) - cov(R_out, kg, g))/len(g)) + beta * (cov_r_out_v / uncov(R_out.append(r), kg, v) - cov_r_out_v / uncov(R_out, kg, v))

# covarage of rules over set
def cov(rules:list[Rule], kg:Graph, ex_set:set):
    c = set()

    filter = "||".join(f"(?a = <{ex[0]}> && ?b = <{ex[1]}>)" for ex in ex_set)

    rules_q = "UNION".join(f"{{{r_sparql(r)}}}" for r in rules)

    query = f""" SELECT ?a ?b
                WHERE{{
                {rules_q}
                FILTER({filter})
                }}
                """
    
    for row in kg.query(query):
        c.add(row)

    return c

# unbounded coverage of rules over set
def uncov(rules:list[Rule], kg:Graph, ex_set:set):
    print(f"------------rules-----------{rules}---------------")
    rules = {unbind(r) for r in rules}
    return cov(kg, ex_set, rules)

# marginal weight of a (sub)rule
# allows for of weight(R_out) to avoid unnessecary commputation
def m_weight(r:Rule, R_out:list[Rule], kg:Graph, g:set, v:set, alpha:float, beta:float, R_out_weight:float=-1.0):
    if R_out_weight < 0:
        R_out_weight = weight(R_out, kg, g, v, alpha, beta)
    return weight(R_out.append(r), kg, g, v, alpha, beta) - R_out_weight, R_out_weight

# weight of a set of rules
def weight(rules:list[Rule], kg:Graph, g:set, v:set, alpha:float, beta:float):
    return alpha * (cov_cardinality(rules, kg, g)/ len(g)) + beta * (cov_cardinality(rules, kg, v)/uncov_cardinality(rules, kg, v))
    
# returns the cardinality of the coverage 
def cov_cardinality(rules:list[Rule], kg:Graph, set:set):

    filter = "||".join(f"(?a = <{pred[0]}> && ?b = <{pred[1]}>)" for pred in set)

    rules_q = "UNION".join(f"{{{r_sparql(r)}}}" for r in rules)

    query = f""" SELECT (COUNT(*) AS ?count)
                WHERE{{
                {rules_q}
                FILTER({filter})
                }}
                """
    
    for row in kg.query(query):
        i = row[0]

    return i

# format a rule for WHERE-bracket of a sparql query
def r_sparql(r:Rule):
    return " ".join(f"{t[0]} <{t[1]}> {t[2]} ." for t in r.body)

# returns the cardinality of the unbounded coverage 
def uncov_cardinality(rules:list[Rule], kg:Graph, set:set):
    rules = {unbind(r) for r in rules}
    return cov_cardinality(kg, set, rules)

# unbinds a rule body
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




