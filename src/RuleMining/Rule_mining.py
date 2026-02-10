import json
import csv
import numpy as np
import warnings
from RuleMining.Util import *
from RuleMining.Classes import Path, Rule, P_map, IncidenceList, Ontology

import time




def mine_rules(transformed_kg:IncidenceList, targets:set, transform_output_dir:str, ontology:Ontology, rules_file:str, prefix:str, max_depth:int=3, set_size:int=100, 
               alpha:float=0.5, type_predicate:str='http://www.w3.org/1999/02/22-rdf-syntax-ns#type', rule_type:str="rudik", negative_rules:bool=False):
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


    # need to ensure predicate mapping consistency, every new predicate mentioned in mappings must be in kg, even if there is no corresponding triple
    check_preds_in_graph(neg_predicate_mappings, transformed_kg)

    result = []

    # TODO remove
    exr_time = 0
    exp_time = 0
    find_r_time = 0
    w_time = 0
    exp_calls = 0
    w_calls = 0
    cov_time = 0
    fdr_time = 0
    rule_time = 0

    for p in targets:

        # getting post normalization instances of target predicate and the negative instances from validation
        pmap = P_map(p, new_preds(p, predicate_mappings), set() , predicate_mappings, neg_predicate_mappings)
        pmap.neg_predicates = neg_preds(pmap.predicates, neg_predicate_mappings)


        if negative_rules:
            # TODO prepare g and v flipped
            # meaning, pos examples without predicate as v, negative examples with negative predicate as g
            pass
            print(f"creating input sets G and V in order to mine negative rules for target predicate <{p}>...\n")

            v_temp = getExamples(transformed_kg, pmap.predicates, set_size)
            len_v = len(v_temp)
            if len_v < set_size:
                print(f"There aren't enough positive examples in the graph, proceeding with {len_v} examples in V.\n")  
            v = set()
            for ex in v_temp:
                v.add((ex[0], ex[2]))


            # first, get constraint violating triples
            g_temp = getNegExamples(transformed_kg, pmap.neg_predicates, set_size)

            # if not enough in v fill with lcwa-conform examples
            len_g = len(g_temp)
            if len_g < set_size:
                print(f"{len_g} examples found from constraint violations, selecting remaining {set_size - len_g} examples from graph for G.\n")
                g_temp.update(getExamplesLCWA(transformed_kg, ontology, pmap, set_size - len_g, type_predicate))

            # if not enough in v fill with random examples
            len_g = len(g_temp)
            if len_g < set_size:
                print(f"There aren't enough negative examples in the graph, choosing {set_size - len_g} random examples for G.\n")  
                v.update(getRandomNegExamples(transformed_kg, pmap.predicates, set_size - len_g, g_temp)) 


            len_g = len(g_temp)
            if len_g < set_size:
                print(f"There aren't enough negative examples in the graph, proceeding with {len_g} examples for G.\n")   

            g = set()
            for ex in g_temp:
                g.add((ex[0], pmap.target, ex[1]))
        else:
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

        #result.extend(mine_rules_for_target_predicate(g, v, pmap, transformed_kg, prefix, type_predicate, ontology, expand_fun, fits_max_depth, max_depth, alpha, beta))

        #TODO remove
        res, exr, exp, find_r, wt, ec, wc, fdr, cov, rt = mine_rules_for_target_predicate(g, v, pmap, transformed_kg, prefix, type_predicate, ontology, expand_fun, fits_max_depth, negative_rules, max_depth, alpha, beta)
        result.extend(res)
        exr_time += exr
        exp_time += exp
        find_r_time += find_r
        w_time += wt
        exp_calls += ec
        w_calls += wc
        fdr_time += fdr
        cov_time += cov
        rule_time += rt
        

    print(result)
    print(f"exp rule {exr_time}\nexp path {exp_time} for {exp_calls} calls\n find r {find_r_time}\n weight time {w_time} for {w_calls} calls\n fits_domain_range {fdr_time}\n cov/uncov {cov_time}\n path.rule() time {rule_time}")
    #TODO add result to csvs
    with open(rules_file, mode='w', newline='', encoding='utf-8') as datei:
        writer = csv.writer(datei)
        writer.writerow(["head", "body"])
        writer.writerows(result)

    return

