import json
import csv
import numpy as np
import warnings
from RuleMining.Util import *
from RuleMining.Classes import Path, Rule, P_map, IncidenceList, Ontology




def mine_rules(transformed_kg:IncidenceList, targets:set, transform_output_dir:str, ontology:Ontology, rules_file:str, prefix:str, max_depth:int=3, set_size:int=100, 
               alpha:float=0.5, type_predicate:str='http://www.w3.org/1999/02/22-rdf-syntax-ns#type', rule_type:str="rudik"):
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

    expand_fun = None
    fits_max_depth = None



    # TODO if clauses for other rule types
    if rule_type == "rudik":
        expand_fun = expand_path_rudik
        fits_max_depth = fits_max_depth_rudik

    if not expand_fun or not fits_max_depth:
        raise ValueError("parameter rule_type must be one of the following strings: \"rudik\". If not spedified, it defaults to \"rudik\".")


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

        # first, get constraint violating triples
        v = getNegExamples(transformed_kg, pmap.neg_predicates, set_size)

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
            continue  
        if not v:
            warnings.warn(f"There are no validation examples for {pmap.target}. No rule-mining possible \n", UserWarning)   
            continue

        
        print(f"mining rules for target predicate <{p}>...\n")
        result.extend(mine_rules_for_target_predicate(g, v, pmap, transformed_kg, prefix, type_predicate, ontology, expand_fun, fits_max_depth, max_depth, alpha, beta))

        # if p == "isGenre":
        #     isGenre_g = {('Dire_Straits(Album)', 'isGenre_Rock', 'Rock'), ('Let_It_Be', 'isGenre_Rock', 'Rock'), ('Rosanna', 'isGenre_Rock', 'Rock'), ('Regatta_De_Blanc', 'isGenre_Reggae', 'Reggae'), ('Outlandos_D%27Amour', 'isGenre_Punk', 'Punk'), ('The_Beatles(Album)', 'isGenre_Jazz', 'Jazz'), ('In_The_Gallery', 'isGenre_Rock', 'Rock'), ('Lions', 'isGenre_Rock', 'Rock'), ('Africa', 'isGenre_Rock', 'Rock'), ('Shape_of_my_Heart', 'isGenre_Pop', 'Pop'), ('Let_It_Be', 'isGenre_Pop', 'Pop'), ('Making_Movies', 'isGenre_Pop', 'Pop'), ('461_Ocean_Blvd.', 'isGenre_Blues', 'Blues'), ('Ten_Summoner%27s_Tales', 'isGenre_Pop', 'Pop'), ('Down_To_The_Waterline', 'isGenre_Rock', 'Rock')}
        #     isGenre_v = {('Sultans_Of_Swing', 'NONONOFunk'), ('Make_Believe', 'NONONOMetal'), ('Water_Of_Love', 'NONONOCountry'), ('Outlandos_D%27Amour', 'Pop'), ('The_Seventh_One', 'Jazz'), ('The_Beatles(Album)', 'Rock'), ('It%27s_a_Feeling', 'NONONOSoul'), ('Outlandos_D%27Amour', 'Jazz'), ('Lovers_in_the_Night', 'NONONOCountry'), ('The_Seventh_One', 'Pop'), ('The_Seventh_One', 'Reggae'), ('Regatta_De_Blanc', 'Jazz'), ('Making_Movies', 'Reggae'), ('461_Ocean_Blvd.', 'Rock'), ('Ten_Summoner%27s_Tales', 'Rock')}
        #     result.extend(mine_rules_for_target_predicate(isGenre_g, isGenre_v, pmap, transformed_kg, prefix, type_predicate, ontology, max_depth))
            

    print(result)
    #TODO add result to csvs
    with open(rules_file, mode='w', newline='', encoding='utf-8') as datei:
        writer = csv.writer(datei)
        writer.writerows(result)

    print(type(expand_fun))
    return

