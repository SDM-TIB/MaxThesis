import json
from rdflib import Graph, URIRef, Namespace
import os
import time
import shutil
import sys
from Normalization.Validation import travshacl
from Normalization.Normalization_transform import transform
from Normalization.Normalization import *
from Normalization.Negative_triples import get_negative_triples
from Util.Util import parseGraph, parseOntology
from Util.Classes import IncidenceList, Ontology
import logging
from main import delete_existing_result


def initialize(input_config):
    """
    Initializes the system using the configuration provided in the input file. It reads
    the configuration file, extracts necessary parameters, constructs paths for various
    files and folders, and logs the loaded configuration details.

    Args:
        input_config (str): The path to the configuration file in JSON format.

    Returns:
        tuple: A tuple containing the following elements in order:
            - prefix (str): The prefix specified in the configuration file.
            - rules (str): Path to the rules file.
            - rdf (str): Path to the RDF file.
            - path (str): Path to the knowledge graph (KG) directory.
            - predictions_folder (str): Path to the predictions folder.
            - constraints (str): Path to the constraints folder.
            - kg (str): Name of the knowledge graph (KG).
            - pca_threshold (float): PCA threshold value from the configuration file.
    """
    print(f"Reading configuration from {input_config}")
    with open(input_config, "r") as input_file_descriptor:
        input_data = json.load(input_file_descriptor)

    prefix = input_data['prefix']
    abbr = input_data['prefix-abbreviation']
    kg_name = input_data['KG']
    kg_path = os.path.join('Data', 'KG', input_data['KG'])
    rules_path = os.path.join('Data', 'Rules', input_data['rules_file'])
    rdf_path = os.path.join(kg_path, input_data['rdf_file'])
    ontology_path = os.path.join('Data', 'Ontology', input_data['ontology_file'])
    predictions_folder = os.path.join('Data', 'Predictions', input_data['KG'] + "_predictions")
    constraints_folder = os.path.join('Data', 'Constraints',input_data['constraints_folder'])

    if not input_data['max_body_length']:
        max_depth = 3
    else:
        max_depth = int(input_data['max_body_length'])
    if not input_data['example_set_size']:
        set_size = 20
    else:
        set_size = int(input_data['example_set_size'])

    type_predicate = input_data['type_predicate']
    if not type_predicate:
        type_predicate = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
    if not input_data['alpha']:
        alpha = 0.5
    else:
        alpha = float(input_data['alpha'])

    negative_rules = True if input_data["mine_negative_rules"] else False

    onto_valid = True if input_data["onto-valid"] else False

    logger.info(f"Configuration loaded:\n"
          f"- Prefix: {prefix}\n"
          f"- Prefix-abbreviation: {abbr}\n"
          f"- Rules file: {rules_path}\n"
          f"- RDF file: {rdf_path}\n"
          f"- Predictions folder: {predictions_folder}\n"
          f"- Constraints folder: {constraints_folder}\n"
          f"- maximum path length: {max_depth}\n"
          f"- example set size: {set_size}\n"
          f"- type_predicate: {type_predicate}\n"
          f"- alpha: {alpha}\n"
          f"- mining {"negative" if negative_rules else "positive"} rules\n"
    )
    return prefix, abbr, rules_path, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, max_depth, set_size, type_predicate, alpha, negative_rules, onto_valid


if __name__ == '__main__':
    try:
        #check cwd
        cwd = os.getcwd()
        if (os.path.basename(cwd) != 'src'):
            raise RuntimeError(f"Expected working directory to be the projects 'src' folder, but got {cwd}")

        start_time = time.time()

        # Initialize configuration
        input_config = './Data/input_normalization.json'

        # Create logs directory if it doesn't exist
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        # Set up logging with file output and rotation
        log_level = 'INFO'  # Default to INFO level
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        log_file = os.path.join(logs_dir, f'normalization_{timestamp}.log')

        # Configure logging to write to both console and file
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
            ]
        )
        logger = logging.getLogger(__name__)

        #Initializaing from the input.json file
        prefix, abbr, rules_path, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, max_depth, set_size, type_predicate, alpha, negative_rules, onto_valid = initialize(input_config)


        #delete result folder
        #track time for user input
        user_input_start_time = time.time()
        result_path = f'{constraints_folder}/result_{kg_name}'
        delete_existing_result(result_path)
        user_input_end_time = time.time()

        NS = Namespace(prefix)
        g = Graph()
        g.bind(abbr, NS)
        g.bind("xsd","http://www.w3.org/2001/XMLSchema/")

        # parse inputs
        parse_start = time.time()
        g.parse(rdf_path, format='nt')
        o = Ontology()
        parseOntology(ontology_path, o, prefix)

        # Validate SHACL constraints
        validation_start = time.time()
        print("\nValidating results...")
        val_results = travshacl(g, constraints_folder, kg_name)
        negative_triple_dict = get_negative_triples(g, constraints_folder, kg_name)

        #normalzation with traces
        normalize_start = time.time()
        onto_valid_log, nf1_log, nf2_log, nf3_log, nf4_log =normalize(g, o, NS, "ex", True, True, True, True, kg_name, bnode_name="Blank_Node", negative_triple_dict=negative_triple_dict)

        # Print execution time
        end_time = time.time()
        parse_time = validation_start - parse_start
        validation_time = normalize_start - validation_start
        normalize_time = end_time - normalize_start
        time_total = end_time - start_time - (user_input_end_time - user_input_start_time)
        print(f"\nTime to parse data: {parse_time} s")
        print(f"\nTime to validate constraints: {validation_time} s")
        print(f"\nTime to normalize KG: {normalize_time} s")
        print(f"\nTotal execution time: {time_total} s")
        print(f"\nNORMALIZATION INFO:\n\tOntology validation removed {onto_valid_log} triples.")
        print(f"\tNF1: {nf1_log} violation{"s" if nf1_log > 1 else ""}")
        print(f"\tNF2: {nf2_log} violation{"s" if nf2_log > 1 else ""}")
        print(f"\tNF3: {nf3_log} violation{"s" if nf3_log > 1 else ""}")
        print(f"\tNF4: {nf4_log} violation{"s" if nf4_log > 1 else ""}")

        log_data = {"runtime": time_total, 
                    "parse_time": parse_time, 
                    "validation_time": validation_time, 
                    "normalization_time": normalize_time, 
                    "Ontology_validation_triples_removed": onto_valid_log, 
                    "NF1_triples_invalidated": nf1_log,
                    "NF2_triples_invalidated": nf2_log,
                    "NF3_triples_invalidated": nf3_log,
                    "NF4_triples_invalidated": nf4_log
                    }
        logger.info(json.dumps(log_data, indent=4))
        logger.info("Process completed successfully!")
    except Exception as e:
        error_msg = f"Error occurred during execution: {str(e)}"
        print(f"\n{error_msg}")
        if 'logger' in locals():
            logger.error(error_msg, exc_info=True)  # Logs the full traceback
        raise
