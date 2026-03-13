###################
#
# this file is just used for developing, will not be part of final product
#
####################

from pandasql import sqldf
import os
from Normalization.Validation import travshacl
from Normalization.Normalization_transform import transform
from RuleMining.Rule_mining import mine_rules
from RuleMining.Classes import removePrefix
import csv

import random

  
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

def txt_to_nt(input_file, output_file, prefix):
    
    with open(input_file, 'r', encoding='utf-8') as txt_file, open(output_file, 'w', encoding='utf-8') as nt_file:
        for line in txt_file:
            # Entfernen von Kommentaren und leeren Zeilen
            line = line.strip()
            if not line or line.startswith('#'):
                continue



            # Trennen in Subjekt, Prädikat und Objekt
            parts = line.split()

            
            subject = f"<{prefix}{parts[0]}>"
            predicate = f"<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>" if parts[1] == "type" else f"<{prefix}{parts[1]}>" 
            obj = f"<{prefix}{parts[2]}>"

            # Schreiben in die NT-Datei mit space als Trennzeichen
            nt_file.write(f"{subject} {predicate} {obj} .\n")

    print(f"Konvertierung abgeschlossen. Die tab-separierte Datei wurde als '{output_file}' gespeichert.")

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

def copy_file_with_random_exclusion(source_file, target_file, search_string):
    with open(source_file, 'r', encoding='utf-8') as src, open(target_file, 'w', encoding='utf-8') as tgt:
        for line in src:
            if search_string in line:
                if random.random() < 0.10:
                    continue  
            tgt.write(line)

def transform_dbp_ontology(infile, temp, outfile, dict):
    with open(infile, 'r', encoding='utf-8') as inf, open(temp, 'w', encoding='utf-8') as outf:
        block = []
        end = False
        eq = False
        wiki = None
        for line in inf:
            if line.__contains__(":comment"):
                continue
            if line.__contains__("owl:Class"):
                if not line.__contains__("wikidata"):
                    block.append(line)
            if block:
                block.append(line)
                if line.__contains__("equivalentClass"):
                    eq = True
                if eq and line.__contains__("wikidata:"):
                    s = line.split()
                    wiki = next(i for i in s if i.__contains__("wikidata:"))
                    print(wiki.split(":")[1])
                if line.__contains__("."):
                    end = True
            if not block:
                outf.write(line)
            
            if end:
                l = block[0].split()
                if wiki:
                    for i in range(len(l)):
                        if l[i].__contains__("dbo:"):
                            dict[l[i]] = wiki
                            l[i] = wiki
                            

                outf.write(" ".join(l))
                outf.write("\n")
                for li in block[2:]:
                    outf.write(f"{li}")
                #outf.write("\n")
                block = []
                wiki = None
                end = False
                eq = False

    with open(temp, 'r', encoding='utf-8') as inf, open(outfile, 'w', encoding='utf-8') as outf:
        for line in inf:
            if line.__contains__("Domain is unrestricted since Organization is Agent but City is Place. "):
                continue
            
            for key in dict.keys():
                if line.__contains__(f"{key} ") or line.__contains__(f"{key}."):
                    line = line.replace(key, dict[key])
                    break
            outf.write(line)

def triple_ttl_to_nt(infile, outfile):
    with open(infile, 'r', encoding='utf-8') as ttl, open(outfile, 'w', encoding='utf-8') as nt:
        for line in ttl:
            if not line:
                continue
            if line.startswith(("@", "#")):
                continue

            s = line.split("\t")
            for i in range(len(s)):
                s[i] = s[i].removeprefix("<").removesuffix(">")
                if s[i].__contains__("^^"):
                    s[i] = s[i].split("^^")[0]
            nt.write("\t".join(s))

def add_types_to_nt(nt, types, out, classes):
        with open(nt, 'r', encoding='utf-8') as nt, open(types, 'r', encoding='utf-8') as types, open(out, 'w', encoding='utf-8') as out:
            entities = set()
            handled_entities = set()
            for line in nt:
                out.write(line)
                s = line.split(" ")
                entities.add(s[0])
                entities.add(s[2])

            print(f"found {len(entities)} entities")
            c = 0
            for line in types:
                s = line.split(" ")
                if s[0] in entities and s[2] in classes:
                    handled_entities.add(s[0])
                    c += 1
                    out.write(f"{s[0]} <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> {s[2].removesuffix("\n")} .\n")
            print(c)

