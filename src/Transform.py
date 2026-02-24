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
    
    print(os.getcwd())
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

if __name__== '__main__':
    d = {}
    transform_dbp_ontology("./Data/Ontology/dbpedia_2016-10.ttl", "./Data/Ontology/temp.ttl","./Data/Ontology/DB100K.ttl", d)
    print(d)



# class_dict = {'dbo:Ambassador': 'wikidata:Q121998', 'dbo:AmericanFootballPlayer': 'wikidata:Q14128148', 'dbo:Anime': 'wikidata:Q1107', 'dbo:Archeologist': 'wikidata:Q3621491', 'dbo:Archipelago': 'wikidata:Q33837', 'dbo:Archive': 'wikidata:Q166118', 'dbo:Asteroid': 'wikidata:Q3863', 'dbo:AustralianRulesFootballPlayer': 'wikidata:Q13414980', 'dbo:BaseballLeague': 'wikidata:Q6631808', 'dbo:BasketballPlayer': 'wikidata:Q3665646', 'dbo:Beer': 'wikidata:Q44', 'dbo:Bodybuilder': 'wikidata:Q15982795', 'dbo:Bone': 'wikidata:Q265868', 'dbo:BrownDwarf': 'wikidata:Q101600', 'dbo:Casino': 'wikidata:Q133215', 'dbo:Castle': 'wikidata:Q23413', 'dbo:Cat': 'wikidata:Q146', 'dbo:Celebrity': 'wikidata:Q211236', 'dbo:Chancellor': 'wikidata:Q373085', 'dbo:CyclingRace': 'wikidata:Q15091377', 'dbo:Dam': 'wikidata:Q12323', 'dbo:Dog': 'wikidata:Q25324', 'dbo:Economist': 'wikidata:Q188094', 'dbo:Egyptologist': 'wikidata:Q1350189', 'dbo:Employer': 'wikidata:Q3053337', 'dbo:Engineer': 'wikidata:Q81096', 'dbo:Entomologist': 'wikidata:Q3055126', 'dbo:Enzyme': 'wikidata:Q8047', 'dbo:Factory': 'wikidata:Q83405', 'dbo:Farmer': 'wikidata:Q131512', 'dbo:FashionDesigner': 'wikidata:Q3501317', 'dbo:Fencer': 'wikidata:Q737498Q13381863', 'dbo:Fish': 'wikidata:Q152', 'dbo:Garden': 'wikidata:Q1107656', 'dbo:Gate': 'wikidata:Q53060', 'dbo:GeologicalPeriod': 'wikidata:Q392928', 'dbo:Glacier': 'wikidata:Q35666', 'dbo:GolfTournament': 'wikidata:Q15061650', 'dbo:Governor': 'wikidata:Q132050', 'dbo:Guitar': 'wikidata:Q6607', 'dbo:Guitarist': 'wikidata:Q855091', 'dbo:HandballPlayer': 'wikidata:Q13365117', 'dbo:HandballTeam': 'wikidata:Q10517054', 'dbo:HistoricalPeriod': 'wikidata:Q11514315', 'dbo:HistoricalRegion': 'wikidata:Q1620908', 'dbo:Holiday': 'wikidata:Q1445650', 'dbo:Hormone': 'wikidata:Q8047', 'dbo:HotSpring': 'wikidata:Q177380', 'dbo:InformationAppliance': 'wikidata:Q1067263', 'dbo:Insect': 'wikidata:Q1390', 'dbo:Journalist': 'wikidata:Q1930187', 'dbo:Lawyer': 'wikidata:Q40348', 'dbo:Ligament': 'wikidata:Q39888', 'dbo:LightNovel': 'wikidata:Q747381', 'dbo:Lighthouse': 'wikidata:Q39715', 'dbo:Linguist': 'wikidata:Q14467526', 'dbo:Locality': 'wikidata:Q3257686', 'dbo:Manga': 'wikidata:Q8274', 'dbo:Manhua': 'wikidata:Q754669', 'dbo:Manhwa': 'wikidata:Q562214', 'dbo:Marriage': 'wikidata:Q8445', 'dbo:Media': 'wikidata:Q340169', 'dbo:Medicine': 'wikidata:Q11190', 'dbo:Meeting': 'wikidata:Q2761147', 'dbo:MetroStation': 'wikidata:Q928830', 'dbo:Mineral': 'wikidata:Q7946', 'dbo:MobilePhone': 'wikidata:Q17517', 'dbo:Model': 'wikidata:Q4610556', 'dbo:Mollusca': 'wikidata:Q25326', 'dbo:Mosque': 'wikidata:Q32815', 'dbo:Motorcycle': 'wikidata:Q34493', 'dbo:MountainPass': 'wikidata:Q133056', 'dbo:MovieDirector': 'wikidata:Q2526255', 'dbo:MusicDirector': 'wikidata:Q1198887', 'dbo:NationalAnthem': 'wikidata:Q23691', 'dbo:NaturalRegion': 'wikidata:Q1970725', 'dbo:NobelPrize': 'wikidata:Q7191', 'dbo:Ocean': 'wikidata:Q9430', 'dbo:OverseasDepartment': 'wikidata:Q202216', 'dbo:Painter': 'wikidata:Q1028181', 'dbo:Parliament': 'wikidata:Q35749', 'dbo:Philosopher': 'wikidata:Q4964182', 'dbo:Photographer': 'wikidata:Q33231', 'dbo:PlayWright': 'wikidata:Q214917', 'dbo:Poem': 'wikidata:Q5185279', 'dbo:Poet': 'wikidata:Q49757', 'dbo:Polyhedron': 'wikidata:Q172937', 'dbo:Port': 'wikidata:Q44782', 'dbo:Prefecture': 'wikidata:Q515716', 'dbo:President': 'wikidata:Q30461', 'dbo:Prison': 'wikidata:Q40357', 'dbo:Producer': 'wikidata:Q3282637', 'dbo:Profession': 'wikidata:Q28640', 'dbo:ProgrammingLanguage': 'wikidata:Q9143', 'dbo:Psychologist': 'wikidata:Q212980', 'dbo:PublicService': 'wikidata:Q161837', 'dbo:Pyramid': 'wikidata:Q12516', 'dbo:Racecourse': 'wikidata:Q1777138', 'dbo:RadioHost': 'wikidata:Q2722764', 'dbo:RadioProgram': 'wikidata:Q1555508', 'dbo:RailwayLine': 'wikidata:Q728937', 'dbo:RailwayStation': 'wikidata:Q55488', 'dbo:RallyDriver': 'wikidata:Q10842936', 'dbo:Religious': 'wikidata:Q2566598', 'dbo:RoadTunnel': 'wikidata:Q2354973', 'dbo:RomanEmperor': 'wikidata:Q842606', 'dbo:Rower': 'wikidata:Q13382576', 'dbo:RugbyLeague': 'wikidata:Q10962', 'dbo:RugbyPlayer': 'wikidata:Q13415036', 'dbo:ScreenWriter': 'wikidata:Q28389', 'dbo:SerialKiller': 'wikidata:Q484188', 'dbo:Singer': 'wikidata:Q177220', 'dbo:Skater': 'wikidata:Q847400', 'dbo:Skier': 'wikidata:Q4270517', 'dbo:SoccerManager': 'wikidata:Q628099', 'dbo:SolarEclipse': 'wikidata:Q3887', 'dbo:SongWriter': 'wikidata:Q753110', 'dbo:Square': 'wikidata:Q174782', 'dbo:SquashPlayer': 'wikidata:Q16278103', 'dbo:Street': 'wikidata:Q79007', 'dbo:Surfer': 'wikidata:Q13561328', 'dbo:Synagogue': 'wikidata:Q34627', 'dbo:TableTennisPlayer': 'wikidata:Q13382519', 'dbo:Tax': 'wikidata:Q8161', 'dbo:TelevisionHost': 'wikidata:Q947873', 'dbo:TennisTournament': 'wikidata:Q13219666', 'dbo:TheatreDirector': 'wikidata:Q3387717', 'dbo:Town': 'wikidata:Q3957', 'dbo:TradeUnion': 'wikidata:Q178790', 'dbo:Treadmill': 'wikidata:Q683267', 'dbo:Tunnel': 'wikidata:Q44377', 'dbo:Valley': 'wikidata:Q39816', 'dbo:VicePresident': 'wikidata:Q42178', 'dbo:Village': 'wikidata:Q532', 'dbo:WaterRide': 'wikidata:Q2870166', 'dbo:WaterTower': 'wikidata:Q274153', 'dbo:Watermill': 'wikidata:Q185187', 'dbo:WindMotor': 'wikidata:Q15854792', 'dbo:Windmill': 'wikidata:Q38720', 'dbo:Winery': 'wikidata:Q156362', 'dbo:Year': 'wikidata:Q577', 'dbo:Zoo': 'wikidata:Q43501', 'dbo:AdultActor': 'wikidata:Q488111', 'dbo:Altitude': 'wikidata:Q190200', 'dbo:Cave': 'wikidata:Q35509', 'dbo:Church': 'wikidata:Q16970', 'dbo:Contest': 'wikidata:Q476300', 'dbo:CultivatedVariety': 'wikidata:Q4886', 'dbo:Deity': 'wikidata:Q178885', 'dbo:Drama': 'wikidata:Q25372', 'dbo:Election': 'wikidata:Q40231', 'dbo:GivenName': 'wikidata:Q202444', 'dbo:GolfCourse': 'wikidata:Q1048525', 'dbo:GovernmentAgency': 'wikidata:Q327333', 'dbo:Ideology': 'wikidata:Q7257', 'dbo:Intercommunality': 'wikidata:Q3153117', 'dbo:Judge': 'wikidata:Q16533', 'dbo:Letter': 'wikidata:Q9788', 'dbo:LunarCrater': 'wikidata:Q1348589', 'dbo:MemberOfParliament': 'wikidata:Q486839', 'dbo:Monastery': 'wikidata:Q44613', 'dbo:Murderer': 'wikidata:Q16266334', 'dbo:Muscle': 'wikidata:Q7365', 'dbo:Musical': 'wikidata:Q2743', 'dbo:MythologicalFigure': 'wikidata:Q15410431', 'dbo:Non-ProfitOrganisation': 'wikidata:Q163740', 'dbo:NuclearPowerStation': 'wikidata:Q134447', 'dbo:Opera': 'wikidata:Q1344', 'dbo:Organ': 'wikidata:Q1444', 'dbo:Pope': 'wikidata:Q19546', 'dbo:Priest': 'wikidata:Q42603', 'dbo:RailwayTunnel': 'wikidata:Q1311958', 'dbo:Statistic': 'wikidata:Q1949963', 'dbo:Swimmer': 'wikidata:Q10843402', 'dbo:Theatre': 'wikidata:Q24354', 'dbo:Vein': 'wikidata:Q9609', 'dbo:Volcano': 'wikidata:Q8072', 'dbo:Wine': 'wikidata:Q282', 'dbo:WorldHeritageSite': 'wikidata:Q9259', 'dbo:Artery': 'wikidata:Q9655', 'dbo:Boxing': 'wikidata:Q32112', 'dbo:BroadcastNetwork': 'wikidata:Q141683', 'dbo:Flag': 'wikidata:Q14660', 'dbo:Game': 'wikidata:Q11410', 'dbo:LawFirm': 'wikidata:Q613142', 'dbo:Mayor': 'wikidata:Q30185', 'dbo:Nerve': 'wikidata:Q9620', 'dbo:Novel': 'wikidata:Q8261', 'dbo:Presenter': 'wikidata:Q13590141', 'dbo:ProtectedArea': 'wikidata:Q473972', 'dbo:Shrine': 'wikidata:Q697295', 'dbo:SkiResort': 'wikidata:Q130003', 'dbo:Tower': 'wikidata:Q12518', 'dbo:Train': 'wikidata:Q870', 'dbo:VideoGame': 'wikidata:Q7889', 'dbo:Astronaut': 'wikidata:Q11631', 'dbo:Cartoon': 'wikidata:Q627603', 'dbo:Cemetery': 'wikidata:Q39614', 'dbo:ChemicalCompound': 'wikidata:Q11173', 'dbo:Criminal': 'wikidata:Q2159907', 'dbo:Eukaryote': 'wikidata:Q19088', 'dbo:Grape': 'wikidata:Q10978', 'dbo:Magazine': 'wikidata:Q41298', 'dbo:Mammal': 'wikidata:Q7377', 'dbo:NobleFamily': 'wikidata:Q13417114', 'dbo:Population': 'wikidata:Q33829', 'dbo:RaceTrack': 'wikidata:Q1777138', 'dbo:SiteOfSpecialScientificInterest': 'wikidata:Q422211', 'dbo:Taxon': 'wikidata:Q16521', 'dbo:VolleyballPlayer': 'wikidata:Q15117302', 'dbo:Wrestler': 'wikidata:Q13474373', 'dbo:Constellation': 'wikidata:Q8928', 'dbo:EthnicGroup': 'wikidata:Q41710', 'dbo:FormerMunicipality': 'wikidata:Q19730508', 'dbo:HockeyTeam': 'wikidata:Q4498974', 'dbo:Monument': 'wikidata:Q4989906', 'dbo:Museum': 'wikidata:Q33506', 'dbo:Name': 'wikidata:Q82799', 'dbo:Newspaper': 'wikidata:Q11032', 'dbo:RacingDriver': 'wikidata:Q378622', 'dbo:RecordLabel': 'wikidata:Q18127', 'dbo:Region': 'wikidata:Q3455524', 'dbo:SpaceStation': 'wikidata:Q25956', 'dbo:TermOfOffice': 'wikidata:Q524572', 'dbo:AcademicJournal': 'wikidata:Q737498', 'dbo:BaseballPlayer': 'wikidata:Q10871364', 'dbo:Comic': 'wikidata:Q245068', 'dbo:Drug': 'wikidata:Q8386', 'dbo:FigureSkater': 'wikidata:Q13219587', 'dbo:Gene': 'wikidata:Q7187', 'dbo:Monarch': 'wikidata:Q116', 'dbo:GridironFootballPlayer': 'wikidata:Q14128148', 'dbo:Protein': 'wikidata:Q8054', 'dbo:Sales': 'wikidata:Q194189', 'dbo:Single': 'wikidata:Q134556', 'dbo:Airline': 'wikidata:Q46970', 'dbo:Bridge': 'wikidata:Q12280', 'dbo:Family': 'wikidata:Q8436', 'dbo:ResearchProject': 'wikidata:Q1298668', 'dbo:Skyscraper': 'wikidata:Q11303', 'dbo:Writer': 'wikidata:Q36180', 'dbo:Activity': 'wikidata:Q1914636', 'dbo:LegalCase': 'wikidata:Q2334719', 'dbo:MountainRange': 'wikidata:Q46831', 'dbo:MusicGenre': 'wikidata:Q188451', 'dbo:PowerStation': 'wikidata:Q159719', 'dbo:Scientist': 'wikidata:Q901', 'dbo:Tournament': 'wikidata:Q500834', 'dbo:Road': 'wikidata:Q34442', 'dbo:LaunchPad': 'wikidata:Q1353183', 'dbo:Play': 'wikidata:Q25379', 'dbo:Sport': 'wikidata:Q349', 'dbo:Disease': 'wikidata:Q12136', 'dbo:Legislature': 'wikidata:Q11204', 'dbo:Saint': 'wikidata:Q43115', 'dbo:SoccerPlayer': 'wikidata:Q937857', 'dbo:Stream': 'wikidata:Q47521', 'dbo:Actor': 'wikidata:Q33999', 'dbo:ReligiousBuilding': 'wikidata:Q1370598', 'dbo:IceHockeyPlayer': 'wikidata:Q11774891', 'dbo:Mill': 'wikidata:Q44494', 'dbo:PeriodicalLiterature': 'wikidata:Q1092563', 'dbo:Politician': 'wikidata:Q82955', 'dbo:SoccerClub': 'wikidata:Q476028', 'dbo:Plant': 'wikidata:Q756', 'dbo:Software': 'wikidata:Q7397', 'dbo:MusicalWork': 'wikidata:Q2188189', 'dbo:SpaceShuttle': 'wikidata:Q48806', 'dbo:TelevisionShow': 'wikidata:Q15416', 'dbo:Biomolecule': 'wikidata:Q206229', 'dbo:Galaxy': 'wikidata:Q318', 'dbo:PoliticalParty': 'wikidata:Q7278', 'dbo:Rocket': 'wikidata:Q41291', 'dbo:GolfPlayer': 'wikidata:Q13156709', 'dbo:Station': 'wikidata:Q719456', 'dbo:Animal': 'wikidata:Q729', 'dbo:Food': 'wikidata:Q2095', 'dbo:FictionalCharacter': 'wikidata:Q95074', 'dbo:Spacecraft': 'wikidata:Q40218', 'dbo:Planet': 'wikidata:Q634', 'dbo:Award': 'wikidata:Q618779', 'dbo:Building': 'wikidata:Q41176', 'dbo:Agent': 'wikidata:Q24229398', 'dbo:Broadcaster': 'wikidata:Q15265344', 'dbo:MilitaryUnit': 'wikidata:Q176799', 'dbo:TennisPlayer': 'wikidata:Q10833314', 'dbo:Artist': 'wikidata:Q483501', 'dbo:SportsLeague': 'wikidata:Q623109', 'dbo:AnatomicalStructure': 'wikidata:Q4936952', 'dbo:Island': 'wikidata:Q23442', 'dbo:SpaceMission': 'wikidata:Q2133344', 'dbo:Settlement': 'wikidata:Q486972'}