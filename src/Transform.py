###################
#
# this file is just used for developing, will not be part of final product
#
####################

import numpy as np
import json
import pandas as pd
import rdflib
from rdflib.plugins.sparql.processor import SPARQLResult
from pandasql import sqldf
from rdflib import Graph, URIRef
import re
import os
import time
from Normalization.Validation import travshacl
from Normalization.Normalization_transform import transform
from RuleMining.Rule_mining import mine_rules
from RuleMining.Classes import removePrefix
import csv
import logging
import shutil
import sys

def convert_nt_file_with_prefix(input_file, output_file, prefix):
    with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'w', encoding='utf-8') as f_out:
        for line in f_in:
            if line.strip() == "":
                continue  # Überspringe leere Zeilen

            parts = line.split()

            if len(parts) < 3:
                print(f"Warnung: Ungültige Zeile gefunden (zu wenige Teile): {line}")
                continue

            # Präfix zu Subjekt hinzufügen
            parts[0] = f"<{prefix}{parts[0]}>"

            # Präfix zu Prädikat hinzufügen
            cutoff = parts[1].find("_")
            if cutoff > -1:
                parts[1] = f"<{prefix}{parts[1][0:cutoff]}>"
            else:
                parts[1] = f"<{prefix}{parts[1]}>"
            # Präfix zu Objekt hinzufügen, wenn es ein URI ist
            parts[2] = f"<{prefix}{parts[2]}>"

            # Zeile mit Punkt abschließen
            if not parts[-1].endswith('.'):
                parts[-1] += '.'

            f_out.write(' '.join(parts) + '\n')


# def initialize(input_config):
#     """
#     Initializes the system using the configuration provided in the input file. It reads
#     the configuration file, extracts necessary parameters, constructs paths for various
#     files and folders, and logs the loaded configuration details.

#     Args:
#         input_config (str): The path to the configuration file in JSON format.

#     Returns:
#         tuple: A tuple containing the following elements in order:
#             - prefix (str): The prefix specified in the configuration file.
#             - rules (str): Path to the rules file.
#             - rdf (str): Path to the RDF file.
#             - path (str): Path to the knowledge graph (KG) directory.
#             - predictions_folder (str): Path to the predictions folder.
#             - constraints (str): Path to the constraints folder.
#             - kg (str): Name of the knowledge graph (KG).
#             - pca_threshold (float): PCA threshold value from the configuration file.
#     """
#     print(f"Reading configuration from {input_config}")
#     with open(input_config, "r") as input_file_descriptor:
#         input_data = json.load(input_file_descriptor)

#     prefix = input_data['prefix']
#     kg_name = input_data['KG']
#     kg_path = os.path.join('Data', 'KG', input_data['KG'])
#     rules_path = os.path.join('Data', 'Rules', input_data['rules_file'])
#     rdf_path = os.path.join(kg_path, input_data['rdf_file'])
#     ontology_path = os.path.join('Data', 'Ontology', input_data['ontology_file'])
#     predictions_folder = os.path.join('Data', 'Predictions', input_data['KG'] + "_predictions")
#     constraints_folder = os.path.join('Data', 'Constraints',input_data['constraints_folder'])
#     pca_threshold = input_data['pca_threshold']

#     logger.info(f"Configuration loaded:\n "
#           f"- Prefix: {prefix}\n"
#           f"- Rules file: {rules_path}\n"
#           f"- RDF file: {rdf_path}\n"
#           f"- Predictions folder: {predictions_folder}\n"
#           f"- Constraints folder: {constraints_folder}\n"
#           f"- PCA Threshold: {pca_threshold}")

#     return prefix, rules_path, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, pca_threshold


# def delete_existing_result(pfad):
#     if os.path.exists(pfad) and os.path.isdir(pfad):
#         i = True
#         while i:
#             user_input = input(f"There already exists a result folder for this knowledge graph at '{pfad}'. Do you want to delete it and resume? (y/n) ").strip().lower()
            
