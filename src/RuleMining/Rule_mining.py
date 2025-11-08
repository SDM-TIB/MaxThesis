import json
import csv
import numpy as np
import warnings
from RuleMining.Util import *
from RuleMining.Classes import Path, Rule, P_map, IncidenceList, Ontology




def mine_rules(transformed_kg:IncidenceList, targets:set, transform_output_dir:str, o:Ontology, rules_file:str, prefix:str, max_depth:int=3, set_size:int=100, 
               alpha:float=0.5, type_predicate:str='http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
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

    if alpha > 1 or alpha < 0:
        raise ValueError("alpha must be in [0,1].")
    beta = 1 - alpha
    print(f"computed beta as {beta}.\n")
    print(f"using <{type_predicate}> as type predicate.\n")

    if type_predicate in targets:
        targets.remove(type_predicate)

    # load predicate mappings 
    with open(f"{transform_output_dir}/predicate_mappings.json", "r", encoding="utf-8") as p_map_file:
        predicate_mappings = json.load(p_map_file)
    with open(f"{transform_output_dir}/no_predicate_mappings.json", "r", encoding="utf-8") as np_map_file:
        neg_predicate_mappings = json.load(np_map_file)
    result = []


    for p in targets:
        print(f"creating input sets G and V for target predicate <{p}>...\n")

        # getting post normalization instances of target predicate and the negative instances from validation
        pmap = P_map(p, new_preds(p, predicate_mappings), set() , predicate_mappings, neg_predicate_mappings)
        pmap.neg_predicates = neg_preds(pmap.predicates, neg_predicate_mappings)

        # create positive examples
        g = getExamples(transformed_kg, pmap.predicates, set_size)
        len_g = len(g)
        if len_g < set_size:
            warnings.warn(f"There aren't enough positive examples in the graph, proceeding with {len_g} examples.\n", UserWarning)  

        # TODO: maybe enable custom input for extra negative examples
        # TODO create negative examples
        # first, get all constraint violating triples

        v = getExamples(transformed_kg, pmap.neg_predicates, set_size)
        len_v = len(v)
        if len_v < set_size:
            warnings.warn(f"{len_v} examples found from constraint violations, selecting remaining {set_size - len_v} examples from graph.\n", UserWarning)
            # TODO incorporate LCWA --> negative examples must have the target predicate with other entities   

            # TODO if not enough add more random v-entries, maybe: allow custom input 


        len_v = len(v)
        if len_v < set_size:
            warnings.warn(f"There aren't enough negative examples in the graph, proceeding with {len_v} examples.\n", UserWarning)   


        
        print(f"mining rules for target predicate <{p}>...\n")
        result.extend(mine_rules_for_target_predicate(g, v, pmap, g, transformed_kg, prefix, type_predicate, o, max_depth))

    #TODO add result to csvs
    with open(rules_file, mode='w', newline='', encoding='utf-8') as datei:
        writer = csv.writer(datei)
        writer.writerows(result)

    return

def mine_rules_for_target_predicate(g:set, v:set, p:P_map, transformed_kg:IncidenceList, prefix:str, type_predicate:str, o:Ontology,  max_depth:int=3, alpha:float=0.5, beta:float=0.5):
    
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
    # TODO uncomment
    # assert g, "missing genreration exmples"
    # assert v, "missing validation examples"

    kg = transformed_kg

    R_out = []
    r = Rule(head=("a","p1" "b"), body={("d", "e", "f")}, connections={("a", "d"), ("b", "f")})    

    p1 = Path()
    p1.head = ("Shape of my Heart","isGenre","Pop")
    p1.graph.add("Dire Straits","hasAlbum", "Communique")
    p1.graph.add("Lady Writer", "includedIn", "Communique")
    p1.graph.add("Sting", "collaboratedWith", "Dire Straits")
    p1.graph.add("Sting","hasAlbum","Fields of Gold(Album)")
    p1.graph.add("Shape of my Heart","includedIn","Fields of Gold(Album)")
    p1.graph.add("Shape of my Heart","isGenre","Pop")
    p1.graph.add("Shape of my Heart","writer","Sting")

    p2 = Path()
    p2.head = ("I Shot the Sheriff","isGenre","Rock")
    p2.graph.add("Here Comes the Sun","includedIn","Abbey Road")
    p2.graph.add("I Shot the Sheriff","includedIn","461 Ocean Blvd.")
    p2.graph.add("Eric Clapton","collaboratedWith","The Beatles")
    p2.graph.add("I Shot the Sheriff","isGenre","Rock")
    p2.graph.add("The Beatles","hasAlbum","Abbey Road")
    p2.graph.add("Eric Clapton","hasAlbum","461 Ocean Blvd.")

    print(p1)
    print(p2)
    r1 = p1.rule()

    r2 = p2.rule()



    print(r1._Rule__key() == r2._Rule__key())
    print(r2)
    print(is_valid(r2))


    exit()

    d = {}
    d[r] = 5

    #boolean that marks if R_out has changed since the last calculation of marginal weight
    R_out_changed = False

    #TODO Nf in RuDiK
    frontiers = {t[0] for t in g}


    #TODO potential (sub)rules (Qr in RuDiK)
    candidates = expand_ft(frontiers, kg, g)


    # find most promising (sub)rule, the one with the lowest marginal weight
    for rule in candidates:
        continue


    # main loop
    while candidates and r.cur_emw < 0 and len(cov(R_out, kg, g)) < len(g):
        
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

        # find new r
        if R_out_changed:
            r.cur_emw = est_m_weight(r, R_out, kg, g, v, alpha, beta)
            for rule in candidates:
                continue

        else:
            for new_rule in new_rules:
                continue




        R_out_changed = False

    #TODO rudik
    return R_out

#TODO help function expand_frontiers(list of current nodes)
def expand_ft(frontiers:set, kg, g:np.ndarray):
    # get all frontier nodes of the rule and edges


    # return rules generated by this


    return {}

#TODO calc frontiers of r
def ft(r:Rule):
    return










