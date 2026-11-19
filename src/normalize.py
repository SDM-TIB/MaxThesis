import json
from rdflib import Graph, URIRef, Namespace, term
import os
import time
import shutil
import sys
from Normalization.Validation import travshacl
from Normalization.Normalization import normalize
from Normalization.Negative_triples import get_negative_triples
from Util.Util import parseGraph, parseOntology
from Util.Classes import IncidenceList, Ontology
import logging
from main import delete_existing_result

# {
# "KG": "musicKG-test-normalization",
# "prefix": "http://example.org/",
# "prefix-abbreviation":"ex",
# "other_prefixes": {
#     "http://www.w3.org/2004/02/skos/core":"skos",
#     "https://w3id.org/sem-disnet/ontology#":"disnet-o",
#     "http://www.w3.org/ns/prov#": "prov",
#     "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
#     "http://www.w3.org/ns/rdf-star#": "rdf-star",
#     "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
#     "http://www.w3.org/2002/07/owl#": "owl",
#     "http://www.w3.org/2001/XMLSchema#": "xsd",
#     "http://purl.org/dc/terms/": "dcterms",
#     "http://purl.org/vocab/vann/":"vann",
#     "https://go.drugbank.com/drugs/": "drugbank",
#     "https://omim.org/entry/":"mim",
#     "http://identifiers.org/ensembl:":"ensembl",
#     "http://www.ebi.ac.uk/efo/":"efo",
#     "http://id.nlm.nih.gov/mesh/":"mesh",
#     "http://purl.obolibrary.org/obo/":"obo",
#     "https://www.uniprot.org/uniprotkb/":"uniprot",
#     "https://www.ebi.ac.uk/ols4/ontologies/ordo/":"ORDO",
#     "http://example.org/resource":"resource",
#     "http://bio2rdf.org/ctd_vocabulary:":"ctd_vocabulary",
#     "http://purl.bioontology.org/ontology/ICD10CM/":"ICD10CM",
#     "http://purl.bioontology.org/ontology/ICD10/":"ICD10",
#     "http://purl.bioontology.org/ontology/ICD9CM/":"ICD9CM",
#     "http://purl.bioontology.org/ontology/RXNORM/":"RXNORM",
#     "http:example.org/ncbigene":"ncbigene"
# },
# "rdf_file": "musicKG-test-normalization.nt",
# "constraints_folder": "musicKG-test-normalization",
# "ontology_file": "musicKGOntology.ttl",
# "onto-valid": "",
# "nf1": "F",
# "nf2": "F",
# "nf3": "F",
# "nf4": "F"
# }


# {
# "KG": "FrenchRoyalty",
# "prefix": "http://FrenchRoyalty.org/",
# "prefix-abbreviation":"fr",
# "other_prefixes": {},
# "rdf_file": "FrenchRoyalty.nt",
# "constraints_folder": "FrenchRoyalty",
# "ontology_file": "ontology_FrenchRoyalty.ttl",
# "onto-valid": "F",
# "nf1": "",
# "nf2": "",
# "nf3": "",
# "nf4": ""
# }

