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

    
    isGenre_g = {('Ten_Summoner%27s_Tales', 'Pop'), ('Dire_Straits(Album)', 'Rock'), ('Rubber_Soul', 'Rock'), ('Making_Movies', 'Pop')}#, ('Outlandos_D%27Amour', 'Punk'), ('In_The_Gallery', 'Rock'), ('461_Ocean_Blvd.', 'Blues'), ('Water_Of_Love', 'Country'), ('Make_Beleive', 'Metal'), ('The_Beatles(Album)', 'Jazz'), ('It%27s_a_Feeling', 'Soul'), ('Regatta_De_Blanc', 'Reggae'), ('Let_It_Be', 'Pop'), ('Sultans_Of_Swing', 'Funk'), ('Lovers_in_the_Night', 'Country')}
    print(isGenre_g)
    #valid rule
    r = Rule(head=("?VAR1","isGenre", "?VAR2"), 
             body={("?VAR3", "collaboratedWith", "?VAR4"), ("?VAR5", "hasAlbum", "?VAR6"), ("?VAR7", "isGenre", "?VAR8"), 
                   ("?VAR9", "hasAlbum", "?VAR10"), ("?VAR11", "releaseYear", "?VAR12")}, 
                   connections={("?VAR1", "?VAR6", "?VAR11"), ("?VAR2", "?VAR8"), ("?VAR5", "?VAR3"), ("?VAR4", "?VAR9"),("?VAR10", "?VAR7")}) 
    if False and pmap.target == "isGenre":
        print(is_valid(r))
        print(cov(r,kg,isGenre_g, pmap))
        print(instantiable(r, kg,pmap,{}))
        exit()
    d = {}
    d[r] = 5





    p1 = Path()
    p1.head = ("Shape_of_my_Heart","isGenre_Pop","Pop")
    p1.graph.add("Dire_Straits","hasAlbum_Making_Movies", "Making_Movies")
    p1.graph.add("Solid_Rock", "includedIn_Making_Movies", "Making_Movies")
    p1.graph.add("Sting", "collaboratedWith_Dire_Straits", "Dire_Straits")
    p1.graph.add("Sting","hasAlbum_Ten_Summoner%27s_Tales","Ten_Summoner%27s_Tales")
    p1.graph.add("Shape_of_my_Heart","includedIn_Ten_Summoner%27s_Tales","Ten_Summoner%27s_Tales")
    p1.graph.add("Shape_of_my_Heart","isGenre_Pop","Pop")
    p1.graph.add("Making_Movies","isGenre_Pop","Pop")
    p1.graph.add("Pop","=","Pop")
    p1.graph.add("Ten_Summoner%27s_Tales","releaseYear_1993","\"1993\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    p1.graph.add("Making_Movies.","releaseYear_1980","\"1980\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    p1.graph.add("\"1993\"^^<http://www.w3.org/2001/XMLSchema#/int>","<","\"1980\"^^<http://www.w3.org/2001/XMLSchema#/int>")
   # p1.graph.add("Shape_of_my_Heart","writer_Sting","Sting")

    p2 = Path()
    p2.head = ("I_Shot_the_Sheriff","isGenre_Rock","Rock")
    p2.graph.add("Here_Comes_the_Sun","includedIn_Abbey_Road","Abbey_Road")
    #p2.graph.add("Here_Comes_the_Sun","releaseYear_1969","\"1969\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    #p2.graph.add("461_Ocean_Blvd.","releaseYear_1974","\"1974\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    #p2.graph.add("\"1969\"^^<http://www.w3.org/2001/XMLSchema#/int>","<","\"1974\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    p2.graph.add("I_Shot_the_Sheriff","includedIn_461_Ocean_Blvd.","461_Ocean_Blvd.")
    p2.graph.add("Eric_Clapton","collaboratedWith_The_Beatles","The_Beatles")
    p2.graph.add("Here_Comes_the_Sun","isGenre_Rock","Rock")
    p2.graph.add("The_Beatles","hasAlbum_Abbey_Road","Abbey_Road")
    p2.graph.add("Eric_Clapton","hasAlbum_461_Ocean_Blvd.","461_Ocean_Blvd.")

    print(p1)
    print(p2)
    r1 = p1.rule(pmap)

    r2 = p2.rule(pmap)



    print(r1._Rule__key() == r2._Rule__key())
    print(r1)
    print(r2)
    print(is_valid(r1))
    print(is_valid(r2))
    print(ontology)
    print(fits_domain_range("\"1969\"", ("\"1969\"","=","\"1969\""), ontology, kg, pmap, type_predicate))

    exit()





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










