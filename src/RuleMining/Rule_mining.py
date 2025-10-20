from rdflib import Graph, URIRef, BNode, Literal, Namespace
import json
import csv
import numpy as np
import warnings



def mine_rules(transformed_kg:Graph, targets:set, transform_output_dir:str, ontology_path:str, rules_file:str, prefix:str, max_depth:int=3, set_size:int=100,
        type_predicate:str="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"):
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
        predicates = [k for k, v in predicate_mappings.items() if v == p]
        neg_predicates = [k for k, v in neg_predicate_mappings.items() if v in predicates]


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
        result.extend(mine_rules_for_target_predicate(np.array(g), np.array(v), p, predicates, neg_predicates, transformed_kg, prefix, type_predicate, ontology_path, max_depth))

        print(f"----------result--------------\n{result}\n--------------------------------------\n")
    #TODO add result to csvs
    with open(rules_file, mode='w', newline='', encoding='utf-8') as datei:
        writer = csv.writer(datei)
        writer.writerows(result)
        print(rules_file)


    # 
    return

def mine_rules_for_target_predicate(g:np.ndarray, v:np.ndarray, target:URIRef, predicates:list[str], neg_predicates:list[str],
                                    transformed_kg:Graph, prefix:str, type_predicate:str, ontology_path:str,  max_depth:int=3):
    """


    Args:
        G -- generation set
        V -- validation set
        predicates -- all post normalization versions of the original predicates rules are mined for
        neg_predicates -- 
        transformed_kg -- knowledge graph to mine rules for
        ontology_path -- path to given ontology
        prefix -- prefix
        max_depth -- max length of paths in graph corresponding to rule length

    Returns:
        R_out -- mined rules for the target predicate
    """

    kg = transformed_kg
    R_out = []
    frontiers = {}
    candidates = {}


    #TODO rudik
    return [["fr", "df", "dg"], ["wf", "fll", "rgnrpg"]]


#TODO help function get_domain/range

#TODO help function weight

#TODO help function coverage, unbounded coverage

#TODO help function expand_frontiers(list of current nodes)