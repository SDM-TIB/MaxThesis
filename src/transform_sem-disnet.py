from rdflib import Graph, Namespace
from Util.NormalizationUtil import *
from Util.Classes import *
from Util.Util import parseGraph, parseOntology

def extract_subgraph():

    prefix = "https://w3id.org/sem-disnet/"
    abbr = "disnet"
    prefix_dict = {str(prefix): abbr,
                            "http://www.w3.org/2004/02/skos/core":"skos",
                            "https://w3id.org/sem-disnet/ontology#":"disnet-o",
                            "http://www.w3.org/ns/prov#": "prov",
                            "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
                            "http://www.w3.org/ns/rdf-star#": "rdf-star",
                            "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
                            "http://www.w3.org/2002/07/owl#": "owl",
                            "http://www.w3.org/2001/XMLSchema#": "xsd",
                            "http://purl.org/dc/terms/": "dcterms",
                            "http://purl.org/vocab/vann/":"vann",
                            "https://go.drugbank.com/drugs/": "drugbank",
                            "https://omim.org/entry/":"mim",
                            "http://identifiers.org/ensembl:":"ensembl",
                            "http://www.ebi.ac.uk/efo/":"efo",
                            "http://id.nlm.nih.gov/mesh/":"mesh",
                            "http://purl.obolibrary.org/obo/":"obo",
                            "https://www.uniprot.org/uniprotkb/":"uniprot",
                            "https://www.ebi.ac.uk/ols4/ontologies/ordo/":"ORDO",
                            "http://example.org/resource":"resource",
                            "http://bio2rdf.org/ctd_vocabulary:":"ctd_vocabulary",
                            "http://purl.bioontology.org/ontology/ICD10CM/":"ICD10CM",
                            "http://purl.bioontology.org/ontology/ICD10/":"ICD10",
                            "http://purl.bioontology.org/ontology/ICD9CM/":"ICD9CM",
                            "http://purl.bioontology.org/ontology/RXNORM/":"RXNORM",
                            "http:example.org/ncbigene":"ncbigene"
                            }

    ontology = Ontology()
    parseOntology("./Data/Ontology/sem-disnet-max.ttl", ontology, "https://w3id.org/sem-disnet/ontology#", "disnet-o",prefix_dict)
    
    datatype_ps = {}
    for c in ontology.properties:
        for r in ontology.properties[c][1]:
            if r.startswith("xsd:"):
                datatype_ps[c]=r
    full_graph = Graph()
    subgraph = Graph()
    print(datatype_ps)
    #full_graph.parse("./Data/KG/sem-disnet/experiment2_sem-disnet-enriched.tsv")