# {
# "KG": "musicKG-test-normalization",
# "prefix": "http://example.org/",
# "prefix-abbreviation":"ex",
# "other_prefixes": {},
# "rdf_file": "musicKG-test-normalization.nt",
# "constraints_folder": "musicKG-test-normalization",
# "ontology_file": "musicKGOntology.ttl",
# "onto-valid": "",
# "nf1": "",
# "nf2": "",
# "nf3": "",
# "nf4": ""
# }


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
    input_prefix_dict = input_data['other_prefixes']
    input_prefix_dict[prefix] = abbr
    general_prefix_dict = {"http://www.w3.org/ns/prov#": "prov", "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf", "http://www.w3.org/ns/rdf-star#": "rdf-star", "http://www.w3.org/2000/01/rdf-schema#": "rdfs", "http://www.w3.org/2002/07/owl#": "owl", "http://www.w3.org/2001/XMLSchema/":"xsd"}
    for k,v in general_prefix_dict.items():
        if k not in input_prefix_dict:
            input_prefix_dict[k]=v

    kg_name = input_data['KG']
    kg_path = os.path.join('Data', 'KG', input_data['KG'])
    rdf_path = os.path.join(kg_path, input_data['rdf_file'])
    ontology_path = os.path.join('Data', 'Ontology', input_data['ontology_file'])
    predictions_folder = os.path.join('Data', 'Predictions', input_data['KG'] + "_predictions")
    constraints_folder = os.path.join('Data', 'Constraints',input_data['constraints_folder'])



    type_predicate = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'

    onto_valid = False if input_data["onto-valid"] else True
    nf1 = False if input_data["nf1"] else True
    nf2 = False if input_data["nf2"] else True
    nf3 = False if input_data["nf3"] else True
    nf4 = False if input_data["nf4"] else True
    logger.info(f"Configuration loaded:\n"
          f"- Prefix: {prefix}\n"
          f"- Prefix-abbreviation: {abbr}\n"
          f"- RDF file: {rdf_path}\n"
          f"- Predictions folder: {predictions_folder}\n"
          f"- Constraints folder: {constraints_folder}\n"
          f"- type_predicate: {type_predicate}\n"
          f"- {"NOT " if not onto_valid else ""}performing ontology validation.\n"
          f"- Normalizsing to these NFs: {"NF1 " if nf1 else ""}{"NF2 " if nf2 else ""}{"NF3 " if nf3 else ""}{"NF4 " if nf4 else ""}\n\n"
    )
    return prefix, abbr, input_prefix_dict, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, type_predicate, onto_valid, nf1, nf2, nf3, nf4


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
        prefix, abbr, prefix_dict, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, type_predicate, onto_valid, nf1, nf2, nf3, nf4 = initialize(input_config)

        #delete result folder
        #track time for user input
        user_input_start_time = time.time()
        result_path = f'{constraints_folder}/result_{kg_name}'
        delete_existing_result(result_path)
        user_input_end_time = time.time()

        # TODO bind all prefixes to graph
        NS = Namespace(prefix)
        g = Graph()
        g.bind(abbr, NS)
        for p,a in prefix_dict.items():
            if a == abbr:
                continue
            g.bind(a,p)


        # parse inputs
        parse_start = time.time()
        g.parse(rdf_path, format='nt')
        o = Ontology()
        parseOntology(ontology_path, o, prefix, abbr, prefix_dict)
        # Validate SHACL constraints
        validation_start = time.time()
        print("\nValidating results...")
        val_results = travshacl(g, constraints_folder, kg_name)
        negative_triple_dict = get_negative_triples(g, constraints_folder, kg_name)
        print(negative_triple_dict)
        #normalzation with traces
        normalize_start = time.time()
        onto_valid_log, nf1_log, nf2_log, nf3_log, nf4_log, nf1_time, nf2_time, nf3_time, nf4_time =normalize(g, o, NS, abbr,prefix_dict,onto_valid,nf1,nf2,nf3,nf4, kg_name, bnode_name="Blank_Node", negative_triple_dict=negative_triple_dict)

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
        if nf1_log:
            print(f"\tNF1: {nf1_log} violation{"s" if nf1_log > 1 else ""}")
        if nf2_log:
            print(f"\tNF2: {nf2_log} violation{"s" if nf2_log > 1 else ""}")
        if nf3_log:
            print(f"\tNF3: {nf3_log} violation{"s" if nf3_log > 1 else ""}")
        if nf4_log:
            print(f"\tNF4: {nf4_log} violation{"s" if nf4_log > 1 else ""}")

        log_data = {"runtime": time_total, 
                    "parse_time": parse_time, 
                    "validation_time": validation_time, 
                    "normalization_time": normalize_time, 
                    "Ontology_validation_triples_removed": onto_valid_log, 
                    "NF1_triples_invalidated": nf1_log,
                    "NF2_triples_invalidated": nf2_log,
                    "NF3_triples_invalidated": nf3_log,
                    "NF4_triples_invalidated": nf4_log,
                    "NF1_runtime": nf1_time,
                    "NF2_runtime": nf2_time,
                    "NF3_runtime": nf3_time,
                    "NF4_runtime": nf4_time
                    }
        logger.info(json.dumps(log_data, indent=4))
        logger.info("Process completed successfully!")
    except Exception as e:
        error_msg = f"Error occurred during execution: {str(e)}"
        print(f"\n{error_msg}")
        if 'logger' in locals():
            logger.error(error_msg, exc_info=True)  # Logs the full traceback
        raise
