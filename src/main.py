import json
import pandas as pd
from rdflib.plugins.sparql.processor import SPARQLResult
from pandasql import sqldf
from rdflib import Graph, URIRef
import re
import os
import time
from Normalization.Validation import travshacl
from Normalization.Normalization_transform import transform
from RuleMining.Rule_mining import mine_rules

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
    pca_threshold = input_data['pca_threshold']

    logger.info(f"Configuration loaded:\n "
          f"- Prefix: {prefix}\n"
          f"- Rules file: {rules_path}\n"
          f"- RDF file: {rdf_path}\n"
          f"- Predictions folder: {predictions_folder}\n"
          f"- Constraints folder: {constraints_folder}\n"
          f"- PCA Threshold: {pca_threshold}")

    return prefix, rules_path, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, pca_threshold



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
        prefix, rules_path, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, pca_threshold = initialize(input_config)



        g = Graph()
        g.parse(rdf_path, format='nt')


        # Validate SHACL constraints
        print("\nValidating results...")
        val_results = travshacl(g, constraints_folder, kg_name)

        # Normalizing enriched KG (enrichedKG obtained from symbolic predictions)
        print("\nTransforming results...")
        transformed_kg, transform_output_dir, original_predicates = transform(g,constraints_folder, kg_name)


        #MAX
        mine_rules(transformed_kg, original_predicates, transform_output_dir, ontology_path, rules_path, prefix, 3, 100)

        # Print execution time
        end_time = time.time()
        print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")
        print("Process completed successfully!")

    except Exception as e:
        error_msg = f"Error occurred during execution: {str(e)}"
        print(f"\n{error_msg}")
        if 'logger' in locals():
            logger.error(error_msg, exc_info=True)  # Logs the full traceback
        raise