def mine_rules_for_target_predicate(g:set, v:set, pmap:P_map, kg:IncidenceList, prefix:str, type_predicate:str, ontology:Ontology, expand_fun, fits_max_depth,  max_depth:int=3, alpha:float=0.5, beta:float=0.5):
    
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


    

    
    # isGenre_g = {('Dire_Straits(Album)', 'isGenre_Rock', 'Rock'), ('Let_It_Be', 'isGenre_Rock', 'Rock'), ('Rosanna', 'isGenre_Rock', 'Rock'), ('Regatta_De_Blanc', 'isGenre_Reggae', 'Reggae'), ('Outlandos_D%27Amour', 'isGenre_Punk', 'Punk'), ('The_Beatles(Album)', 'isGenre_Jazz', 'Jazz'), ('In_The_Gallery', 'isGenre_Rock', 'Rock'), ('Lions', 'isGenre_Rock', 'Rock'), ('Africa', 'isGenre_Rock', 'Rock'), ('Shape_of_my_Heart', 'isGenre_Pop', 'Pop'), ('Let_It_Be', 'isGenre_Pop', 'Pop'), ('Making_Movies', 'isGenre_Pop', 'Pop'), ('461_Ocean_Blvd.', 'isGenre_Blues', 'Blues'), ('Ten_Summoner%27s_Tales', 'isGenre_Pop', 'Pop'), ('Down_To_The_Waterline', 'isGenre_Rock', 'Rock')}    # isGenre_v = {('Africa', 'Funk'), ('Toto_IV', 'Metal'), ('Making_Movies', 'Metal'), ('Ten_Summoner%27s_Tales', 'Rock'), ('Make_Beleive', 'Jazz'), ('Make_Beleive', 'Rock'), ('Africa', 'Soul'), ('Toto', 'Metal'), ('Make_Beleive', 'Funk'), ('Outlandos_D%27Amour', 'Metal'), ('Dire_Straits(Album)', 'Metal'), ('Africa', 'Jazz'), ('Let_It_Be', 'Metal'), ('Ten_Summoner%27s_Tales', 'Metal'), ('461_Ocean_Blvd.', 'Rock')}
    # isGenre_v = {('Sultans_Of_Swing', 'NONONOFunk'), ('Make_Believe', 'NONONOMetal'), ('Water_Of_Love', 'NONONOCountry'), ('Outlandos_D%27Amour', 'Pop'), ('The_Seventh_One', 'Jazz'), ('The_Beatles(Album)', 'Rock'), ('It%27s_a_Feeling', 'NONONOSoul'), ('Outlandos_D%27Amour', 'Jazz'), ('Lovers_in_the_Night', 'NONONOCountry'), ('The_Seventh_One', 'Pop'), ('The_Seventh_One', 'Reggae'), ('Regatta_De_Blanc', 'Jazz'), ('Making_Movies', 'Reggae'), ('461_Ocean_Blvd.', 'Rock'), ('Ten_Summoner%27s_Tales', 'Rock')}

    # #valid rule
    # r = Rule(head=("?VAR1","isGenre", "?VAR2"), 
    #          body={("?VAR3", "collaboratedWith", "?VAR4"), ("?VAR5", "hasAlbum", "?VAR6"), ("?VAR7", "isGenre", "?VAR8"), 
    #                ("?VAR9", "hasAlbum", "?VAR10"), ("?VAR11", "releaseYear", "?VAR12"), ("?VAR13", "releaseYear", "?VAR14"), ("?VAR15", "<", "?VAR16")}, 
    #                connections={("?VAR1", "?VAR6", "?VAR11"), ("?VAR2", "?VAR8"), ("?VAR5", "?VAR3"), ("?VAR4", "?VAR9"),("?VAR10", "?VAR7", "?VAR13"), ("?VAR12", "?VAR16"),("?VAR14", "?VAR15")}) 
    
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


    # p1 = Path()
    # p1.head = ("Ten_Summoner%27s_Tales","isGenre_Pop","Pop")
    # p1.graph.add("Dire_Straits","hasAlbum_Making_Movies", "Making_Movies")
    # p1.graph.add("Sting", "collaboratedWith_Dire_Straits", "Dire_Straits")
    # p1.graph.add("Sting","hasAlbum_Ten_Summoner%27s_Tales","Ten_Summoner%27s_Tales")
    # p1.graph.add("Making_Movies","isGenre_Pop","Pop")
    # p1.graph.add("Ten_Summoner%27s_Tales","releaseYear_1993","\"1993\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    # p1.graph.add("Making_Movies","releaseYear_1980","\"1980\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    # p1.graph.add("\"1980\"^^<http://www.w3.org/2001/XMLSchema#/int>","<","\"1993\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    # p1.graph.add("Shape_of_my_Heart","writer_Sting","Sting")

    # p2 = Path()
    # p2.head = ("I_Shot_the_Sheriff","isGenre_Rock","Rock")
    #p2.graph.add("Here_Comes_the_Sun","releaseYear_1969","\"1969\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    #p2.graph.add("461_Ocean_Blvd.","releaseYear_1974","\"1974\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    #p2.graph.add("\"1969\"^^<http://www.w3.org/2001/XMLSchema#/int>","<","\"1974\"^^<http://www.w3.org/2001/XMLSchema#/int>")
    # p2.graph.add("I_Shot_the_Sheriff","includedIn_461_Ocean_Blvd.","461_Ocean_Blvd.")
    # p2.graph.add("461_Ocean_Blvd.","isGenre_Rock","Rock")

    # print(p2)
    # print(p2.rule(pmap))
    # print(p2.graph)
    # r1 = p1.rule(pmap)

    # r2 = p2.rule(pmap)

    # r3 = Rule(
    #     head=('?VAR1', 'isGenre', '?VAR2'),
    #     body={('?VAR9', 'isGenre', '?VAR10'), ('?VAR15', 'releaseYear', '?VAR16'), ('?VAR3', 'hasAlbum', '?VAR4')},
    #     connections={('?VAR4', '?VAR1', '?VAR15'), ('?VAR10', '?VAR2')})


    # if pmap.target == "isGenre":
    #     rule_dict = {}
    #     rule_dict[p1.rule(pmap)] = set()
    #     rule_dict[p2.rule(pmap)] = set()
    #     rule_dict[r3] = set()
    #     R_out = [r1,r2]
    #     #print(v)
    #     for egg in isGenre_g:
    #         eg = Path(head=(egg[0], pmap.target, egg[1]))
    #         if covers(r1, kg, egg, pmap):
    #             rule_dict[r1].add(eg)
    #         if covers(r2, kg, egg, pmap):
    #             rule_dict[r2].add(eg)
    #         if covers(r3, kg, egg, pmap):
    #             rule_dict[r3].add(eg)
    #     print(est_m_weight(r3, R_out, rule_dict, kg, isGenre_g, isGenre_v, alpha, beta, pmap))
    #     print(cov(r2, kg, isGenre_v, pmap))


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


    ###########################
    # end of test code
    ###########################


    #TODO rudik

    # initialise
    # create a path per pair in g
    # expand by one and save resulting paths in rule dict

    R_out_dict = {}
    rule_dict = {}  
    rule = None 
    paths = {Path((s, p , o), IncidenceList()) for s,p,o in g}

    

    for path in paths:
        expanded_paths = expand_fun(path, kg, ontology, pmap, type_predicate)
        for ep in expanded_paths:
            rule = ep.rule(pmap)
            if rule in rule_dict:
                rule_dict[rule].add(ep)
            else:
                rule_dict[rule] = {ep}



    r, min_weight = find_r(R_out_dict, rule_dict, kg, g, v, alpha, beta, pmap)




    # main loop 

    while True:

        if not rule_dict or cov_g(list(R_out_dict.keys()), g, rule_dict, R_out_dict) == g or min_weight >= 0:
            break
        
        if is_valid(r):
            # move rule to output dict
            R_out_dict[r] = rule_dict.pop(r)
            print(f"\n\nFOUND RULE {r} with {min_weight}\n\n")
            
        else:
            # expand
            # TODO len(r.body) only works if rule is a straight path, need seperate function and different if clause if allow branching
            if fits_max_depth(r, max_depth):
                expand_rule(r, rule_dict, kg, ontology, pmap, type_predicate, expand_fun)
    
            # remove handled rule
            rule_dict.pop(r)

        # find next r
        r, min_weight = find_r(R_out_dict, rule_dict, kg, g, v, alpha, beta, pmap)


    # TODO possibly return the whole R_out_dict or calc some metrics here 
    return list(rule.as_csv_row() for rule in R_out_dict.keys())