def tsv_to_ttl(tsv, ttl, abbr):
    prefix = "https://w3id.org/sem-disnet/"
    prefix_dict = {str(prefix): abbr,
                        "http://www.w3.org/2004/02/skos/core":"skos",
                        "https://w3id.org/sem-disnet/ontology#":"disnet-o",
                        "http://www.w3.org/ns/prov#": "prov",
                        "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
                        "http://www.w3.org/ns/rdf-star#": "rdf-star",
                        "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
                        "http://www.w3.org/2002/07/owl#": "owl",
                        "http://www.w3.org/2001/XMLSchema#": "xsd",
                        "http://purl.org/dc/terms/": "dcterms",
                        "http://purl.org/vocab/vann/":"vann",
                        "https://go.drugbank.com/drugs/": "drugbank",
                        "https://omim.org/entry/":"mim",
                        "http://identifiers.org/ensembl:":"ensembl",
                        "http://www.ebi.ac.uk/efo/":"efo",
                        "http://id.nlm.nih.gov/mesh/":"mesh",
                        "http://purl.obolibrary.org/obo/":"obo",
                        "https://www.uniprot.org/uniprotkb/":"uniprot",
                        "https://www.ebi.ac.uk/ols4/ontologies/ordo/":"ORDO",
                        "http://example.org/resource":"resource",
                        "http://bio2rdf.org/ctd_vocabulary:":"ctd_vocabulary",
                        "http://purl.bioontology.org/ontology/ICD10CM/":"ICD10CM",
                        "http://purl.bioontology.org/ontology/ICD10/":"ICD10",
                        "http://purl.bioontology.org/ontology/ICD9CM/":"ICD9CM",
                        "http://purl.bioontology.org/ontology/RXNORM/":"RXNORM",
                        "http:example.org/ncbigene":"ncbigene"
                        }



    datatype_ps = {'dda_inferredScore': 'xsd:decimal', 'disClass_vocabulary': 'xsd:string', 'disease_ddfType': 'xsd:string', 'dpa_score': 'xsd:decimal', 'dpha_mayoScore': 'xsd:decimal', 'dpha_wikiScore': 'xsd:decimal', 'dra_causality': 'xsd:string', 'dra_evidenceType': 'xsd:string', 'drug_atcCode': 'xsd:string', 'drug_inchiKey': 'xsd:string', 'drug_molecularType': 'xsd:string', 'dta_actionType': 'xsd:string', 'dva_score': 'xsd:decimal', 'gda_score': 'xsd:decimal', 'gene_chromosomeVersion': 'xsd:string', 'gene_dpi': 'xsd:decimal', 'gene_dsi': 'xsd:decimal', 'gene_seqEnd': 'xsd:integer', 'gene_seqStart': 'xsd:integer', 'gene_strand': 'xsd:integer', 'gene_symbol': 'xsd:string', 'mapping_vocabulary': 'xsd:string', 'marker_concentration': 'xsd:string', 'marker_name': 'xsd:string', 'marker_sample': 'xsd:string', 'ppi_quality': 'xsd:string', 'prev_geo': 'xsd:string', 'rna_category': 'xsd:string', 'semType_abbreviation': 'xsd:string', 'target_type': 'xsd:string', 'variant_chromosome': 'xsd:string', 'variant_consequence': 'xsd:string', 'variant_dpi': 'xsd:decimal', 'variant_dsi': 'xsd:decimal', 'variant_position': 'xsd:integer', 'altLabel': 'xsd:string', 'terms:identifier': 'xsd:anyType', "dcterms:identifier": "xsd:anyType"}
    datatype_ps["rdfs:label"] = "xsd:string"
    datatype_ps["skos:altLabel"] = datatype_ps["altLabel"]
    with open( tsv, 'r', encoding='utf-8') as t:
        # TODO recognize correct prefix; NOTE: terms: = dcterms:
        out = ""
        pfs = set()
        with open(ttl, 'w', encoding='utf-8') as tl:
            for row in t:
                dt = False
                s,p,o = row.split("\t")

                if not s.__contains__(":"):
                    s=f"disnet:{s}"
                elif s.startswith("identifiers.org:"):
                    s = s.removeprefix("identifiers.org:")
                elif s.startswith("bio2rdf.org:ctd_vocabulary:"):
                    s = s.removeprefix("bio2rdf.org:")
                

                if p=="type":
                    p="rdf:type"
                elif p=="label":
                    p="rdfs:label"
                    dt = True
                elif p == "altLabel":
                    p = "skos:altLabel"
                    dt = True
                elif p == "exactMatch":
                    p = "skos:exactMatch"
                elif p == "relativeMatch":
                    p = "skos:relativeMatch"
                elif p == "closeMatch":
                    p="skos:closeMatch"
                elif p == "terms:identifier":
                    p = "dcterms:identifier"
                    dt = True
                elif p.startswith("identifiers.org:"):
                    p = p.removeprefix("identifiers.org:")
                elif p in datatype_ps:
                    dt = True
                elif p.startswith("bio2rdf.org:ctd_vocabulary:"):
                    p = p.removeprefix("bio2rdf.org:")
                elif not p.__contains__(":"):
                    p = f"disnet:{p}"


                if dt:
                    o = f"\"{o.strip()}\"^^{datatype_ps[p]}"
                else:
                    if not o.__contains__(":"):
                        o = f"disnet:{o}"
                    elif o.startswith("identifiers.org:"):
                        o = o.removeprefix("identifiers.org:")
                    elif o.startswith("bio2rdf.org:ctd_vocabulary:"):
                        o = o.removeprefix("bio2rdf.org:")
                out += f"{s} {p} {o.strip()} .\n"



                # check for unknown prefixes
                if s.__contains__(":"):
                    pre = s.split(":")
                    pre = pre[:len(pre)-1]
                    if ":".join(pre) not in prefix_dict.values():
                        pfs.add(":".join(pre))

                if p.__contains__(":"):
                    pre = p.split(":")
                    pre = pre[:len(pre)-1]
                    if ":".join(pre) not in prefix_dict.values():
                        pfs.add(":".join(pre))

                if o.__contains__(":") and not o.__contains__("\""):
                    pre = o.split(":")
                    pre = pre[:len(pre)-1]
                    if ":".join(pre) not in prefix_dict.values():
                        pfs.add(":".join(pre))



                if len(out) > 1000000:
                    tl.write(out)
                    out = ""
            tl.write(out)
            print(pfs)
if __name__=="__main__":
    tsv_to_ttl("./Data/KG/sem-disnet/experiment2_sem-disnet-enriched.tsv","./Data/KG/sem-disnet/experiment2_sem-disnet-enriched.ttl", "disnet")
    #extract_subgraph()