def mine_rules_for_target_predicate(g:set, v:set, pmap:P_map, kg:IncidenceList, prefix:str, type_predicate:str, ontology:Ontology, 
                                    expand_fun, fits_max_depth, negative_rules,  max_depth:int=3, alpha:float=0.5, beta:float=0.5):
    
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


    

    
    isGenre_g = {('Dire_Straits(Album)', 'isGenre_Rock', 'Rock'), ('Let_It_Be', 'isGenre_Rock', 'Rock'), ('Rosanna', 'isGenre_Rock', 'Rock'), ('Regatta_De_Blanc', 'isGenre_Reggae', 'Reggae'), ('Outlandos_D%27Amour', 'isGenre_Punk', 'Punk'), ('The_Beatles(Album)', 'isGenre_Jazz', 'Jazz'), ('In_The_Gallery', 'isGenre_Rock', 'Rock'), ('Lions', 'isGenre_Rock', 'Rock'), ('Africa', 'isGenre_Rock', 'Rock'), ('Shape_of_my_Heart', 'isGenre_Pop', 'Pop'), ('Let_It_Be', 'isGenre_Pop', 'Pop'), ('Making_Movies', 'isGenre_Pop', 'Pop'), ('461_Ocean_Blvd.', 'isGenre_Blues', 'Blues'), ('Ten_Summoner%27s_Tales', 'isGenre_Pop', 'Pop'), ('Down_To_The_Waterline', 'isGenre_Rock', 'Rock')}    # isGenre_v = {('Africa', 'Funk'), ('Toto_IV', 'Metal'), ('Making_Movies', 'Metal'), ('Ten_Summoner%27s_Tales', 'Rock'), ('Make_Beleive', 'Jazz'), ('Make_Beleive', 'Rock'), ('Africa', 'Soul'), ('Toto', 'Metal'), ('Make_Beleive', 'Funk'), ('Outlandos_D%27Amour', 'Metal'), ('Dire_Straits(Album)', 'Metal'), ('Africa', 'Jazz'), ('Let_It_Be', 'Metal'), ('Ten_Summoner%27s_Tales', 'Metal'), ('461_Ocean_Blvd.', 'Rock')}
    isGenre_v = {('Sultans_Of_Swing', 'NONONOFunk'), ('Make_Believe', 'NONONOMetal'), ('Water_Of_Love', 'NONONOCountry'), ('Outlandos_D%27Amour', 'Pop'), ('The_Seventh_One', 'Jazz'), ('The_Beatles(Album)', 'Rock'), ('It%27s_a_Feeling', 'NONONOSoul'), ('Outlandos_D%27Amour', 'Jazz'), ('Lovers_in_the_Night', 'NONONOCountry'), ('The_Seventh_One', 'Pop'), ('The_Seventh_One', 'Reggae'), ('Regatta_De_Blanc', 'Jazz'), ('Making_Movies', 'Reggae'), ('461_Ocean_Blvd.', 'Rock'), ('Ten_Summoner%27s_Tales', 'Rock')}
    isGenre_v =  {('Make_Believe', 'Making_Movies'), ('Make_Believe', 'Abbey_Road'), ('I_Won%27t_Hold_You_Back', 'Dire_Straits(Album)'), ('Make_Believe', '461_Ocean_Blvd.'), ('I_Won%27t_Hold_You_Back', 'Making_Movies'), ('Water_Of_Love', 'Toto_IV'), ('Sultans_Of_Swing', 'Toto_IV'), ('Make_Believe', 'Communiqué(Album)'), ('Lions', 'Toto_IV'), ('Down_To_The_Waterline', 'Toto_IV'), ('In_The_Gallery', 'Toto_IV'), ('I_Won%27t_Hold_You_Back', '461_Ocean_Blvd.'), ('Six_Blade_Knife', 'Toto_IV'), ('Setting_Me_Up', 'Toto_IV'), ('Wild_West_End', 'Toto_IV')}
    parent_g = {('Duchess_Helene_of_Mecklenburg_Schwerin', 'parent_Princess_Caroline_Louise_of_Saxe_Weimar_Eisenach', 'Princess_Caroline_Louise_of_Saxe_Weimar_Eisenach'), ('Maria_Carolina_of_Austria', 'parent_Maria_Theresa', 'Maria_Theresa'), ('Welf_I_Duke_of_Bavaria', 'parent_Kunigunde_of_Altdorf', 'Kunigunde_of_Altdorf'), ('Humbert_II_Count_of_Savoy', 'parent_Joan_of_Geneva', 'Joan_of_Geneva'), ('Francesco_I_Sforza', 'parent_Muzio_Attendolo_Sforza', 'Muzio_Attendolo_Sforza'), ('John_Count_of_Chalon', 'parent_Stephen_III_of_Auxonne', 'Stephen_III_of_Auxonne'), ('Joan_Beaufort_Queen_of_Scots', 'parent_John_Beaufort_1st_Earl_of_Somerset', 'John_Beaufort_1st_Earl_of_Somerset'), ('Marie_of_Brabant_Queen_of_France', 'parent_Henry_III_Duke_of_Brabant', 'Henry_III_Duke_of_Brabant'), ('Mary_de_Bohun', 'parent_Humphrey_de_Bohun_7th_Earl_of_Hereford', 'Humphrey_de_Bohun_7th_Earl_of_Hereford'), ('Eckhard_I_Count_of_Scheyern', 'parent_Otto_I_Count_of_Scheyern', 'Otto_I_Count_of_Scheyern'), ('Maria_Anna_of_Bavaria_born_1551', 'parent_Albert_V_Duke_of_Bavaria', 'Albert_V_Duke_of_Bavaria'), ('Matilda_of_Carinthia', 'parent_Engelbert_Duke_of_Carinthia', 'Engelbert_Duke_of_Carinthia'), ('Maria_Theresa_of_Savoy', 'parent_Victor_Amadeus_III_of_Sardinia', 'Victor_Amadeus_III_of_Sardinia'), ('Philip_II_of_Spain', 'parent_Charles_V_Holy_Roman_Emperor', 'Charles_V_Holy_Roman_Emperor'), ('Charles_V_Duke_of_Lorraine', 'parent_Claude_Fran_oise_de_Lorraine', 'Claude_Fran_oise_de_Lorraine')}
    parent_v = {('John_of_Gaunt', 'Theodoric_II_Duke_of_Lorraine'), ('Humbert_II_Count_of_Savoy', 'Theodoric_II_Duke_of_Lorraine'), ('Simon_I_Duke_of_Lorraine', 'Douce_I_Countess_of_Provence'), ('Simon_I_Duke_of_Lorraine', 'Charles_I_Duke_of_Bourbon'), ('Stephen_II_Duke_of_Bavaria', 'Theodoric_II_Duke_of_Lorraine'), ('Simon_I_Duke_of_Lorraine', 'Philippa_of_Hainault'), ('Simon_I_Duke_of_Lorraine', 'Louis_X_of_France'), ('Afonso_IV_of_Portugal', 'Theodoric_II_Duke_of_Lorraine'), ('Simon_I_Duke_of_Lorraine', 'Ranulf_II_of_Aquitaine'), ('Berengaria_of_Barcelona', 'Theodoric_II_Duke_of_Lorraine'), ('Simon_I_Duke_of_Lorraine', 'Elizabeth_of_Portugal'), ('Simon_I_Duke_of_Lorraine', 'Amadeus_II_Count_of_Savoy'), ('Joan_II_of_Navarre', 'Theodoric_II_Duke_of_Lorraine'), ('Ebalus_Duke_of_Aquitaine', 'Theodoric_II_Duke_of_Lorraine'), ('Margaret_of_Bourbon_1438_1483', 'Theodoric_II_Duke_of_Lorraine')}
    #valid rule
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
#   "max_body_length": "",
#   "example_set_size": "",
#   "type_predicate":  "",
#   "alpha": "",
#   "mine_negative_rules": ""
#   }