#             if user_input == 'y':
#                 shutil.rmtree(pfad)
#                 print("The result folder was deleted. Proceeding...\n")
#                 i = False
#             elif user_input == 'n':
#                 print("The result folder was kept. Cancelling...\n")
#                 sys.exit()
#             else:
#                 print("Invalid entry, try again.")


# def r_sparql(r:list):
#     return " ".join(f"{t[0]} <{t[1]}> {t[2]} ." for t in r)
            
            


# if __name__ == '__main__':
#     try:
#         #MAX check cwd
#         cwd = os.getcwd()
#         if (os.path.basename(cwd) != 'src'):
#             raise RuntimeError(f"Expected CWD to be the projects 'src' folder, but got {cwd}")

#         start_time = time.time()
#         print("Starting symbolic prediction generation...")

#         # Initialize configuration
#         input_config = './Data/input.json'

#         # Create logs directory if it doesn't exist
#         logs_dir = 'logs'
#         if not os.path.exists(logs_dir):
#             os.makedirs(logs_dir)

#         # Set up logging with file output and rotation
#         #MAX: whats rotation?
#         log_level = 'INFO'  # Default to INFO level
#         timestamp = time.strftime('%Y%m%d-%H%M%S')
#         log_file = os.path.join(logs_dir, f'symbolic_predictions_{timestamp}.log')

#         # Configure logging to write to both console and file
#         logging.basicConfig(
#             level=getattr(logging, log_level),
#             format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#             handlers=[
#                 logging.FileHandler(log_file),
#                 logging.StreamHandler()  # This sends output to console too
#             ]
#         )
#         logger = logging.getLogger(__name__)

#         #Initializaing from the input.json file
#         prefix, rules_path, rdf_path, kg_path, ontology_path, predictions_folder, constraints_folder, kg_name, pca_threshold = initialize(input_config)

#             #delete result folder
#         #track time for user input
#         user_input_start_time = time.time()
#         result_path = f'{constraints_folder}/result_{kg_name}'
#         delete_existing_result(result_path)
#         user_input_end_time = time.time()

#         g = Graph()
#         g.parse(rdf_path, format='nt')
#         predicates = []

#         set_g = np.array([(rdflib.term.URIRef('http://example.org/Eric_Clapton'), rdflib.term.URIRef('http://example.org/The_Beatles')), (rdflib.term.URIRef('http://example.org/The_Beatles'), rdflib.term.URIRef('http://example.org/Eric_Clapton')), (rdflib.term.URIRef('http://example.org/Sting'), rdflib.term.URIRef('http://example.org/Dire_Straits'))])
#         rules = []
#         rules.append([("?a","http://example.org/hasAlbum","?c"),("?c","http://example.org/isGenre","?d"),("?b","http://example.org/hasAlbum","?e"),("?e","http://example.org/isGenre","?d")])
#         rules.append([("?a","http://example.org/collaboratedWith","?c")])


#         filter_g = "||".join(f"(?a = <{pred[0]}> && ?b = <{pred[1]}>)" for pred in set_g)

#         rules_q = "UNION".join(f"{{{r_sparql(r)}}}" for r in rules)

#         query = f""" SELECT (COUNT(*) AS ?count)
#                     WHERE{{
#                     {rules_q}
#                     FILTER({filter_g})
#                     }}
#                     """

#         print(query)

