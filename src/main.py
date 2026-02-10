import json
import pandas as pd
from rdflib.plugins.sparql.processor import SPARQLResult
from pandasql import sqldf
from rdflib import Graph, URIRef
import re
import os
import time
import shutil
import sys
from Normalization.Validation import travshacl
from Normalization.Normalization_transform import transform
from RuleMining.Rule_mining import mine_rules
from RuleMining.Util import parseGraph, parseOntology
from RuleMining.Classes import IncidenceList, Ontology

import logging

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
    kg_name = input_data['KG']
    kg_path = os.path.join('Data', 'KG', input_data['KG'])
    rules_path = os.path.join('Data', 'Rules', input_data['rules_file'])
    rdf_path = os.path.join(kg_path, input_data['rdf_file'])
    ontology_path = os.path.join('Data', 'Ontology', input_data['ontology_file'])
    predictions_folder = os.path.join('Data', 'Predictions', input_data['KG'] + "_predictions")
    constraints_folder = os.path.join('Data', 'Constraints',input_data['constraints_folder'])

    max_depth = input_data['max_body_length']
    if not max_depth:
        max_depth = 3
    set_size = input_data['example_set_size']
    if not set_size:
        set_size = 15
    type_predicate = input_data['type_predicate']
    if not type_predicate:
        type_predicate = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
    alpha = input_data['alpha']
    if not alpha:
        alpha = 0.5
    negative_rules = True if input_data["mine_negative_rules"] else False

    logger.info(f"Configuration loaded:\n "
          f"- Prefix: {prefix}\n"
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
    return prefix, rules_path, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, max_depth, set_size, type_predicate, alpha, negative_rules

def delete_existing_result(pfad):
    if os.path.exists(pfad) and os.path.isdir(pfad):
        i = True
        while i:
            user_input = input(f"\nThere already exists a result folder for this knowledge graph at '{pfad}'. Do you want to delete it and resume? (y/n) ").strip().lower()
            
            if user_input == 'y':
                shutil.rmtree(pfad)
                print("The result folder was deleted. Proceeding...\n")
                i = False
            elif user_input == 'n':
                print("The result folder was kept. Cancelling...\n")
                sys.exit()
            else:
                print("Invalid entry, try again.")


if __name__ == '__main__':
    try:
        #MAX check cwd
        cwd = os.getcwd()
        if (os.path.basename(cwd) != 'src'):
            raise RuntimeError(f"Expected working directory to be the projects 'src' folder, but got {cwd}")

        start_time = time.time()
        print("Starting symbolic prediction generation...")

        # Initialize configuration
        input_config = './Data/input.json'

        # Create logs directory if it doesn't exist
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        # Set up logging with file output and rotation
        #MAX: whats rotation?
        log_level = 'INFO'  # Default to INFO level
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        log_file = os.path.join(logs_dir, f'symbolic_predictions_{timestamp}.log')

        # Configure logging to write to both console and file
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()  # This sends output to console too
            ]
        )
        logger = logging.getLogger(__name__)

        #Initializaing from the input.json file
        prefix, rules_path, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, max_depth, set_size, type_predicate, alpha, negative_rules = initialize(input_config)


        #delete result folder
        #track time for user input
        user_input_start_time = time.time()
        result_path = f'{constraints_folder}/result_{kg_name}'
        delete_existing_result(result_path)
        user_input_end_time = time.time()

        g = Graph()
        g.parse(rdf_path, format='nt')


        # Validate SHACL constraints
        print("\nValidating results...")
        val_results = travshacl(g, constraints_folder, kg_name)

        # Normalizing enriched KG (enrichedKG obtained from symbolic predictions)
        print("\nTransforming results...")
        transformed_kg, transform_output_dir, original_predicates = transform(g,constraints_folder, prefix, kg_name)

        time_start_parse = time.time()
        kg_transformed_i_list = IncidenceList()
        parseGraph(f"{transform_output_dir}/TransformedKG_{kg_name}.nt", kg_transformed_i_list, prefix)
        o = Ontology()
        parseOntology(ontology_path, o, prefix)
        time_start_mining = time.time()
        mine_rules(kg_transformed_i_list,  original_predicates, transform_output_dir, o, rules_path, prefix, max_depth, set_size, alpha, type_predicate, negative_rules=negative_rules)

        # Print execution time
        end_time = time.time()
        print(f"\nTime to parse data: {time_start_mining - time_start_parse} s\nTime for rule mining (incl. example generation):{end_time-time_start_mining} s")
        print(f"\nTotal execution time: {end_time - start_time - (user_input_end_time - user_input_start_time):.2f} seconds")
        print("Process completed successfully!")

    except Exception as e:
        error_msg = f"Error occurred during execution: {str(e)}"
        print(f"\n{error_msg}")
        if 'logger' in locals():
            pass
            # logger.error(error_msg, exc_info=True)  # Logs the full traceback
        raise