# {
#   "KG": "SynthLC_1000",
#   "prefix": "http://synthetic-LC.org/lungCancer/",
#   "rules_file": "SynthLC_1000.csv",
#   "rdf_file": "SynthLC_1000.nt",
#   "constraints_folder": "SynthLC_1000",
#   "ontology_file": "ontology_LungCancer.ttl",
#   "pca_threshold": 0.75
# }


# {
#   "KG": "FrenchRoyalty",
#   "prefix": "http://FrenchRoyalty.org/",
#   "rules_file": "FrenchRoyalty.csv",
#   "rdf_file": "french_royalty.nt",
#   "constraints_folder": "FrenchRoyalty",
#   "ontology_file": "ontology_FrenchRoyalty.ttl",
#   "pca_threshold": 0.75
# }



    rulelist = [Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'child', '?VAR4')},
        connections= {('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'mother', '?VAR4')},
        connections= {('?VAR3', '?VAR1'), ('?VAR4', '?VAR2')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'father', '?VAR4')},
        connections= {('?VAR4', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'parent', '?VAR4')},
        connections= {('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'successor', '?VAR4')},
        connections= {('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'successor', '?VAR4')},
        connections= {('?VAR4', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'spouse', '?VAR4')},
        connections= {('?VAR4', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'father', '?VAR4')},
        connections= {('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'predecessor', '?VAR4')},
        connections= {('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'father', '?VAR4')},
        connections= {('?VAR3', '?VAR1'), ('?VAR4', '?VAR2')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'mother', '?VAR4')},
        connections= {('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'mother', '?VAR4')},
        connections= {('?VAR4', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'child', '?VAR4')},
        connections= {('?VAR4', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'successor', '?VAR4')},
        connections= {('?VAR3', '?VAR2'), ('?VAR4', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'child', '?VAR4')},
        connections= {('?VAR3', '?VAR2'), ('?VAR4', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'predecessor', '?VAR4')},
        connections= {('?VAR3', '?VAR1'), ('?VAR4', '?VAR2')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'predecessor', '?VAR4')},
        connections= {('?VAR4', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
        connections= {('?VAR5', '?VAR2'), ('?VAR3', '?VAR1'), ('?VAR4', '?VAR6')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR7', 'parent', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
        connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR7', 'spouse', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
        connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR7', 'mother', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
        connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4'), ('?VAR7', 'father', '?VAR8')},
        connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR7', 'spouse', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
        connections= {('?VAR8', '?VAR2'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR7')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'gender', '?VAR6'), ('?VAR7', 'successor', '?VAR8'), ('?VAR3', 'gender', '?VAR4')},
        connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'gender', '?VAR6'), ('?VAR7', 'predecessor', '?VAR8'), ('?VAR3', 'gender', '?VAR4')},
        connections= {('?VAR8', '?VAR2'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR7')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'gender', '?VAR6'), ('?VAR7', 'child', '?VAR8'), ('?VAR3', 'gender', '?VAR4')},
        connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR7', 'parent', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
        connections= {('?VAR8', '?VAR2'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR7')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4'), ('?VAR7', 'father', '?VAR8')},
        connections= {('?VAR8', '?VAR2'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR7')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
        connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'parent', '?VAR6')},
        connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'spouse', '?VAR6')},
        connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'predecessor', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
        connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'child', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
        connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'father', '?VAR6')},
        connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'mother', '?VAR6')},
        connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'successor', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
        connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'spouse', '?VAR6')},
        connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'parent', '?VAR6')},
        connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'mother', '?VAR6')},
        connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'father', '?VAR6')},
        connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'successor', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
        connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'predecessor', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
        connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'child', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
        connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'spouse', '?VAR6')},
        connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'father', '?VAR6')},
        connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
        connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'predecessor', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
        connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'child', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
        connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'successor', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
        connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'parent', '?VAR6')},
        connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'parent', '?VAR6')},
        connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'successor', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
        connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'spouse', '?VAR6')},
        connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'father', '?VAR6')},
        connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'predecessor', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
        connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'mother', '?VAR6')},
        connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR5', 'child', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
        connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
        , Rule(
        head= ('?VAR1', 'parent', '?VAR2'),
        body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'mother', '?VAR6')},
        connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
        ]
    

    pathlist = [ Path( ('Blanche_of_Burgundy', 'parent_Mahaut_Countess_of_Artois', 'Mahaut_Countess_of_Artois'), IncidenceList(
        {'spouse_Charles_IV_of_France': {('Blanche_of_Burgundy', 'Charles_IV_of_France')}, 
         'spouse_Joan_of__vreux': {('Charles_IV_of_France', 'Joan_of__vreux')}},        
        {'Blanche_of_Burgundy': {'spouse_Charles_IV_of_France'}, 
         'Charles_IV_of_France': {'spouse_Charles_IV_of_France', 'spouse_Joan_of__vreux'},
           'Joan_of__vreux': {'spouse_Joan_of__vreux'}}
        )),

        Path( ('Philip_V_of_Spain', 'parent_Louis_Dauphin_of_France_son_of_Louis_XIV', 'Louis_Dauphin_of_France_son_of_Louis_XIV'), IncidenceList(
         {'spouse_Maria_Amalia_of_Saxony': {('Philip_V_of_Spain', 'Maria_Amalia_of_Saxony'),
                                             ('Charles_III_of_Spain', 'Maria_Amalia_of_Saxony')}},
         {'Philip_V_of_Spain': {'spouse_Maria_Amalia_of_Saxony'}, 
          'Maria_Amalia_of_Saxony': {'spouse_Maria_Amalia_of_Saxony'}, 
          'Charles_III_of_Spain': {'spouse_Maria_Amalia_of_Saxony'}}
        )),
        Path( ('Philip_V_of_Spain', 'parent_Louis_Dauphin_of_France_son_of_Louis_XIV', 'Louis_Dauphin_of_France_son_of_Louis_XIV'), IncidenceList(
         {'spouse_Maria_Amalia_of_Saxony': {('Philip_V_of_Spain', 'Maria_Amalia_of_Saxony')},
           'marriedTo_Elisabeth_Farnese': {('Maria_Amalia_of_Saxony', 'Elisabeth_Farnese')}},
         {'Philip_V_of_Spain': {'spouse_Maria_Amalia_of_Saxony'},
           'Maria_Amalia_of_Saxony': {'marriedTo_Elisabeth_Farnese', 'spouse_Maria_Amalia_of_Saxony'},
             'Elisabeth_Farnese': {'marriedTo_Elisabeth_Farnese'}}
        )), 


        Path( ('Philip_V_of_Spain', 'parent_Louis_Dauphin_of_France_son_of_Louis_XIV', 'Louis_Dauphin_of_France_son_of_Louis_XIV'), IncidenceList(
         {'spouse_Maria_Amalia_of_Saxony': {('Philip_V_of_Spain', 'Maria_Amalia_of_Saxony'), ('Charles_III_of_Spain', 'Maria_Amalia_of_Saxony')}},
         {'Philip_V_of_Spain': {'spouse_Maria_Amalia_of_Saxony'},
           'Maria_Amalia_of_Saxony': {'spouse_Maria_Amalia_of_Saxony'},
             'Charles_III_of_Spain': {'spouse_Maria_Amalia_of_Saxony'}}
        )),
        Path( ('Philip_V_of_Spain', 'parent_Louis_Dauphin_of_France_son_of_Louis_XIV', 'Louis_Dauphin_of_France_son_of_Louis_XIV'), IncidenceList(
         {'spouse_Maria_Amalia_of_Saxony': {('Philip_V_of_Spain', 'Maria_Amalia_of_Saxony')}},
         {'Philip_V_of_Spain': {'spouse_Maria_Amalia_of_Saxony'},
           'Maria_Amalia_of_Saxony': { 'spouse_Maria_Amalia_of_Saxony'}}
        )),
        ]
     



    #########################
    # FR runtime
    
    # exp rule 293.1274049282074
    # exp path 292.27738404273987 for 39326 calls
    # find r 247.1837990283966
    # weight time 244.89486694335938 for 12249 calls
    # fdr 228.44119000434875
    # cov 61.921411752700806

    # exp rule 250.4089686870575
    # exp path 249.61481380462646 for 36992 calls
    # find r 223.62124681472778
    # weight time 222.06457448005676 for 9523 calls
    # fdr 195.1195251941681
    # cov 84.86956405639648

    # Total execution time: 498.85 seconds


    # exp rule 326.1665086746216
    # exp path 325.29557514190674 for 45334 calls
    # find r 1619.713145494461
    # weight time 1617.6381304264069 for 11601 calls
    # fdr 254.85655879974365
    # cov 135.619286775589

    # Total execution time: 1972.67 seconds

    # exp rule 1289.1665630340576
    # exp path 1288.9272735118866 for 43281 calls
    # find r 225.8708691596985
    # weight time 215.14681196212769 for 9711 calls
    # fdr 112.79601550102234
    # cov 52.896766901016235
    # rule time 1154.3494980335236
    # Total execution time: 1531.63 seconds

    ################################









    ###########################
    # end of test code
    ###########################


    #TODO when expanding, excluding bad paths better?
    # TODO when finding r, mind rules with same weight, collect all and look through those until a rule is found

    # initialise
    # create a path per pair in g
    # expand by one and save resulting paths in rule dict

    R_out_dict = {}
    rule_dict = {}  

    # for saving calculation results for est m weight
    rule_weight_dict = {}
    R_out_cov_v_cardinality = [None]
    R_out_uncov_v = None
    
   # TODO remove
    exr_time = 0
    exp_time = 0
    find_r_time = 0
    w_time = 0
    fdr_time = 0
    rule_time = 0
    cov_time = 0

    exp_calls = 0
    w_calls = 0

    paths = {Path((s, p , o), IncidenceList()) for s,p,o in g}

    # TODO call expand rule here, duplicate code

    t1 = time.time()
    for path in paths:
        exp_calls += 1
        t2 = time.time()
        frontier, time_add_Copy = expand_fun(rule_dict, path, kg, ontology, pmap, type_predicate)
        fdr_time+= frontier
        rule_time += time_add_Copy
        t3=time.time()
        exp_time += t3 - t2

    t4 = time.time()
    exr_time = t4 - t1

    r, min_weight,wt, wc, ct = find_r(R_out_dict, R_out_cov_v_cardinality, R_out_uncov_v, rule_dict, rule_weight_dict, kg, g, v, alpha, beta, pmap, fits_max_depth, max_depth)
    t5= time.time()
    find_r_time = t5-t4
    w_time += wt
    w_calls += wc
    cov_time += ct
 

    # main loop 

    while True:


        #print(f"ruledict {len(rule_dict)}\n\n cov == g {cov_g(list(R_out_dict.keys()), rule_dict, R_out_dict) == g}\n\nmw {min_weight}\n\n")

        if not rule_dict or cov_g(list(R_out_dict.keys()), rule_dict, R_out_dict) == g or min_weight >= 0:
            #print(f"END ruledict {len(rule_dict)}\n\n cov == g {cov_g(list(R_out_dict.keys()), rule_dict, R_out_dict) == g}\n\nmw {min_weight}\n\n")
            break
        
        if is_valid(r):
            # move rule to output dict
            R_out_dict[r] = rule_dict.pop(r)

            # resetting these, since R_out has changed
            rule_weight_dict = {}
            R_out_cov_v_cardinality = [None, None]
            R_out_uncov_v = None
            print(f"\n\nFOUND RULE {r} with {min_weight}\n\n")
            
        else:
            # expand
            if fits_max_depth(r, max_depth):
                #print("expand")
                t1 = time.time()
                et, ec, fdr, rt = expand_rule(r, rule_dict, kg, ontology, pmap, type_predicate, expand_fun)
                exr_time += time.time() - t1
                exp_time += et
                exp_calls += ec
                fdr_time += fdr
                rule_time += rt
            # remove handled rule
            rule_dict.pop(r)

        # find next r
        #print("find_r")
        t1 = time.time()
        r, min_weight, wt, wc, ct = find_r(R_out_dict, R_out_cov_v_cardinality, R_out_uncov_v, rule_dict, rule_weight_dict, kg, g, v, alpha, beta, pmap, fits_max_depth, max_depth)
        find_r_time += time.time() -t1
        w_time += wt
        w_calls += wc
        cov_time += ct

    # TODO possibly return the whole R_out_dict or calc some metrics here 

    

    return list(rule.as_csv_row(negative_rules) for rule in R_out_dict.keys()), exr_time, exp_time, find_r_time, w_time, exp_calls, w_calls, fdr_time, cov_time, rule_time