def add_classes_to_ontology(tax, on, out):
    with open(tax, 'r', encoding='utf-8') as tax, open(on, 'r', encoding='utf-8') as on, open(out, 'w', encoding='utf-8') as out:
        classes = {"<http://yago-knowledge.org/resource/wordnet_person_100007846>", "<http://yago-knowledge.org/resource/wordnet_organization_108008335>", "<http://yago-knowledge.org/resource/wordnet_location_100027167>", "<http://yago-knowledge.org/resource/wordnet_language_106282651>", "<http://yago-knowledge.org/resource/wordnet_city_108524735>", "<http://yago-knowledge.org/resource/wordnet_university_108286569>",
                   "<http://yago-knowledge.org/resource/yagoLegalActor>", "owl:Thing","<http://yago-knowledge.org/resource/wordnet_sex_105006898>","<http://yago-knowledge.org/resource/yagoPermanentlyLocatedEntity>","<http://yago-knowledge.org/resource/yagoGeoEntity>","rdfs:Class","<http://yago-knowledge.org/resource/wordnet_actor_109765278>",
                   "<http://yago-knowledge.org/resource/wordnet_movie_106613686>","<http://yago-knowledge.org/resource/wordnet_event_100029378>","<http://yago-knowledge.org/resource/yagoLegalActorGeo>","<http://yago-knowledge.org/resource/wordnet_award_106696483>","<http://yago-knowledge.org/resource/wordnet_editor_110044879>","<http://yago-knowledge.org/resource/wordnet_country_108544813>",
                   "<http://yago-knowledge.org/resource/wordnet_organization_108008335>", "<http://yago-knowledge.org/resource/wordnet_administrative_district_108491826>", "<http://yago-knowledge.org/resource/yagoURL>"}
        for line in on:
            out.write(line)
        new_classes = set()
        old_classes = set()

        while True:
            for line in tax:
                if not line:
                    continue
                s = line.split(" ")
                if s[0] in classes or s[2] in classes:
                    out.write(f"{s[0]} {s[1]} {s[2]} .\n")
                    if s[0] not in classes and s[0] not in old_classes:
                        new_classes.add(s[0])
                    if s[2] not in classes and s[2] not in old_classes:
                        new_classes.add(s[2])
            
            old_classes.update(classes)
            classes = new_classes.copy()
            new_classes = set()
            if not classes:
                break
        return old_classes

def pyclause_rules_to_csv(txtf, csvf):
    def format_triple(triple, var_dict):
        temp = triple.strip().split("(")
        p = temp[0]
        s = temp[1].split(",")[0]
        o = temp[1].split(",")[1].split(")")[0]

        if s in var_dict and o in var_dict:
            return f"{var_dict[s]} {p} {var_dict[o]}"
        if s in var_dict:
            return f"{var_dict[s]} {p} {o}"
        if o in var_dict:
            return f"{s} {p} {var_dict[o]}"
        return f"{s} {p} {o}"
    
    var_dict = {"X":"?a", "Y":"?b", "A":"?c", "B":"?d", "C":"?e", "D":"?f"}
    with open(txtf, 'r', encoding='utf-8') as txt, open(csvf, 'w',newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['Body', 'Head'], quoting=csv.QUOTE_NONE, escapechar="\\")
        writer.writeheader()

        for line in txt:
            if not line:
                continue
            split = line.split("<=")
            body = split[1].strip().split(", ")
            if body == [""]:
                continue
            sp = split[0].split("\t")
            head = sp[len(sp)-1].strip()
            rule = {}
            rule["Head"] = format_triple(head, var_dict)
            rule["Body"] = "   ".join(format_triple(t, var_dict) for t in body)
            print(rule)
            writer.writerow(rule)

def yago_tsv_to_nt(inf, outf):
    prefix = "http://yago-knowledge.org/resource/"
    with open(inf, 'r', encoding='utf-8') as inf, open(outf, 'w', encoding='utf-8') as outf:
        first = True
        ct = 0
        for line in inf:
            ct += 1
            if line.__contains__("\\u003"):
                continue
            if ct % 10000 == 0:
                print("10k")
            if first:
                first = False
                continue
            if line.startswith("#"):
                break
            l = line.split("\t")
            s = "<" + prefix + l[1].removeprefix("<").removesuffix(">") + ">" if not l[1].__contains__(":") else l[1].removeprefix("<").removesuffix(">")
            p = "<" + prefix + l[2].removeprefix("<").removesuffix(">") + ">" if not l[2].__contains__(":") else l[2].removeprefix("<").removesuffix(">")
            o = "<" + prefix + l[3].removeprefix("<").removesuffix(">") + ">" if not l[3].__contains__(":") else l[3].removeprefix("<").removesuffix(">")
            if p.__contains__("rdf:type"):
                outf.write(f"{s} http://www.w3.org/1999/02/22-rdf-syntax-ns#type {o} .\n")
            else:
                outf.write(f"{s} {p} {o} .\n")

def addPrefix(file, out, prefix):
    with open(file, "r", encoding="utf-8") as f, open(out, "w", encoding="utf-8") as out:
        for line in f:
            s = line.split("\t")
            out.write(f"<{prefix}{s[0]}> <{prefix}{s[1]}> <{prefix}{s[2].removesuffix("\n")}> .\n")

def remove_rules_with_constants(file, out):
    with open(file, "r", encoding="utf-8") as f, open(out, "w", encoding="utf-8") as out:
        for line in f:
            s = line.split(",")
            if not s[1].__contains__("?a") or not s[1].__contains__("?b"):
                continue
            out.write(line)


if __name__== '__main__':
    #pyclause_rules_to_csv("./Data/Rules/FrenchRoyalty-AnyBURL.txt","./Data/Rules/FrenchRoyalty-AnyBURL.csv")
    #yago_tsv_to_nt("./Data/KG/YAGO3-10/files/yagoTypes.tsv","./Data/KG/YAGO3-10/files/yagoTypes.nt")
    #classes = add_classes_to_ontology("./Data/KG/YAGO3-10/files/yagoTaxonomy.nt", "./Data/Ontology/YAGO3-10Ontology-properties.ttl","./Data/Ontology/YAGO3-10Ontology.ttl")
    #add_types_to_nt("./Data/KG/YAGO3-10/files/YAGO3-10-no-types.nt","./Data/KG/YAGO3-10/files/yagoTypes.nt","./Data/KG/YAGO3-10/YAGO3-10.nt", classes)
    remove_rules_with_constants(".\Data\Experimental_results\FrenchRoyalty-AnyBURL_PCA-adapted.csv", ".\Data\Experimental_results\FrenchRoyalty_PCA-no-constants.csv")