#         for row in g.query(query):
#             print(row[0])


       
#     except Exception as e:
#         error_msg = f"Error occurred during execution: {str(e)}"
#         print(f"\n{error_msg}")
#         if 'logger' in locals():
#             logger.error(error_msg, exc_info=True)  # Logs the full traceback
#         raise



     
def csv_to_nt(csv_file, nt_file, prefix='http://example.org/'):
    with open(csv_file, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        
        with open(nt_file, 'w', newline='', encoding='utf-8') as ntfile:
            for row in reader:
                s,p,o = row
                if s == "" or p == "" or o == "":
                    continue

                s = s.replace(" ", "_")


                p = p.replace(" ", "_")
                if p == "#type":
                    p = f"<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
                else:
                    p = f"<{prefix}{p}>"


                o = o.replace(" ", "_")
                if o.isdigit():
                    o = f"\"{o}\"^^<http://www.w3.org/2001/XMLSchema#/int>"
                else:
                    o = f"<{prefix}{o}>"


                out = f"<{prefix}{s}> {p} {o} .\n"
                out = out.replace("’","%27")
                out = out.replace("'","%27")

                ntfile.write(out)


    return



def nt_to_txt(input_file, output_file, prefix):
    try:
        with open(input_file, 'r', encoding='utf-8') as nt_file, open(output_file, 'w', encoding='utf-8') as txt_file:
            for line in nt_file:
                # Entfernen von Kommentaren und leeren Zeilen
                line = line.strip()
                if not line or line.startswith('#'):
                    continue



                # Trennen in Subjekt, Prädikat und Objekt
                parts = line.split(' ')

                
                subject = removePrefix(parts[0], prefix)
                predicate = removePrefix(parts[1], prefix)
                obj = removePrefix(parts[2], prefix)

                # Schreiben in die TXT-Datei mit Tabulator als Trennzeichen
                txt_file.write(f"{subject}\t{predicate}\t{obj}\n")

        print(f"Konvertierung abgeschlossen. Die tab-separierte Datei wurde als '{output_file}' gespeichert.")

    except FileNotFoundError:
        print(f"Die Datei '{input_file}' wurde nicht gefunden.")
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

def remove_lines_with_string(input_filename, output_filename, s):
    with open(input_filename, 'r', encoding='utf-8') as infile, open(output_filename, 'w', encoding='utf-8') as outfile:
        for line in infile:
            write = True
            for string_to_remove in s:
                if string_to_remove in line:
                    write = False
            if write:
                l = line.replace("/entity", "")
                outfile.write(l)

def add_type_person(input_filename, output_filename):
    with open(input_filename, 'r', encoding='utf-8') as infile, open(output_filename, 'a', encoding='utf-8') as outfile:

        for line in infile:
            l = f"<{line.split()[0]}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://FrenchRoyalty.org/Person> .\n"
            outfile.write(l)



import random

def copy_file_with_random_exclusion(source_file, target_file, search_string):
    with open(source_file, 'r', encoding='utf-8') as src, open(target_file, 'w', encoding='utf-8') as tgt:
        for line in src:
            if search_string in line:
                if random.random() < 0.10:
                    continue  
            tgt.write(line)


if __name__== '__main__':
    csvpath = "./Data/KG/musicKG/musicKG.csv"

    ntpath = "./Data/KG/SynthLC_1000/SynthLC_1000.nt"
    txtpath = "./Data/KG/SynthLC_1000/SynthLC_1000.txt"
    outpath = "./Data/KG/FrenchRoyalty/FrenchRoyalty.nt"

    #nt_to_txt(ntpath, txtpath, "http://synthetic-LC.org/")
    #csv_to_nt(csvpath, ntpath)
    #remove_lines_with_string(ntpath, outpath, ["/type"])
    #add_type_person("./Data/KG/FrenchRoyalty/missing.txt", outpath)
    for i in range(5):
        copy_file_with_random_exclusion(ntpath, f"./Data/KG/SynthLC_1000/SynthLC_1000_10p_{i+1}.nt", "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>")
        nt_to_txt(f"./Data/KG/SynthLC_1000/SynthLC_1000_10p_{i+1}.nt", f"./Data/KG/SynthLC_1000/SynthLC_1000_10p_{i+1}.txt", "http://synthetic-LC.org/")

    for i in range(5):
        copy_file_with_random_exclusion("./Data/KG/FrenchRoyalty/FrenchRoyalty.nt", f"./Data/KG/FrenchRoyalty/FrenchRoyalty_10p_{i+1}.nt", "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>")
        nt_to_txt(f"./Data/KG/FrenchRoyalty/FrenchRoyalty_10p_{i+1}.nt", f"./Data/KG/FrenchRoyalty/FrenchRoyalty_10p_{i+1}.txt", "http://FrenchRoyalty.org/")