def find_r(R_out_dict:dict, R_out_cov_v_cardinality:list, R_out_uncov_v:set, rule_dict:dict, rule_weight_dict:dict, kg:IncidenceList, g:set, v:set, alpha:float, beta:float, pmap:P_map, fits_max_depth,  max_depth:int):

    w_time = 0
    wc = 0
    cov_time = 0
    min_weight = np.inf
    r = None

    rules_to_remove = set()

    for rule in rule_dict.keys():
        if rule in rule_weight_dict:
            weight = rule_weight_dict[rule]
        else:
            wc += 1
            tw = time.time()
            ct, weight = est_m_weight(rule, R_out_dict, rule_dict, kg, g, v, alpha, beta, pmap, R_out_cov_v_cardinality, R_out_uncov_v)
            w_time += time.time() - tw
            rule_weight_dict[rule] = weight
            cov_time += ct

        if not fits_max_depth(rule, max_depth) and (weight >= 0 or not is_valid(rule)):
            # collect hopeless rules
            rules_to_remove.add(rule)
            continue

        if weight < min_weight or (weight == min_weight and is_valid(rule)):
            r = rule
            min_weight = weight


    
    # remove hopeless rules, declutter rule_dict
    #print(f"removing {len(rules_to_remove)} hopeless rules")
    for rule in rules_to_remove:
        rule_dict.pop(rule)

    return r, min_weight, w_time, wc, cov_time