def find_r(R_out_dict, rule_dict, kg:IncidenceList, g:set, v:set, alpha:float, beta:float, pmap:P_map):
    min_weight = np.inf
    r = None
    for rule in rule_dict.keys():
        weight = est_m_weight(rule, R_out_dict, rule_dict, kg, g, v, alpha, beta, pmap)
        if weight < min_weight:
            r = rule
            min_weight = weight

    return r, min_weight



def expand_rule(rule, rule_dict, kg:IncidenceList, ontology:Ontology, pmap:P_map, type_predicate, expand_fun):

    for path in rule_dict[rule]:
        expanded_paths = expand_fun(path, kg, ontology, pmap, type_predicate)
        if expanded_paths:
            for ep in expanded_paths:
                r = ep.rule(pmap)
                if r in rule_dict:
                    rule_dict[r].add(ep)
                else:
                    rule_dict[r] = {ep}
                

def fits_max_depth_rudik(r:Rule, max_depth):
    return len(r.body) < max_depth

def expand_path_rudik(path:Path, kg:IncidenceList, ontology:Ontology, pmap:P_map, type_predicate:str):
    expanded_paths = set()
    # TODO here is decided what structure the rules will have, is every node a frontier to branch out?  or only leaves...

    # find all leaves, head object doesn't count
    # TODO this is wrong, need to count corresponding appearances not different preds, there can be 1000 triples with same pred in graph... 
    frontiers = path.frontiers()
    #print(f"path {path} frontiers {frontiers}")
    # if head subject isn't connected -> path is only head, it's a leaf too
    if path.head[0] not in path.graph.nodes.keys():
        frontiers.add(path.head[0])

    # go through all possible new triples, create new path versions with one more triple than given path
    # TODO depending on how rules should look like, add multiple triples here aswell

    for f in frontiers:
        preds = kg.nodes.get(f)
        if not preds:
            continue

        for p in preds:
            pairs = kg.edges.get(p)
            if not pairs:
                continue

            for pair in pairs:
                if f not in pair:
                # cannot jump through kg
                    continue

                e = pair[0] if pair[1] == f else pair[1]

                if e != f and e in path.graph.nodes.keys():
                # don't want circles, except when s = o
                    continue

                triple = (pair[0],p, pair[1])

                if triple == path.head:
                # we only want triples that are not in path, need to check head seperately here
                    continue

                if fits_domain_range(e, triple, ontology, kg, pmap, type_predicate):
                    new = path.copy()
                    new.graph.add(pair[0], p, pair[1])
                    expanded_paths.add(new)
    return expanded_paths



def fits_max_depth_branch(r:Rule, max_depth):
    pass

def expand_path_branch(path:Path, kg:IncidenceList, ontology:Ontology, pmap:P_map, type_predicate:str):
    pass






