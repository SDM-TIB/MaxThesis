import json
import os
import re
from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import SH, RDF
from typing import Dict, List, Tuple, Set, Optional

from Util.Classes import removePrefix, addPrefix


class TriplePattern:
    def __init__(self, predicate: URIRef, object_value: URIRef, in_filter: bool = False, is_not_exists: bool = False):
        self.predicate = predicate
        self.object = object_value
        self.in_filter = in_filter
        self.is_not_exists = is_not_exists

    def __str__(self):
        return f"({self.predicate}, {self.object}, {'NOT ' if self.is_not_exists else ''}FILTER)" if self.in_filter else f"({self.predicate}, {self.object})"
    def __repr__(self):
        return f"({self.predicate}, {self.object}, {'NOT ' if self.is_not_exists else ''}FILTER)" if self.in_filter else f"({self.predicate}, {self.object})"


def process_shacl_shapes(shacl_file: str) -> Dict[str, List[TriplePattern]]:
    """
    Processes the provided SHACL (Shapes Constraint Language) file to extract and return
    a dictionary of SHACL NodeShapes and their associated SPARQL queries for negative triple identification. The
    function parses the SHACL file into a graph, identifies NodeShapes, and retrieves
    any SPARQL queries and builds the negative triple SPARQL-queries.

    Args:
        shacl_file (str): Path to the SHACL Turtle file to be processed.

    Returns:
        Dict[str, str]: A dictionary mapping SHACL NodeShapes to SPARQL-queries.
    """

    def get_negation_query(query):

        def strip_negation_triple(s):
            return s.split('#')[0][1:].strip().replace("\r","")
        
        negates = re.findall(r'\n.*?#.*\*negate\*', query)
        if not negates:
            return None
        construct = ""
        for negate in negates:
            construct += strip_negation_triple(negate) #remove newline at beginning and comment in the end
        match_where = re.search(r'[Ww][Hh][Ee][Rr][Ee]', query)
        match_select = re.search(r'[Ss][Ee][Ll][Ee][Cc][Tt]', query)
        where_bracket = query[match_where.start():]
        pre_select = query[:match_select.start()]
        return f"""{pre_select.strip()}\nCONSTRUCT  {"{"+ construct.strip() + "}"}\n{where_bracket.strip()}""".replace("\r", "")

    shapes_graph = Graph()
    shapes_graph.parse(shacl_file, format='turtle')

    negative_triple_queries = {}

    for shape in shapes_graph.subjects(RDF.type, SH.NodeShape):
        for sparql in shapes_graph.objects(shape, SH.sparql):
            query = str(shapes_graph.value(sparql, SH.select))
            negation_query = get_negation_query(query)
            if negation_query:
                negative_triple_queries[str(shape)] = negation_query

    return negative_triple_queries


def process_validation_report(report_file: str) -> List[Tuple[str, str]]:
    """
    Processes a SHACL validation report and extracts violations as tuples containing
    focus node and source shape.

    The function reads the validation report file, adds necessary RDF prefixes, parses
    the data into a graph, and extracts all validation results. From these results, it
    collects the focus node and source shape for each violation.

    Args:
        report_file (str): Path to the SHACL validation report file in Turtle format.

    Returns:
        List[Tuple[str, str]]: A list of tuples where each tuple contains the focus
        node and source shape for a validation violation.
    """

    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()

    prefixes = """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        @prefix : <http://example.org/> .
    """
    modified_content = prefixes + content

    report_graph = Graph()
    report_graph.parse(data=modified_content, format='turtle')

    violations = []
    validation_results = list(report_graph.subjects(RDF.type, SH.ValidationResult))

    for result in validation_results:
        focus_node = report_graph.value(result, SH.focusNode)
        source_shape = report_graph.value(result, SH.sourceShape)
        if focus_node and source_shape:
            violations.append((str(focus_node), str(source_shape)))

    return violations


def get_negative_triples(kg: Graph, constraints_folder: str, prefix,  kg_name: str = None) -> Tuple[Graph, str]:
    """
    Transforms a given knowledge graph (KG) based on a series of predicate-object transformations,
    SHACL constraints, and violation reports. The transformation involves modifying triples in the graph as
    pre defined patterns and saving the results to the appropriate output files.

    Args:
        kg: The input RDF graph to be transformed.
        kg_name: The name associated with the KG. If not provided, it is derived from the current directory.

    Returns:
        Graph: The final transformed RDF graph after applying all transformations.

    Raises:
        Exception: If any error occurs during the transformation process, it is raised for troubleshooting.
    """

    try:
        # If kg_name is not provided, try to determine it from current directory
        if kg_name is None:
            kg_name = os.path.basename(os.getcwd())
            print(f"No kg_name provided, using '{kg_name}' derived from current directory.")


        # Setup for constraint validation
        constraints_result_dir = f"{constraints_folder}/result_{kg_name}"
        shapes_file = f"{constraints_folder}/{kg_name}.ttl"
        validation_report = f"{constraints_result_dir}/validationReport.ttl"

        print("Processing SHACL constraints...")
        constraint_patterns = process_shacl_shapes(shapes_file)
        print(f"Found patterns for {len(constraint_patterns)} shapes")

        print("Processing validation report...")
        violations = process_validation_report(validation_report)
        print(f"Found {len(violations)} violations")

        negative_triple_dict = {}
        for k in constraint_patterns.keys():
            triples = set()
            res = kg.query(constraint_patterns[k])
            for row in res:
                triples.add(row)
            negative_triple_dict[k] = triples
        return negative_triple_dict

    except Exception as e:
        print(f"\nError during transformation: {str(e)}")
        raise