def expand_rule(rule, rule_dict, kg:IncidenceList, ontology:Ontology, pmap:P_map, type_predicate, expand_fun):
    exp_time = 0
    ec = 0
    fdr_time = 0
    rule_time = 0
    for path in rule_dict[rule]:
        ec += 1
        t = time.time()
        fdr, rt= expand_fun(rule_dict, path, kg, ontology, pmap, type_predicate)
        fdr_time += fdr
        rule_time += rt
        exp_time += time.time() - t
          
    return exp_time, ec, fdr_time, rule_time

def fits_max_depth_rudik(r:Rule, max_depth):
    return len(r.body) < max_depth


"""expands given path by one from frontiers, creates straight paths in line with RuDiK"""
def expand_path_rudik(rule_dict:dict, path:Path, kg:IncidenceList, ontology:Ontology, pmap:P_map, type_predicate:str):

    # find  leaf, head object doesn't count
    f = path.frontiers_rudik()

    if f == None:
        print(f"no frontier for {path}")
        print(path.frontiers_rudik())
        exit()

    time_copy_add = 0
    t_if = 0
    # TODO literal comparisons
    if is_literal(f):
        pass

    preds = kg.nodes.get(f)

    for p in preds:
        # don't want to traverse type triples or negative triples
        if pmap.original_pred(p) == type_predicate or p in pmap.neg_predicate_mappings:
            continue


        for pair in kg.edges.get(p):
            if f in pair:
            # cannot jump through kg

                triple = (pair[0],p, pair[1])
                edges_p = path.graph.edges.get(p)
                if ( edges_p and  pair in edges_p) or triple == path.head:
                # we only want triples that are not in path, need to check head seperately here
                    continue


                # e is entity path is expanded to
                e = pair[0] if pair[1] == f else pair[1]

                if e != f and e in path.graph.nodes:
                # don't want circles, except when s = o
                    continue

                subtime = 0
                t = time.time()
                if fits_domain_range(e, triple, ontology, kg, pmap, type_predicate):
                    t3 = time.time()

                    # check path.copy() -> is slow
                    new = path.copy()
                    t5 = time.time()

                    new.graph.add(pair[0], p, pair[1])

                    r = new.rule_rudik(pmap)


                    if r in rule_dict:
                        rule_dict[r].add(new)
                    else:
                        rule_dict[r] = {new}

                    time_copy_add += (t5-t3)
                t2 = time.time()
                t_if += (t2-t)

    return t_if, time_copy_add



def fits_max_depth_branch(r:Rule, max_depth):
    pass

def expand_path_branch(path:Path, kg:IncidenceList, ontology:Ontology, pmap:P_map, type_predicate:str):
    pass






