import json
import csv
import numpy as np
import warnings
from RuleMining.Util import *
from RuleMining.Classes import Path, Rule, P_map, IncidenceList, Ontology





def mine_rules(transformed_kg:IncidenceList, targets:set, transform_output_dir:str, ontology:Ontology, rules_file:str, prefix:str, max_depth:int=3, set_size:int=100, 
               alpha:float=0.5, type_predicate:str='http://www.w3.org/1999/02/22-rdf-syntax-ns#type', rule_type:str="rudik", negative_rules:bool=False, onto_valid:bool=False):
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

    if onto_valid:
        pmap = P_map(None, None , set() , predicate_mappings, neg_predicate_mappings)
        kg = IncidenceList()
        count = 0
        for k,v in transformed_kg.edges.items():
            for pair in v:
                if k.__contains__(type_predicate):
                    kg.add(pair[0], k, pair[1])
                    continue
    
                if fits_domain_range(pair[0], (pair[0], k, pair[1]), ontology, transformed_kg, pmap, type_predicate):
                    if fits_domain_range(pair[1], (pair[0], k, pair[1]), ontology, transformed_kg, pmap, type_predicate):
                        count += 1
                        kg.add(pair[0], k, pair[1])
        transformed_kg = kg

        # TODO remove
        with open("./Data/Test/YAGO3-10-onto-valid.nt", 'w', encoding='utf-8')as f:
            for edge in transformed_kg.edges.keys():
                for pair in transformed_kg.edges[edge]:
                    if not pair[1].startswith("\""):
                        f.write(f"<{prefix}{pair[0]}> <{prefix}{edge}> <{prefix}{pair[1]}> .\n")
                    elif k.__contains__(type_predicate):
                        f.write(f"<{prefix}{pair[0]}> <{edge}> {pair[1]} .\n")

                    else:
                        f.write(f"<{prefix}{pair[0]}> <{prefix}{edge}> {pair[1]} .\n")


    # need to ensure predicate mapping consistency, every new predicate mentioned in mappings must be in kg, even if there is no corresponding triple
    check_preds_in_graph(neg_predicate_mappings, transformed_kg)

    result = []
    for p in targets:
        # getting post normalization instances of target predicate and the negative instances from validation
        pmap = P_map(p, new_preds(p, predicate_mappings), set() , predicate_mappings, neg_predicate_mappings)
        pmap.neg_predicates = neg_preds(pmap.predicates, neg_predicate_mappings)

        # count = 0
        # fit_count = 0
        # for k,v in transformed_kg.edges.items():
        #     for pair in v:
        #         count += 1
        #         if fits_domain_range(pair[0], (pair[0], k, pair[1]), ontology, transformed_kg, pmap, type_predicate):
        #             if fits_domain_range(pair[1], (pair[0], k, pair[1]), ontology, transformed_kg, pmap, type_predicate):
        #                 fit_count += 1
        # print(ontology)
        # print(count)
        # print(fit_count)

        # exit()
        
        # print(p)
        # g = getExamplesLCWA(transformed_kg,ontology, pmap, set_size, type_predicate)
        # print(len(g))

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

        result.extend(mine_rules_for_target_predicate(g, v, pmap, transformed_kg, type_predicate, ontology, expand_fun, fits_max_depth, negative_rules, max_depth, alpha, beta, onto_valid))
        
    print(result)
    #TODO add result to csvs
    with open(rules_file, mode='w', newline='', encoding='utf-8') as datei:
        writer = csv.DictWriter(datei, fieldnames=['Body', 'Head'])
        writer.writeheader()
        writer.writerows(result)

    return

def mine_rules_for_target_predicate(g:set, v:set, pmap:P_map, kg:IncidenceList, type_predicate:str, ontology:Ontology, 
                                    expand_fun, fits_max_depth, negative_rules,  max_depth:int=3, alpha:float=0.5, beta:float=0.5, onto_safe:bool=False):
    
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


