import json
import csv
import numpy as np
import warnings
from RuleMining.Util import *
from RuleMining.Classes import Path, Rule, P_map, IncidenceList, Ontology




def mine_rules(transformed_kg:IncidenceList, targets:set, transform_output_dir:str, ontology:Ontology, rules_file:str, prefix:str, max_depth:int=3, set_size:int=100, 
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

        # getting post normalization instances of target predicate and the negative instances from validation
        pmap = P_map(p, new_preds(p, predicate_mappings), set() , predicate_mappings, neg_predicate_mappings)
        pmap.neg_predicates = neg_preds(pmap.predicates, neg_predicate_mappings)

        print(f"creating input sets G and V for target predicate <{p}>...\n")
        # create positive examples
        g = getExamples(transformed_kg, pmap.predicates, set_size)
        len_g = len(g)
        if len_g < set_size:
            print(f"There aren't enough positive examples in the graph, proceeding with {len_g} examples.\n")  

        # first, get all constraint violating triples
        v = getExamples(transformed_kg, pmap.neg_predicates, set_size)

        # if not enough in v fill with lcwa-conform examples
        len_v = len(v)
        if len_v < set_size:
            print(f"{len_v} examples found from constraint violations, selecting remaining {set_size - len_v} examples from graph.\n")
            v.update(getExamplesLCWA(transformed_kg, ontology, pmap, set_size - len_v, type_predicate))

        # if not enough in v fill with random examples
        len_v = len(v)
        if len_v < set_size:
            print(f"There aren't enough negative examples in the graph, choosing {set_size - len_v} random examples.\n")  
            v.update(getRandomNegExamples(transformed_kg, pmap.predicates, set_size - len_v, v)) 


        len_v = len(v)
        if len_v < set_size:
            print(f"There aren't enough negative examples in the graph, proceeding with {len_v} examples.\n")   

        if not g:
            warnings.warn(f"There are no generation examples for {pmap.target}. No rule-mining possible \n", UserWarning)   
            return []    
        if not v:
            warnings.warn(f"There are no validation examples for {pmap.target}. No rule-mining possible \n", UserWarning)   
            return []

        
        print(f"mining rules for target predicate <{p}>...\n")
        result.extend(mine_rules_for_target_predicate(g, v, pmap, transformed_kg, prefix, type_predicate, ontology, max_depth))

    #TODO add result to csvs
    with open(rules_file, mode='w', newline='', encoding='utf-8') as datei:
        writer = csv.writer(datei)
        writer.writerows(result)

    return

def mine_rules_for_target_predicate(g:set, v:set, pmap:P_map, transformed_kg:IncidenceList, prefix:str, type_predicate:str, ontology:Ontology,  max_depth:int=3, alpha:float=0.5, beta:float=0.5):
    
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

    kg = transformed_kg

    R_out = []

    
    isGenre_g = {('Ten_Summoner%27s_Tales', 'Pop'), ('Dire_Straits(Album)', 'Rock'), ('Wild_West_End', 'Rock'), ('Rubber_Soul', 'Rock'), ('Making_Movies', 'Pop'), ('Outlandos_D%27Amour', 'Punk'), ('In_The_Gallery', 'Rock'), ('461_Ocean_Blvd.', 'Blues'), ('Water_Of_Love', 'Country'), ('Make_Beleive', 'Metal'), ('The_Beatles(Album)', 'Jazz'), ('It%27s_a_Feeling', 'Soul'), ('Regatta_De_Blanc', 'Reggae'), ('Let_It_Be', 'Pop'), ('Sultans_Of_Swing', 'Funk'), ('Lovers_in_the_Night', 'Country')}
    isGenre_v = {('Africa', 'Funk'), ('Toto_IV', 'Metal'), ('Making_Movies', 'Metal'), ('Ten_Summoner%27s_Tales', 'Rock'), ('Make_Beleive', 'Jazz'), ('Make_Beleive', 'Rock'), ('Africa', 'Soul'), ('Toto', 'Metal'), ('Make_Beleive', 'Funk'), ('Outlandos_D%27Amour', 'Metal'), ('Dire_Straits(Album)', 'Metal'), ('Africa', 'Jazz'), ('Let_It_Be', 'Metal'), ('Ten_Summoner%27s_Tales', 'Metal'), ('461_Ocean_Blvd.', 'Rock')}
    #valid rule
    r = Rule(head=("?VAR1","isGenre", "?VAR2"), 
             body={("?VAR3", "collaboratedWith", "?VAR4"), ("?VAR5", "hasAlbum", "?VAR6"), ("?VAR7", "isGenre", "?VAR8"), 
                   ("?VAR9", "hasAlbum", "?VAR10"), ("?VAR11", "releaseYear", "?VAR12"), ("?VAR13", "releaseYear", "?VAR14"), ("?VAR15", "<", "?VAR16")}, 
                   connections={("?VAR1", "?VAR6", "?VAR11"), ("?VAR2", "?VAR8"), ("?VAR5", "?VAR3"), ("?VAR4", "?VAR9"),("?VAR10", "?VAR7", "?VAR13"), ("?VAR12", "?VAR16"),("?VAR14", "?VAR15")}) 
    
# {
#   "KG": "musicKG",
#   "prefix": "http://example.org/",
#   "rules_file": "musicKG.csv",
#   "rdf_file": "musicKG.nt",
#   "constraints_folder": "musicKG",
#   "ontology_file": "musicKGOntology.ttl",
#   "pca_threshold": 0.75
# }


# {
#   "KG": "FrenchRoyalty",
#   "prefix": "http://FrenchRoyalty.org/",
#   "rules_file": "french_royalty.csv",
#   "rdf_file": "french_royalty.nt",
#   "constraints_folder": "FrenchRoyalty",
#   "ontology_file": "musicKGOntology.ttl",
#   "pca_threshold": 0.75
# }


    p1 = Path()
    p1.head = ("Ten_Summoner%27s_Tales","isGenre_Pop","Pop")
    p1.graph.add("Dire_Straits","hasAlbum_Making_Movies", "Making_Movies")
    p1.graph.add("Sting", "collaboratedWith_Dire_Straits", "Dire_Straits")
    p1.graph.add("Sting","hasAlbum_Ten_Summoner%27s_Tales","Ten_Summoner%27s_Tales")
    p1.graph.add("Making_Movies","isGenre_Pop","Pop")
    p1.graph.add("Ten_Summoner%27s_Tales","releaseYear_1993","\"1993\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    p1.graph.add("Making_Movies","releaseYear_1980","\"1980\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    p1.graph.add("\"1980\"^^<http://www.w3.org/2001/XMLSchema#/int>","<","\"1993\"^^<http://www.w3.org/2001/XMLSchema#/int>")
   # p1.graph.add("Shape_of_my_Heart","writer_Sting","Sting")

    p2 = Path()
    p2.head = ("I_Shot_the_Sheriff","isGenre_Rock","Rock")
    #p2.graph.add("Here_Comes_the_Sun","releaseYear_1969","\"1969\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    #p2.graph.add("461_Ocean_Blvd.","releaseYear_1974","\"1974\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    #p2.graph.add("\"1969\"^^<http://www.w3.org/2001/XMLSchema#/int>","<","\"1974\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    p2.graph.add("I_Shot_the_Sheriff","includedIn_461_Ocean_Blvd.","461_Ocean_Blvd.")
    p2.graph.add("461_Ocean_Blvd.","isGenre_Rock","Rock")

    print(p1)
    print(p2)
    r1 = p1.rule(pmap)

    r2 = p2.rule(pmap)

    r3 = Rule(
        head=('?VAR1', 'isGenre', '?VAR2'),
        body={('?VAR9', 'isGenre', '?VAR10'), ('?VAR15', 'releaseYear', '?VAR16'), ('?VAR3', 'hasAlbum', '?VAR4')},
        connections={('?VAR4', '?VAR1', '?VAR15'), ('?VAR10', '?VAR2')})


    if pmap.target == "isGenre":
        rule_dict = {}
        rule_dict[p1.rule(pmap)] = set()
        rule_dict[p2.rule(pmap)] = set()
        rule_dict[r3] = set()
        R_out = [r1,r2]
        #print(v)
        for egg in isGenre_g:
            eg = Path(head=(egg[0], pmap.target, egg[1]))
            if covers(r1, kg, egg, pmap):
                rule_dict[r1].add(eg)
            if covers(r2, kg, egg, pmap):
                rule_dict[r2].add(eg)
            if covers(r3, kg, egg, pmap):
                rule_dict[r3].add(eg)
        print(est_m_weight(r3, R_out, rule_dict, kg, isGenre_g, isGenre_v, alpha, beta, pmap))
        print(cov(r2, kg, isGenre_v, pmap))

        exit()

    # ('Outlandos_D%27Amour', 'Punk') ('461_Ocean_Blvd.', 'Blues'), ('Regatta_De_Blanc', 'Reggae')
    # {('Let_It_Be', 'Pop'), ('Dire_Straits(Album)', 'Rock'), ('Rubber_Soul', 'Rock'), ('The_Beatles(Album)', 'Jazz'), ('Ten_Summoner%27s_Tales', 'Pop'), ('Making_Movies', 'Pop')}


    # #boolean that marks if R_out has changed since the last calculation of marginal weight
    # R_out_changed = False

    # #TODO Nf in RuDiK
    # frontiers = {t[0] for t in g}


    # #TODO potential (sub)rules (Qr in RuDiK)
    # candidates = expand_ft(frontiers, kg, g)


    # # find most promising (sub)rule, the one with the lowest marginal weight
    # for rule in candidates:
    #     continue


    # # main loop
    # while candidates and r.cur_emw < 0 and len(cov(R_out, kg, g)) < len(g):
        
    #     candidates = candidates.remove(r)

    #     # if r is a valid rule, add it to solution
    #     if is_valid(r):
    #         R_out.append(r)
    #         R_out_changed = True

    #     # if r is not a valid rule, expand on it
    #     else:
    #         #expand r
    #         if len(r.body) < max_depth:
    #             #the last visited nodes in all search paths that correspond to r
    #             frontiers = ft(r)
    #             new_rules = expand_ft(frontiers, kg, g)
    #             candidates.append(new_rules)

    #     # find new r
    #     if R_out_changed:
    #         r.cur_emw = est_m_weight(r, R_out, kg, g, v, alpha, beta)
    #         for rule in candidates:
    #             continue

    #     else:
    #         for new_rule in new_rules:
    #             continue




    #     R_out_changed = False

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