# {
#   "KG": "YAGO3-10",
#   "prefix": "http://yago-knowledge.org/resource/",
#   "rules_file": "YAGO3-10.csv",
#   "rdf_file": "YAGO3-10.nt",
#   "constraints_folder": "YAGO3-10",
#   "ontology_file": "YAGO3-10Ontology.ttl",
#   "max_body_length": "",
#   "example_set_size": "",
#   "type_predicate":  "",
#   "alpha": "",
#   "mine_negative_rules": ""
#   }

    
# {
#   "KG": "DB100K",
#   "prefix": "http://db100k.org/",
#   "rules_file": "DB100K.tsv",
#   "rdf_file": "DB100K.nt",
#   "constraints_folder": "DB100K",
#   "ontology_file": "DB100K.ttl",
#   "max_body_length": "",
#   "example_set_size": "",
#   "type_predicate":  "",
#   "alpha": "",
#   "mine_negative_rules": ""
#   }


    
   
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



    # rulelist = [Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'child', '?VAR4')},
    #     connections= {('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'mother', '?VAR4')},
    #     connections= {('?VAR3', '?VAR1'), ('?VAR4', '?VAR2')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'father', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'parent', '?VAR4')},
    #     connections= {('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'successor', '?VAR4')},
    #     connections= {('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'successor', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'spouse', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'father', '?VAR4')},
    #     connections= {('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'predecessor', '?VAR4')},
    #     connections= {('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'father', '?VAR4')},
    #     connections= {('?VAR3', '?VAR1'), ('?VAR4', '?VAR2')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'mother', '?VAR4')},
    #     connections= {('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'mother', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'child', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'successor', '?VAR4')},
    #     connections= {('?VAR3', '?VAR2'), ('?VAR4', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'child', '?VAR4')},
    #     connections= {('?VAR3', '?VAR2'), ('?VAR4', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'predecessor', '?VAR4')},
    #     connections= {('?VAR3', '?VAR1'), ('?VAR4', '?VAR2')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'predecessor', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
    #     connections= {('?VAR5', '?VAR2'), ('?VAR3', '?VAR1'), ('?VAR4', '?VAR6')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR7', 'parent', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
    #     connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR7', 'spouse', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
    #     connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR7', 'mother', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
    #     connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4'), ('?VAR7', 'father', '?VAR8')},
    #     connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR7', 'spouse', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
    #     connections= {('?VAR8', '?VAR2'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR7')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'gender', '?VAR6'), ('?VAR7', 'successor', '?VAR8'), ('?VAR3', 'gender', '?VAR4')},
    #     connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'gender', '?VAR6'), ('?VAR7', 'predecessor', '?VAR8'), ('?VAR3', 'gender', '?VAR4')},
    #     connections= {('?VAR8', '?VAR2'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR7')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'gender', '?VAR6'), ('?VAR7', 'child', '?VAR8'), ('?VAR3', 'gender', '?VAR4')},
    #     connections= {('?VAR2', '?VAR7'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR8')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR7', 'parent', '?VAR8'), ('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4')},
    #     connections= {('?VAR8', '?VAR2'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR7')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'gender', '?VAR4'), ('?VAR7', 'father', '?VAR8')},
    #     connections= {('?VAR8', '?VAR2'), ('?VAR4', '?VAR6'), ('?VAR3', '?VAR1'), ('?VAR5', '?VAR7')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'parent', '?VAR6')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'spouse', '?VAR6')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'predecessor', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'child', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'father', '?VAR6')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'mother', '?VAR6')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'successor', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'spouse', '?VAR6')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'parent', '?VAR6')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'mother', '?VAR6')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'parent', '?VAR4'), ('?VAR5', 'father', '?VAR6')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'successor', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'predecessor', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR5', '?VAR3')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'child', '?VAR6'), ('?VAR3', 'parent', '?VAR4')},
    #     connections= {('?VAR4', '?VAR1'), ('?VAR3', '?VAR6')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'spouse', '?VAR6')},
    #     connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'father', '?VAR6')},
    #     connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'gender', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
    #     connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'predecessor', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
    #     connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'child', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
    #     connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'successor', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
    #     connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'parent', '?VAR6')},
    #     connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'parent', '?VAR6')},
    #     connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'successor', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
    #     connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'spouse', '?VAR6')},
    #     connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'father', '?VAR6')},
    #     connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'predecessor', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
    #     connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'mother', '?VAR6')},
    #     connections= {('?VAR4', '?VAR5'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR5', 'child', '?VAR6'), ('?VAR3', 'spouse', '?VAR4')},
    #     connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
    #     , Rule(
    #     head= ('?VAR1', 'parent', '?VAR2'),
    #     body= {('?VAR3', 'spouse', '?VAR4'), ('?VAR5', 'mother', '?VAR6')},
    #     connections= {('?VAR4', '?VAR6'), ('?VAR3', '?VAR1')})
    #     ]
    

    # pathlist = [ Path( ('Blanche_of_Burgundy', 'parent_Mahaut_Countess_of_Artois', 'Mahaut_Countess_of_Artois'), IncidenceList(
    #     {'spouse_Charles_IV_of_France': {('Blanche_of_Burgundy', 'Charles_IV_of_France')}, 
    #      'spouse_Joan_of__vreux': {('Charles_IV_of_France', 'Joan_of__vreux')}},        
    #     {'Blanche_of_Burgundy': {'spouse_Charles_IV_of_France'}, 
    #      'Charles_IV_of_France': {'spouse_Charles_IV_of_France', 'spouse_Joan_of__vreux'},
    #        'Joan_of__vreux': {'spouse_Joan_of__vreux'}}
    #     )),

    #     Path( ('Philip_V_of_Spain', 'parent_Louis_Dauphin_of_France_son_of_Louis_XIV', 'Louis_Dauphin_of_France_son_of_Louis_XIV'), IncidenceList(
    #      {'spouse_Maria_Amalia_of_Saxony': {('Philip_V_of_Spain', 'Maria_Amalia_of_Saxony'),
    #                                          ('Charles_III_of_Spain', 'Maria_Amalia_of_Saxony')}},
    #      {'Philip_V_of_Spain': {'spouse_Maria_Amalia_of_Saxony'}, 
    #       'Maria_Amalia_of_Saxony': {'spouse_Maria_Amalia_of_Saxony'}, 
    #       'Charles_III_of_Spain': {'spouse_Maria_Amalia_of_Saxony'}}
    #     )),
    #     Path( ('Philip_V_of_Spain', 'parent_Louis_Dauphin_of_France_son_of_Louis_XIV', 'Louis_Dauphin_of_France_son_of_Louis_XIV'), IncidenceList(
    #      {'spouse_Maria_Amalia_of_Saxony': {('Philip_V_of_Spain', 'Maria_Amalia_of_Saxony')},
    #        'marriedTo_Elisabeth_Farnese': {('Maria_Amalia_of_Saxony', 'Elisabeth_Farnese')}},
    #      {'Philip_V_of_Spain': {'spouse_Maria_Amalia_of_Saxony'},
    #        'Maria_Amalia_of_Saxony': {'marriedTo_Elisabeth_Farnese', 'spouse_Maria_Amalia_of_Saxony'},
    #          'Elisabeth_Farnese': {'marriedTo_Elisabeth_Farnese'}}
    #     )), 


    #     Path( ('Philip_V_of_Spain', 'parent_Louis_Dauphin_of_France_son_of_Louis_XIV', 'Louis_Dauphin_of_France_son_of_Louis_XIV'), IncidenceList(
    #      {'spouse_Maria_Amalia_of_Saxony': {('Philip_V_of_Spain', 'Maria_Amalia_of_Saxony'), ('Charles_III_of_Spain', 'Maria_Amalia_of_Saxony')}},
    #      {'Philip_V_of_Spain': {'spouse_Maria_Amalia_of_Saxony'},
    #        'Maria_Amalia_of_Saxony': {'spouse_Maria_Amalia_of_Saxony'},
    #          'Charles_III_of_Spain': {'spouse_Maria_Amalia_of_Saxony'}}
    #     )),
    #     Path( ('Philip_V_of_Spain', 'parent_Louis_Dauphin_of_France_son_of_Louis_XIV', 'Louis_Dauphin_of_France_son_of_Louis_XIV'), IncidenceList(
    #      {'spouse_Maria_Amalia_of_Saxony': {('Philip_V_of_Spain', 'Maria_Amalia_of_Saxony')}},
    #      {'Philip_V_of_Spain': {'spouse_Maria_Amalia_of_Saxony'},
    #        'Maria_Amalia_of_Saxony': { 'spouse_Maria_Amalia_of_Saxony'}}
    #     )),
    #     ]
     



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
    
  
    paths = {Path((s, p , o), IncidenceList()) for s,p,o in g}

    # TODO call expand rule here, duplicate code

    for path in paths:
        expand_fun(rule_dict, path, kg, ontology, pmap, type_predicate, onto_safe)


    r, min_weight = find_r(R_out_dict, R_out_cov_v_cardinality, R_out_uncov_v, rule_dict, rule_weight_dict, kg, g, v, alpha, beta, pmap, fits_max_depth, max_depth)
 

    # main loop 

    while True:



        if not rule_dict or cov_g(list(R_out_dict.keys()), rule_dict, R_out_dict) == g or min_weight >= 0:
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
                expand_rule(r, rule_dict, kg, ontology, pmap, type_predicate, expand_fun, onto_safe)
            # remove handled rule
            rule_dict.pop(r)

        # find next r
        r, min_weight = find_r(R_out_dict, R_out_cov_v_cardinality, R_out_uncov_v, rule_dict, rule_weight_dict, kg, g, v, alpha, beta, pmap, fits_max_depth, max_depth)

    # TODO possibly return the whole R_out_dict or calc some metrics here 

    

    return list(rule.as_csv_dict(negative_rules) for rule in R_out_dict.keys())



def find_r(R_out_dict:dict, R_out_cov_v_cardinality:list, R_out_uncov_v:set, rule_dict:dict, rule_weight_dict:dict, kg:IncidenceList, g:set, v:set, alpha:float, beta:float, pmap:P_map, fits_max_depth,  max_depth:int):

    min_weight = np.inf
    r = None

    rules_to_remove = set()

    for rule in rule_dict.keys():
        if rule in rule_weight_dict:
            weight = rule_weight_dict[rule]
        else:
            weight = est_m_weight(rule, R_out_dict, rule_dict, kg, g, v, alpha, beta, pmap, R_out_cov_v_cardinality, R_out_uncov_v)
            rule_weight_dict[rule] = weight

        if not fits_max_depth(rule, max_depth) and (weight >= 0 or not is_valid(rule)):
            # collect hopeless rules
            rules_to_remove.add(rule)
            continue

        if weight < min_weight or (weight == min_weight and is_valid(rule)):
            r = rule
            min_weight = weight

    # remove hopeless rules, declutter rule_dict
    for rule in rules_to_remove:
        rule_dict.pop(rule)

    return r, min_weight



def expand_rule(rule, rule_dict, kg:IncidenceList, ontology:Ontology, pmap:P_map, type_predicate, expand_fun, onto_safe):
    for path in rule_dict[rule]:
        expand_fun(rule_dict, path, kg, ontology, pmap, type_predicate, onto_safe)
          

def fits_max_depth_rudik(r:Rule, max_depth):
    return len(r.body) < max_depth


"""expands given path by one from frontiers, creates straight paths in line with RuDiK"""
def expand_path_rudik(rule_dict:dict, path:Path, kg:IncidenceList, ontology:Ontology, pmap:P_map, type_predicate:str, onto_safe):

    # find  leaf, head object doesn't count
    f = path.frontiers_rudik()

    if f == None:
        print(f"no frontier for {path}")
        print(path.frontiers_rudik())
        exit()

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

                if onto_safe or fits_domain_range(e, triple, ontology, kg, pmap, type_predicate):

                    # check path.copy() -> is slow
                    new = path.copy()

                    new.graph.add(pair[0], p, pair[1])

                    r = new.rule_rudik(pmap)


                    if r in rule_dict:
                        rule_dict[r].add(new)
                    else:
                        rule_dict[r] = {new}


    return 



def fits_max_depth_branch(r:Rule, max_depth):
    pass

def expand_path_branch(path:Path, kg:IncidenceList, ontology:Ontology, pmap:P_map, type_predicate:str):
    pass






