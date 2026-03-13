"""
=============================================================
  ANONIMIZADOR DE EVOLUCIONES CLÍNICAS EN ESPAÑOL  v4.0
  Basado en Microsoft Presidio + spaCy
  Con lista blanca médica: NO anonimiza fármacos,
  enfermedades, microorganismos ni términos clínicos.
  Comparación case-insensitive (mayúsculas/minúsculas ignoradas).
  Sistema de autoaprendizaje: recuerda términos entre sesiones.
  100% local — ningún dato sale de tu computadora.
=============================================================

INSTALACIÓN (una sola vez, desde la terminal):
  pip install presidio-analyzer presidio-anonymizer
  python -m spacy download es_core_news_md

USO:
  1. Modo demo:        python anonimizar_clinico.py
  2. Un archivo .txt:  python anonimizar_clinico.py mi_evolucion.txt
  3. Una carpeta:      python anonimizar_clinico.py carpeta/

PERSONALIZACIÓN:
  - Agregá términos en LISTA_BLANCA_MEDICA más abajo.
  - El archivo 'terminos_aprendidos.txt' se actualiza automáticamente.
  - El archivo 'terminos_aprendidos.txt' se actualiza automáticamente.
=============================================================
"""

import sys
import os
import re
from pathlib import Path
import json
from pathlib import Path

# ── Dependencias principales ─────────────────────────────
try:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
except ImportError:
    print("\n❌ Faltan librerías. Ejecutá en la terminal:\n")
    print("   pip install presidio-analyzer presidio-anonymizer")
    print("   python -m spacy download es_core_news_md\n")
    sys.exit(1)


# ══════════════════════════════════════════════════════════
#  LISTA BLANCA MÉDICA
#  Todos los términos aquí NUNCA serán anonimizados,
#  aunque spaCy los detecte como nombres o lugares.
#
#  CASE-INSENSITIVE: da igual si escribís Staphylococcus,
#  staphylococcus o STAPHYLOCOCCUS — todos son equivalentes.
#
#  → Podés agregar tus propios términos al final de
#    cada sección con cualquier capitalización.
# ══════════════════════════════════════════════════════════

LISTA_BLANCA_MEDICA = set(w.lower() for w in [

    # ── FÁRMACOS Y PRINCIPIOS ACTIVOS ─────────────────────
    # Analgésicos / antiinflamatorios
    "ibuprofeno", "paracetamol", "diclofenac", "ketorolac", "metamizol",
    "dipirona", "naproxeno", "celecoxib", "indometacina", "piroxicam",
    "meloxicam", "nimesulida", "aspirina", "acido acetilsalicilico",
    "tramadol", "morfina", "codeina", "fentanilo", "buprenorfina",
    "oxicodona", "metadona", "tapentadol",

    # Antibióticos
    "amoxicilina", "ampicilina", "ciprofloxacina", "levofloxacina",
    "azitromicina", "claritromicina", "eritromicina", "doxiciclina",
    "metronidazol", "clindamicina", "vancomicina", "linezolid",
    "meropenem", "imipenem", "piperacilina", "tazobactam",
    "ceftriaxona", "cefalexina", "cefazolina", "cefuroxima",
    "trimetoprima", "sulfametoxazol", "cotrimoxazol", "nitrofurantoina",
    "rifampicina", "isoniazida", "etambutol", "pirazinamida",

    # Cardiovasculares
    "enalapril", "lisinopril", "ramipril", "perindopril", "captopril",
    "losartan", "valsartan", "irbesartan", "candesartan", "telmisartan",
    "amlodipina", "nifedipina", "diltiazem", "verapamilo",
    "atenolol", "metoprolol", "carvedilol", "bisoprolol", "propranolol",
    "furosemida", "hidroclorotiazida", "espironolactona", "torasemida",
    "digoxina", "amiodarona", "flecainida", "sotalol",
    "atorvastatina", "rosuvastatina", "simvastatina", "pravastatina",
    "nitroglicerina", "isosorbide", "clopidogrel", "warfarina",
    "heparina", "enoxaparina", "rivaroxaban", "apixaban", "dabigatran",
    "aas",

    # Antidiabéticos
    "metformina", "glibenclamida", "glimepirida", "sitagliptina",
    "vildagliptina", "empagliflozina", "dapagliflozina", "canagliflozina",
    "insulina", "glargina", "detemir", "lispro", "aspart", "glulisina",
    "semaglutida", "liraglutida", "dulaglutida", "exenatida",

    # Neurológicos / psiquiátricos
    "sertralina", "fluoxetina", "paroxetina", "escitalopram", "citalopram",
    "venlafaxina", "duloxetina", "mirtazapina", "bupropion",
    "amitriptilina", "imipramina", "clomipramina",
    "haloperidol", "risperidona", "olanzapina", "quetiapina", "clozapina",
    "aripiprazol", "ziprasidona", "amisulprida",
    "diazepam", "lorazepam", "alprazolam", "clonazepam", "bromazepam",
    "zolpidem", "midazolam", "fenobarbital",
    "fenitoina", "carbamazepina", "valproato", "lamotrigina",
    "levetiracetam", "topiramato", "gabapentina", "pregabalina",
    "donepezilo", "memantina", "rivastigmina",
    "metilfenidato", "atomoxetina",

    # Respiratorios
    "salbutamol", "terbutalina", "salmeterol", "formoterol", "indacaterol",
    "ipratropio", "tiotropio", "budesonida", "fluticasona", "beclometasona",
    "montelukast", "teofilina", "acetilcisteina", "ambroxol",

    # Gastrointestinales
    "omeprazol", "pantoprazol", "lansoprazol", "esomeprazol", "rabeprazol",
    "ranitidina", "famotidina", "metoclopramida", "domperidona",
    "ondansetron", "loperamida", "mesalazina", "sulfasalazina",
    "lactulosa", "polietilenglicol", "bisacodilo",

    # Inmunosupresores / oncológicos
    "prednisona", "prednisolona", "dexametasona", "hidrocortisona",
    "metilprednisolona", "betametasona", "triamcinolona",
    "metotrexato", "azatioprina", "ciclosporina", "tacrolimus",
    "micofenolato", "rituximab", "infliximab", "adalimumab",

    # Hormonas / tiroides
    "levotiroxina", "metimazol", "propiltiouracilo",
    "estradiol", "progesterona", "testosterona",

    # Vitaminas y suplementos
    "vitamina", "hierro", "calcio", "magnesio", "zinc", "folato",
    "acido folico", "vitamina d", "vitamina b12", "ferritina",

    # Otros frecuentes
    "atropina", "adrenalina", "epinefrina", "noradrenalina",
    "dopamina", "dobutamina", "vasopresina",
    "albumina", "plasma", "dextrosa", "glucosa", "potasio", "sodio",

    # ── ENFERMEDADES Y DIAGNÓSTICOS ───────────────────────
    "hipertension", "hipertension arterial", "hta",
    "diabetes", "dislipemia", "hiperlipidemia", "obesidad",
    "hipotiroidismo", "hipertiroidismo", "tiroiditis",
    "asma", "epoc", "bronquitis", "neumonia", "tuberculosis",
    "insuficiencia cardiaca", "cardiopatia", "coronariopatia",
    "infarto", "iam", "angina", "arritmia", "fibrilacion", "taquicardia",
    "bradicardia", "bloqueo", "flutter",
    "acv", "avc", "ictus", "tia", "accidente cerebrovascular",
    "epilepsia", "convulsiones", "migrana", "cefalea",
    "depresion", "ansiedad", "trastorno bipolar", "esquizofrenia",
    "alzheimer", "parkinson", "demencia",
    "artritis", "artrosis", "osteoporosis", "fibromialgia", "lupus",
    "artritis reumatoidea", "espondilitis",
    "insuficiencia renal", "nefropatia", "litiasis renal",
    "hepatitis", "cirrosis", "higado graso", "esteatosis",
    "gastritis", "ulcera", "enfermedad de crohn", "colitis ulcerosa",
    "reflujo", "hernia hiatal", "pancreatitis",
    "anemia", "leucemia", "linfoma", "mieloma",
    "cancer", "carcinoma", "adenocarcinoma", "tumor", "neoplasia",
    "vih", "sida", "covid", "coronavirus",
    "sepsis", "shock", "bacteriemia",
    "celulitis", "erisipela", "absceso",
    "trombosis", "tep", "tvp",
    "hipoglucemia", "hiperglucemia", "cetoacidosis",

    # ── SÍNTOMAS Y SIGNOS ─────────────────────────────────
    "dolor", "fiebre", "tos", "disnea", "fatiga", "astenia",
    "nauseas", "vomitos", "diarrea", "constipacion", "estrenimiento",
    "edema", "ascitis", "ictericia", "cianosis", "palidez",
    "taquipnea", "bradipnea", "apnea", "ortopnea",
    "palpitaciones", "sincope", "presincope", "lipotimia",
    "mareos", "vertigo", "fotofobia",
    "hematuria", "disuria", "poliuria", "oliguria", "anuria",
    "hemoptisis", "epistaxis", "melena", "rectorragia", "hematemesis",
    "prurito", "urticaria", "rash", "eritema", "exantema",
    "precordial", "torácico", "toracico", "abdominal",

    # ── PROCEDIMIENTOS Y ESTUDIOS ─────────────────────────
    "ecg", "electrocardiograma", "ecocardiograma", "holter",
    "radiografia", "rx", "tomografia", "tac", "tc", "resonancia", "rmn",
    "ecografia", "eco", "endoscopia", "colonoscopia",
    "espirometria", "oximetria", "saturacion", "saturometria",
    "hemograma", "laboratorio", "coagulograma", "ionograma",
    "glucemia", "creatinina", "urea", "acido urico", "bilirrubina",
    "transaminasas", "got", "gpt", "ggt", "fosfatasa alcalina",
    "tsh", "t4", "t3", "psa",
    "cultivo", "antibiograma", "biopsia", "citologia",
    "puncion", "paracentesis", "toracocentesis",
    "cirugia", "operacion", "intervencion", "reseccion",
    "internacion", "hospitalizacion", "guardia", "emergencia",
    "interconsulta", "derivacion", "alta", "egreso",
    "hemodinamia", "cateterismo",

    # ── ESPECIALIDADES MÉDICAS ────────────────────────────
    "cardiologia", "neurologia", "neumologia", "gastroenterologia",
    "nefrologia", "urologia", "endocrinologia", "reumatologia",
    "hematologia", "oncologia", "infectologia", "traumatologia",
    "ortopedia", "dermatologia", "oftalmologia", "otorrinolaringologia",
    "ginecologia", "obstetricia", "pediatria", "neonatologia",
    "psiquiatria", "psicologia", "kinesiologia", "fonoaudiologia",
    "nutricion", "clinica medica", "medicina interna", "terapia intensiva",
    "uci", "uti", "unidad coronaria",

    # ── ABREVIATURAS MÉDICAS ──────────────────────────────
    "fc", "fr", "ta", "sao2", "fio2", "glasgow", "apache",
    "icc", "irc",
    "aines", "ace",
    "vo", "ev", "im", "sc", "sl", "iv",
    "bid", "tid", "qid", "hs",
    "mg", "mcg", "ml", "ui", "meq", "lpm",
    "comp", "amp", "sol", "susp", "caps",

    # ── MICROORGANISMOS ───────────────────────────────────
    # Bacterias Gram positivas
    "Staphylococcus", "Staphylococcus aureus", "Staphylococcus epidermidis",
    "Staphylococcus saprophyticus", "Staphylococcus haemolyticus",
    "SAMR", "SARM", "MRSA",
    "Streptococcus", "Streptococcus pyogenes", "Streptococcus agalactiae",
    "Streptococcus pneumoniae", "Streptococcus viridans", "Streptococcus bovis",
    "Streptococcus mutans",
    "Enterococcus", "Enterococcus faecalis", "Enterococcus faecium",
    "Listeria", "Listeria monocytogenes",
    "Clostridium", "Clostridium difficile", "Clostridium perfringens",
    "Clostridium tetani", "Clostridium botulinum",
    "Clostridioides difficile",
    "Bacillus", "Bacillus anthracis", "Bacillus cereus",
    "Corynebacterium", "Corynebacterium diphtheriae",
    "Nocardia", "Actinomyces",
    "C. difficile", "C diff",

    # Bacterias Gram negativas
    "Escherichia", "Escherichia coli", "E. coli", "ECEH",
    "Klebsiella", "Klebsiella pneumoniae", "Klebsiella oxytoca",
    "Pseudomonas", "Pseudomonas aeruginosa",
    "Acinetobacter", "Acinetobacter baumannii",
    "Enterobacter", "Enterobacter cloacae",
    "Proteus", "Proteus mirabilis",
    "Serratia", "Serratia marcescens",
    "Haemophilus", "Haemophilus influenzae",
    "Neisseria", "Neisseria meningitidis", "Neisseria gonorrhoeae",
    "Moraxella", "Moraxella catarrhalis",
    "Salmonella", "Salmonella typhi", "Salmonella enteritidis",
    "Shigella", "Shigella sonnei", "Shigella flexneri",
    "Campylobacter", "Campylobacter jejuni",
    "Helicobacter", "Helicobacter pylori", "H. pylori",
    "Vibrio", "Vibrio cholerae",
    "Yersinia", "Yersinia pestis", "Yersinia enterocolitica",
    "Legionella", "Legionella pneumophila",
    "Bordetella", "Bordetella pertussis",
    "Brucella", "Francisella", "Pasteurella",
    "Burkholderia", "Burkholderia cepacia",
    "Stenotrophomonas", "Stenotrophomonas maltophilia",

    # Bacterias atipicas / intracelulares
    "Mycobacterium", "Mycobacterium tuberculosis", "M. tuberculosis",
    "Mycobacterium leprae", "Mycobacterium avium",
    "Chlamydia", "Chlamydia trachomatis", "Chlamydia pneumoniae",
    "Chlamydophila",
    "Mycoplasma", "Mycoplasma pneumoniae",
    "Rickettsia", "Treponema", "Treponema pallidum",
    "Borrelia", "Borrelia burgdorferi",
    "Leptospira", "Coxiella",

    # Hongos
    "Candida", "Candida albicans", "Candida glabrata",
    "Candida tropicalis", "Candida parapsilosis", "Candida krusei",
    "Aspergillus", "Aspergillus fumigatus", "Aspergillus niger",
    "Cryptococcus", "Cryptococcus neoformans",
    "Pneumocystis", "Pneumocystis jirovecii", "Pneumocystis carinii",
    "Histoplasma", "Histoplasma capsulatum",
    "Coccidioides", "Paracoccidioides", "Paracoccidioides brasiliensis",
    "Sporothrix", "Mucor", "Rhizopus", "Fusarium",
    "Trichophyton", "Microsporum", "Malassezia",

    # Parasitos (protozoos)
    "Plasmodium", "Plasmodium falciparum", "Plasmodium vivax",
    "Plasmodium malariae", "Plasmodium ovale",
    "Toxoplasma", "Toxoplasma gondii",
    "Leishmania", "Trypanosoma", "Trypanosoma cruzi",
    "Giardia", "Giardia lamblia", "Giardia intestinalis",
    "Entamoeba", "Entamoeba histolytica",
    "Cryptosporidium", "Trichomonas", "Trichomonas vaginalis",
    "Babesia",

    # Parasitos (helmintos)
    "Ascaris", "Ascaris lumbricoides",
    "Enterobius", "Enterobius vermicularis",
    "Trichuris", "Ancylostoma", "Necator", "Strongyloides",
    "Taenia", "Taenia solium", "Taenia saginata",
    "Echinococcus", "Echinococcus granulosus",
    "Schistosoma", "Fasciola", "Fasciola hepatica",

    # Virus
    "Influenza", "Influenza A", "Influenza B",
    "SARS-CoV-2", "SARS-CoV", "MERS-CoV", "Coronavirus",
    "Rhinovirus", "Adenovirus", "Metapneumovirus",
    "VSR", "VRS", "Virus sincicial respiratorio",
    "Rotavirus", "Norovirus", "Astrovirus",
    "Hepatitis A", "Hepatitis B", "Hepatitis C", "Hepatitis D", "Hepatitis E",
    "VHB", "VHC", "VHA", "HBsAg", "anti-HBs", "anti-HCV",
    "VIH", "HIV",
    "VHS", "Herpes simplex", "Herpes zoster",
    "VEB", "Epstein-Barr", "CMV", "Citomegalovirus",
    "VVZ", "Varicela-zoster",
    "Parvovirus", "Parvovirus B19",
    "Sarampion", "Rubeola", "Parotiditis",
    "Dengue", "Zika", "Chikungunya", "Fiebre amarilla",
    "Hantavirus", "Arenavirus",
    "Papilomavirus", "VPH", "HPV",
    "Poliovirus",

    # Jerga clinica de microorganismos
    "estafilococo", "estreptococo", "enterococo", "neumococo",
    "meningococo", "gonococo",
    "bacilo de Koch", "BK",
    "gram positivo", "gram negativo", "gram +", "gram -",
    "cocos", "bacilos", "espirilos",
    "flora normal", "flora habitual", "flora mixta",
    "anaerobio", "aerobio", "microaerofilo",
    "multirresistente", "XDR", "MDR", "carbapenemasa",
    "BLEE", "ESBL",

    # ── TÉRMINOS ANATÓMICOS ───────────────────────────────
    "Vesícula", "vesicula", "Bazo", "bazo",
    "Retroperitoneo", "retroperitoneo", "Pancreas", "pancreas", "Páncreas",
    "Vejiga", "vejiga", "Testículos", "testiculos", "Testículo", "testiculo",
    "Vena", "vena", "Venas", "venas", "Arteria", "arteria",
    "Orejuela", "orejuela", "Septum", "septum",
    "Aneurisma", "aneurisma", "Willis", "willis",
    "parenquima", "parénquima", "islote",
    "Anexial", "anexial", "homolat",

    # ── PROCEDIMIENTOS Y CIRUGÍAS ─────────────────────────
    "nefrostomia", "nefrostomía",
    "Nefrectomía", "nefrectomia",
    "Colecistectomía", "colecistectomia",
    "Colpo", "colpo", "colposcopia",
    "Centellograma", "centellograma",
    "broncograma", "Consolidacion", "consolidacion",
    "angiorm", "angioRM", "neuroqx",
    "Hemod", "hemod", "hemodiálisis",
    "derivar", "DERIVAR",

    # ── ABREVIATURAS CLÍNICAS ─────────────────────────────
    "SU", "UR", "Ur", "TUS", "UCO", "ETT",
    "KU", "FENA", "Hbglic", "HCx2",
    "Alb", "alb", "Ca", "PT5", "AcF",
    "Labo", "labo", "Dx", "dx",
    "Ao", "ao", "VI", "LID",
    "Bude", "bude", "Indican", "indican",
    "Azitro", "azitro",
    "c/12", "c/8", "c/6", "c/24",
    "GR", "gr",

    # ── VALORES Y PARÁMETROS DE LABORATORIO ──────────────
    "Proteinas", "proteinas", "Transferrina", "transferrina",
    "Antígeno", "antigeno", "Hbglic",
    "Lactato", "lactato", "Làctico", "lactico",
    "Vit B12", "B12", "Ac Folico", "acido folico",
    "Liq Ascitico", "liquido ascitico",
    "oligoanuria", "Oligoanuria",
    "Hipocalcemia", "hipocalcemia",
    "Trousseau", "trousseau",
    "Hipertrofia", "hipertrofia",
    "Godet", "godet",
    "Cobertura", "cobertura",
    "Observacion", "observación",
    "Abundantes", "abundantes",
    "Ingresa", "ingresa",

    # ── SEROLOGÍA Y MICROBIOLOGÍA ─────────────────────────
    "vdrl", "VDRL", "AgSHBV", "HBsAg",
    "IgGtoxo", "toxo",
    "NR", "neg", "reactivo",

    # ── FÁRMACOS NO INCLUIDOS ANTES ───────────────────────
    "Fosfomicina", "fosfomicina",
    "Tigeciclin", "tigeciclin", "tigeciclina",
    "ertapenem", "Ertapenem",
    "Cisplatino", "cisplatino",
    "Etoposido", "etoposido", "etopósido",
    "Bleomicina", "bleomicina",
    "Terbinafina", "terbinafina",
    "cristaloides",

    # ── ECOCARDIOGRAMA / CARDIOLOGÍA ─────────────────────
    "Trivalva", "trivalva",
    "hipocontráctil", "hipocontractil",
    "Tricuspídea", "tricuspidea",
    "Estenosis Aórtica", "estenosis aortica",
    "esclerocalcificada", "esclerocalcificacion",
    "Insuficiencia Mitral", "insuficiencia mitral",
    "Fx Sistólica", "fx sistolica",
    "Fx Diastólica", "fx diastolica",
    "Válvula Aórtica", "valvula aortica",
    "Velocidades", "velocidades",
    "Anillo Mitral", "anillo mitral",
    "Urico", "urico",
    "Color", "color",

    # ── ANATOMÍA Y ÓRGANOS ───────────────────────────────
    "vejiga", "pancreas", "páncreas", "bazo", "vesícula", "vena", "venas",
    "arteria", "arterias", "retroperitoneo", "parénquima", "testículos",
    "testículo", "orejuela", "septum", "anillo mitral", "válvula aórtica",
    "anexo", "anexial", "Willis", "islote", "islotes",

    # ── TÉRMINOS CLÍNICOS / PROCEDIMIENTOS ADICIONALES ───
    "nefrostomia", "nefrostomía", "nefrectomia", "nefrectomía",
    "colecistectomia", "colecistectomía", "broncograma", "consolidacion",
    "consolidación", "oligoanuria", "cristaloides", "aneurisma",
    "centellograma", "angiorm", "hipertrofia", "hipocontractil",
    "hipocontráctil", "coraliformes",
    "colpo", "colposcopia", "neuroqx", "derivar",

    # ── ESTUDIOS Y PARÁMETROS DE LABORATORIO ─────────────
    "proteinas", "proteínas", "transferrina", "albumina", "alb",
    "acido folico", "ac folico", "acf", "vit b12", "b12",
    "hbglic", "fena", "láctico", "lactico", "ur", "ku",
    "antígeno", "antigeno", "indican", "cobertura", "dx",
    "liq ascitico", "líquido ascítico", "observacion", "observación",
    "vdrl", "agsHBV", "agshbv", "igg toxo", "iggtoxo",
    "hcx2", "hc+punta", "no hay ett", "ett",
    "cisplatino", "etoposido", "etopósido", "bleomicina",
    "terbinafina", "fosfomicina", "tigeciclin", "ertapenem",
    "azitro", "azitromicina",
    "hipocalcemia", "trousseau",
    "fx sistólica", "fx diastólica", "fx sistolica", "fx diastolica",
    "insuficiencia tricuspidea", "tricuspídea", "tricuspidea",
    "estenosis aortica", "estenosis aórtica", "esclerocalcificacion",
    "esclerocalcificación", "velocidades",
    "hemod", "hemodiálisis", "hemodialisis",
    "labo", "godet", "bude", "homolat", "ao",
    "adenomeg", "adenomegalia",
    "su", "uco", "tus", "tur",
    "lido", "lid", "consolidacion lid",
    "t2", "señal",
    "c/12", "c/8", "c/6", "c/24",
    "ingresa",

    # ── TÉRMINOS ADICIONALES DETECTADOS COMO FALSOS POSITIVOS ──
    # Fármacos y principios activos adicionales
    "terbinafina",
    # Procedimientos y cirugías
    "colecistectomia", "colecistectomía",
    # Abreviaturas y términos ecocardiográficos / cardiológicos
    "bude", "godet", "labo",
    "hipertrofia", "ao",
    "fx sistolica", "fx sistólica", "fx diastolica", "fx diastólica",
    "fx sistolica vi", "fx sistólica vi", "fx sistólica vi izquierda",
    "orejuela", "orejuela izquierda",
    "hipocontractil", "hipocontráctil",
    "valvula aortica", "válvula aórtica",
    "valvula aortica trivalva", "válvula aórtica trivalva", "trivalva",
    "velocidades",
    "estenosis aortica", "estenosis aórtica",
    "estenosis aortica leve", "estenosis aórtica leve",
    "esclerocalcificada", "esclerocalcificacion", "esclerocalcificación",
    "esclerocalcificacion del anillo mitral", "esclerocalcificación del anillo mitral",
    "anillo mitral",
    "insuficiencia",
    "tricuspidea", "tricuspídea",
    "insuficiencia tricuspidea", "insuficiencia tricuspídea",
    "septum",
    # Laboratorio
    "color", "urico", "ur", "abundantes",
    "acido urico",
    # Cobertura / administrativa
    "cobertura",
    # Términos de presentación clínica
    "ingresa",

    # ── TÉRMINOS ADICIONALES (corregidos de falsos positivos) ──
    # Cardiología / ecocardiografía
    "fx sistolica", "fx diastolica", "fx sistólica", "fx diastólica",
    "fx sistolica vi", "fx sistolica vi izquierda",
    "septum", "orejuela", "orejuela izquierda",
    "tricuspidea", "tricuspídea",
    "valvula aortica", "válvula aórtica",
    "valvula aortica trivalva", "válvula aórtica trivalva",
    "trivalva",
    "hipocontractil", "hipocontráctil",
    "velocidades",
    "estenosis aortica", "estenosis aórtica",
    "estenosis aortica leve", "estenosis aórtica leve",
    "estenosis aortica leve esclerocalcificada",
    "esclerocalcificacion", "esclerocalcificación",
    "esclerocalcificacion del anillo mitral",
    "esclerocalcificación del anillo mitral",
    "anillo mitral",
    "insuficiencia",
    "ao",

    # Fármacos y abreviaturas de fármacos
    "terbinafina",
    "bude",  # abreviatura de budesonida

    # Procedimientos / términos administrativos clínicos
    "colecistectomia", "colecistectomía",
    "cobertura",
    "ingresa",

    # Abreviaturas y jerga de HC
    "labo",       # laboratorio
    "ur",         # urea
    "urico",      # ácido úrico

    # Signos clínicos
    "godet",      # signo del godet (edema con fóvea)
    "hipertrofia",
    "color",      # en contexto de laboratorio (color de orina)
    "abundantes", # en contexto de sedimento urinario

    # ── AGREGA TUS PROPIOS TERMINOS AQUI ─────────────────
    # "MiMicroorganismo", "mi_farmaco", "mi_enfermedad", ...
])



# ══════════════════════════════════════════════════════════
#  CARGA DE TÉRMINOS EXTRA DESDE ARCHIVO EXTERNO
#  Editá terminos_extra.txt con el Bloc de notas para
#  agregar términos sin tocar el código.
# ══════════════════════════════════════════════════════════

ARCHIVO_TERMINOS_EXTRA = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "terminos_extra.txt"
)

def cargar_terminos_extra() -> set:
    """
    Lee terminos_extra.txt (una línea por término) y devuelve
    un set en minúsculas listo para unirse a LISTA_BLANCA_MEDICA.
    Si el archivo no existe lo crea vacío con instrucciones.
    """
    if not os.path.exists(ARCHIVO_TERMINOS_EXTRA):
        with open(ARCHIVO_TERMINOS_EXTRA, "w", encoding="utf-8") as f:
            f.write(
                "# TÉRMINOS EXTRA — uno por línea\n"
                "# Las líneas que empiezan con # son comentarios (se ignoran)\n"
                "# No importa si escribís en mayúsculas o minúsculas\n"
                "#\n"
                "# Ejemplos:\n"
                "#   Godet\n"
                "#   Terbinafina\n"
                "#   Fx Sistólica\n"
            )
        print(f"📄 Archivo creado: {ARCHIVO_TERMINOS_EXTRA}")
        return set()

    terminos = set()
    with open(ARCHIVO_TERMINOS_EXTRA, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea and not linea.startswith("#"):
                terminos.add(linea.lower())
    return terminos

# ══════════════════════════════════════════════════════════
#  1. CONFIGURACIÓN DEL MOTOR NLP EN ESPAÑOL
# ══════════════════════════════════════════════════════════

def crear_motor_nlp():
    configuracion = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "es", "model_name": "es_core_news_md"}],
    }
    proveedor = NlpEngineProvider(nlp_configuration=configuracion)
    return proveedor.create_engine()


# ══════════════════════════════════════════════════════════
#  2. SISTEMA DE AUTOAPRENDIZAJE
#     Recuerda entre sesiones qué términos son médicos.
# ══════════════════════════════════════════════════════════

# Archivo de memoria — se crea junto a este script.
ARCHIVO_APRENDIZAJE = Path(__file__).parent / "terminos_aprendidos.txt"

# Conjunto en memoria para la sesión actual (se suma a la lista blanca)
_terminos_sesion: set = set()


def cargar_terminos_aprendidos() -> set:
    """Carga los términos guardados en sesiones anteriores."""
    if not ARCHIVO_APRENDIZAJE.exists():
        return set()
    try:
        terminos = set()
        with open(ARCHIVO_APRENDIZAJE, "r", encoding="utf-8") as f:
            for linea in f:
                t = linea.strip()
                if t and not t.startswith("#"):
                    terminos.add(t.lower())
        if terminos:
            print(f"📚 {len(terminos)} término(s) aprendido(s) de sesiones anteriores.")
        return terminos
    except Exception as e:
        print(f"⚠️  No se pudo leer {ARCHIVO_APRENDIZAJE}: {e}")
        return set()


def guardar_termino_aprendido(termino: str) -> bool:
    """Agrega un término al archivo de aprendizaje (evita duplicados)."""
    termino_lower = termino.strip().lower()
    existentes = cargar_terminos_aprendidos()
    if termino_lower in existentes:
        return False
    try:
        with open(ARCHIVO_APRENDIZAJE, "a", encoding="utf-8") as f:
            f.write(termino_lower + "\n")
        return True
    except Exception as e:
        print(f"⚠️  No se pudo guardar '{termino}': {e}")
        return False


def revisar_detecciones(resultados: list, texto: str,
                         blanca_extra: set) -> tuple:
    """
    Para cada detección que pasó el filtro de lista blanca,
    pregunta al usuario si es dato personal real o término médico.
    Devuelve (a_anonimizar, nuevos_aprendidos).
    """
    a_anonimizar = []
    aprendidos_sesion = []
    ya_preguntados = {}   # cache: evita preguntar el mismo término dos veces

    print("\n" + "─" * 58)
    print("  MODO REVISIÓN — confirmá cada detección")
    print("  s = anonimizar  |  n = proteger y recordar  |  Enter = anonimizar")
    print("─" * 58)

    for r in resultados:
        fragmento = texto[r.start:r.end]
        frag_lower = fragmento.lower().strip()

        # Si ya fue revisado en esta sesión, reusar decisión
        if frag_lower in ya_preguntados:
            if ya_preguntados[frag_lower]:
                a_anonimizar.append(r)
            continue

        # Contexto: 45 chars antes y después
        ini = max(0, r.start - 45)
        fin = min(len(texto), r.end + 45)
        ctx = texto[ini:fin].replace("\n", " ")
        pos = r.start - ini
        ctx_visual = ctx[:pos] + f">>>{fragmento}<<<" + ctx[pos + len(fragmento):]

        print(f"\n  [{r.entity_type}] '{fragmento}'  (confianza {r.score:.0%})")
        print(f"  Contexto: ...{ctx_visual}...")

        while True:
            resp = input("  ¿Anonimizar? [s/Enter=sí  n=no, es médico]: ").strip().lower()
            if resp in ("s", "n", ""):
                break

        if resp == "n":
            guardar_termino_aprendido(fragmento)
            blanca_extra.add(frag_lower)
            _terminos_sesion.add(frag_lower)
            aprendidos_sesion.append(fragmento)
            ya_preguntados[frag_lower] = False
            print(f"  🛡️  '{fragmento}' protegido y guardado en memoria.")
        else:
            a_anonimizar.append(r)
            ya_preguntados[frag_lower] = True

    return a_anonimizar, aprendidos_sesion


# ══════════════════════════════════════════════════════════
#  3. FILTRO DE LISTA BLANCA
# ══════════════════════════════════════════════════════════

# Patrones numéricos que NUNCA son datos personales.
# Captura valores de laboratorio, hemogramas, gases en sangre, etc.
# Ejemplos: 35.7/11.5/7400  |  7.39/40.7/-0.4/24.4  |  N73% L17%  |  6200/464000
PATRON_LABORATORIO = re.compile(
    r"""
    # Formato num/num/num.../num  (hemograma, gases, ionograma, etc.)
    (?:\d+[\.,]?\d*\s*/\s*){1,6}\d+[\.,]?\d*
    |
    # Formato con letras: N73% L17% E7%  (fórmula leucocitaria)
    (?:[A-Z]{1,3}\d{1,3}%\s*){2,}
    |
    # Número con % y letra inicial: N73%  L17%  E7%
    [A-Z]{1,3}\d{1,3}%
    |
    # Rangos y valores simples con unidades pegadas: 2800 N73%
    \d{3,7}\s+[A-Z]{1}\d{2,3}%
    |
    # Secuencias tipo 0.88  139/3.8/110  (con espacios entre grupos)
    \d+[\.,]\d+\s+\d+[\.,]?\d*/\d+[\.,]?\d*/\d+[\.,]?\d*
    """,
    re.VERBOSE
)

def es_valor_laboratorio(texto_fragmento: str) -> bool:
    """Devuelve True si el fragmento parece un valor numérico de laboratorio."""
    t = texto_fragmento.strip()
    # Si más del 40% son dígitos o separadores numéricos → es laboratorio
    chars_numericos = sum(1 for c in t if c.isdigit() or c in ".,/%")
    if len(t) > 0 and chars_numericos / len(t) > 0.40:
        return True
    if PATRON_LABORATORIO.search(t):
        return True
    return False

def filtrar_lista_blanca(resultados: list, texto: str,
                          extra: set = None) -> list:
    """
    Elimina resultados cuyo texto:
    - coincida con la lista blanca médica o términos aprendidos, O
    - parezca un valor numérico de laboratorio / hemograma.
    """
    filtrados = []
    for r in resultados:
        fragmento = texto[r.start:r.end].lower().strip()
        palabras = set(re.findall(r'\b\w+\b', fragmento))

        # Filtro 1: lista blanca de términos médicos + aprendidos
        blanca = LISTA_BLANCA_MEDICA | (extra or set())
        if fragmento in blanca:
            continue
        if palabras & blanca:
            continue

        # Filtro 2: valores numéricos de laboratorio
        if es_valor_laboratorio(texto[r.start:r.end]):
            continue

        filtrados.append(r)
    return filtrados


# ══════════════════════════════════════════════════════════
#  4. RECONOCEDORES PERSONALIZADOS PARA ARGENTINA
# ══════════════════════════════════════════════════════════

def crear_reconocedores_argentina():
    reconocedores = []

    reconocedores.append(PatternRecognizer(
        supported_entity="ARG_DNI",
        patterns=[
            Pattern("dni_puntos",  r"\b\d{2}\.\d{3}\.\d{3}\b", 0.95),
            Pattern("dni_palabra", r"\b(?:DNI|D\.N\.I\.?)\s*:?\s*\d{7,8}\b", 0.95),
        ],
        context=["dni", "documento", "identidad", "cedula"],
        supported_language="es"
    ))

    reconocedores.append(PatternRecognizer(
        supported_entity="ARG_CUIL",
        patterns=[Pattern("cuil", r"\b\d{2}-\d{7,8}-\d\b", 0.95)],
        context=["cuil", "cuit"],
        supported_language="es"
    ))

    reconocedores.append(PatternRecognizer(
        supported_entity="NRO_HC",
        patterns=[
            Pattern("nro_hc",
                r"\b(?:HC|H\.C\.|historia\s+cl[ií]nica)\s*[:\-]?\s*\d{4,10}\b",
                0.90),
        ],
        context=["historia", "clinica", "paciente", "registro"],
        supported_language="es"
    ))

    reconocedores.append(PatternRecognizer(
        supported_entity="TELEFONO_AR",
        patterns=[
            Pattern("tel_ar",
                r"\b(?:\+?54\s?)?(?:9\s?)?(?:11|[2-9]\d{2,3})\s?[\-\s]?\d{4}[\-\s]?\d{4}\b",
                0.75),
        ],
        context=["tel", "telefono", "celular", "cel", "contacto"],
        supported_language="es"
    ))

    reconocedores.append(PatternRecognizer(
        supported_entity="DOMICILIO",
        patterns=[
            Pattern("domicilio",
                r"\b(?:calle|av\.|avenida|pje\.|pasaje|bv\.|boulevard)\s+[\w\s]+\s+\d{1,5}\b",
                0.70),
        ],
        context=["domicilio", "direccion", "vive", "reside"],
        supported_language="es"
    ))

    reconocedores.append(PatternRecognizer(
        supported_entity="MATRICULA_MED",
        patterns=[
            Pattern("matricula",
                r"\b(?:M\.?[NP]\.?|mat\.?|matr\.?)\s*:?\s*\d{4,7}\b",
                0.90),
        ],
        context=["matricula", "medico", "profesional", "mn", "mp"],
        supported_language="es"
    ))

    return reconocedores


# ══════════════════════════════════════════════════════════
#  5. OPERADORES DE REEMPLAZO
# ══════════════════════════════════════════════════════════

OPERADORES = {
    "PERSON":           OperatorConfig("replace", {"new_value": "[PERSONA]"}),
    "LOCATION":         OperatorConfig("replace", {"new_value": "[UBICACION]"}),
    "ORG":              OperatorConfig("replace", {"new_value": "[INSTITUCION]"}),
    "EMAIL_ADDRESS":    OperatorConfig("replace", {"new_value": "[EMAIL]"}),
    "PHONE_NUMBER":     OperatorConfig("replace", {"new_value": "[TELEFONO]"}),
    "ARG_DNI":          OperatorConfig("replace", {"new_value": "[DNI]"}),
    "ARG_CUIL":         OperatorConfig("replace", {"new_value": "[CUIL]"}),
    "NRO_HC":           OperatorConfig("replace", {"new_value": "[NRO_HC]"}),
    "TELEFONO_AR":      OperatorConfig("replace", {"new_value": "[TELEFONO]"}),
    "DOMICILIO":        OperatorConfig("replace", {"new_value": "[DOMICILIO]"}),
    "MATRICULA_MED":    OperatorConfig("replace", {"new_value": "[MATRICULA]"}),
    "NRP":              OperatorConfig("replace", {"new_value": "[MATRICULA]"}),
    "MEDICAL_LICENSE":  OperatorConfig("replace", {"new_value": "[MATRICULA]"}),
}


# ══════════════════════════════════════════════════════════
#  6. FUNCIÓN PRINCIPAL DE ANONIMIZACIÓN
# ══════════════════════════════════════════════════════════

def anonimizar_texto(texto: str, analyzer, anonymizer):
    """
    Devuelve (texto_anonimizado, entidades_anonimizadas, entidades_protegidas).
    """
    resultados_brutos = analyzer.analyze(
        text=texto,
        language="es",
        entities=[
            "PERSON", "LOCATION", "ORG",
            "EMAIL_ADDRESS", "PHONE_NUMBER",
            "ARG_DNI", "ARG_CUIL", "NRO_HC",
            "TELEFONO_AR", "DOMICILIO",
            "MATRICULA_MED", "NRP", "MEDICAL_LICENSE",
        ],
        score_threshold=0.4
    )

    a_anonimizar = filtrar_lista_blanca(resultados_brutos, texto, _terminos_sesion)
    protegidos = [r for r in resultados_brutos if r not in a_anonimizar]

    if not a_anonimizar:
        return texto, [], protegidos

    texto_anon = anonymizer.anonymize(
        text=texto,
        analyzer_results=a_anonimizar,
        operators=OPERADORES
    )
    return texto_anon.text, a_anonimizar, protegidos


# ══════════════════════════════════════════════════════════
#  7. PROCESAMIENTO DE ARCHIVOS
# ══════════════════════════════════════════════════════════

def procesar_archivo(ruta_entrada: str, analyzer, anonymizer,
                     modo_revision: bool = False):
    nombre_base = os.path.splitext(ruta_entrada)[0]
    ruta_salida = f"{nombre_base}_ANONIMIZADO.txt"

    with open(ruta_entrada, "r", encoding="utf-8") as f:
        texto_original = f.read()

    # En modo revisión: primero detectar, luego preguntar, luego anonimizar
    if modo_revision:
        resultados_brutos = analyzer.analyze(
            text=texto_original, language="es",
            entities=["PERSON","LOCATION","ORG","EMAIL_ADDRESS","PHONE_NUMBER",
                      "ARG_DNI","ARG_CUIL","NRO_HC","TELEFONO_AR","DOMICILIO",
                      "MATRICULA_MED","NRP","MEDICAL_LICENSE"],
            score_threshold=0.4
        )
        candidatos = filtrar_lista_blanca(resultados_brutos, texto_original, _terminos_sesion)
        candidatos_rev, nuevos = revisar_detecciones(candidatos, texto_original, _terminos_sesion)
        protegidos_rev = [r for r in resultados_brutos if r not in candidatos_rev]
        if candidatos_rev:
            from presidio_anonymizer import AnonymizerEngine as _AE
            _anon = _AE()
            res = _anon.anonymize(text=texto_original, analyzer_results=candidatos_rev, operators=OPERADORES)
            texto_anon_rev = res.text
        else:
            texto_anon_rev = texto_original
        texto_anon, anonimizados, protegidos = texto_anon_rev, candidatos_rev, protegidos_rev
        if nuevos:
            print(f"\n  📝 {len(nuevos)} término(s) nuevo(s) guardado(s): {', '.join(nuevos)}")
    else:
        texto_anon, anonimizados, protegidos = anonimizar_texto(
            texto_original, analyzer, anonymizer
        )

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(texto_anon)

    print(f"\n✅ {ruta_entrada}  →  {ruta_salida}")
    print(f"   🔒 Datos anonimizados ({len(anonimizados)}):")
    for e in sorted(anonimizados, key=lambda x: x.start):
        frag = texto_original[e.start:e.end]
        print(f"      [{e.entity_type:18s}] '{frag}' ({e.score:.0%})")
    if protegidos:
        print(f"   🛡️  Términos médicos protegidos — NO anonimizados ({len(protegidos)}):")
        for e in sorted(protegidos, key=lambda x: x.start):
            frag = texto_original[e.start:e.end]
            print(f"      [PROTEGIDO] '{frag}'")
    return ruta_salida


def procesar_carpeta(ruta_carpeta: str, analyzer, anonymizer,
                     modo_revision: bool = False):
    archivos = [
        os.path.join(ruta_carpeta, f)
        for f in os.listdir(ruta_carpeta)
        if f.endswith(".txt") and "ANONIMIZADO" not in f
    ]
    if not archivos:
        print(f"⚠️  No se encontraron archivos .txt en '{ruta_carpeta}'")
        return
    print(f"\n📂 {len(archivos)} archivo(s) en '{ruta_carpeta}'")
    for archivo in archivos:
        procesar_archivo(archivo, analyzer, anonymizer, modo_revision)


# ══════════════════════════════════════════════════════════
#  8. MODO DEMO
# ══════════════════════════════════════════════════════════

TEXTO_EJEMPLO = """
Paciente: Maria Fernanda Gonzalez
DNI: 28.456.789  —  Fecha de nacimiento: 15/03/1975
Domicilio: Av. Corrientes 3450, CABA
Tel: 011-4567-8901  |  Email: mfgonzalez@gmail.com

Historia clinica HC-00123 — Ingreso: 10/03/2026
Institucion: Hospital Italiano de Buenos Aires
Medico tratante: Dr. Carlos Ramirez (MN 45678)

Evolucion:
Paciente con antecedentes de hipertension arterial y diabetes tipo 2
en tratamiento con enalapril 10 mg/dia y metformina 850 mg c/12hs.
Refiere dolor precordial de 2 horas de evolucion. TA 150/95, FC 98 lpm, SaO2 96%.
Se indica ECG y laboratorio urgente. Se solicita interconsulta con cardiologia.
La Dra. Lopez prescribe AAS 325 mg, atorvastatina 40 mg y clopidogrel 75 mg.
Se coordina traslado al servicio de hemodinamia del Hospital Italiano.
"""


def modo_interactivo(analyzer, anonymizer):
    sep = "=" * 62
    print(f"\n{sep}\n  MODO DEMO — texto clinico de ejemplo\n{sep}")
    print("\n📄 TEXTO ORIGINAL:")
    print(TEXTO_EJEMPLO)

    texto_anon, anonimizados, protegidos = anonimizar_texto(
        TEXTO_EJEMPLO, analyzer, anonymizer
    )

    print("\n🔒 TEXTO ANONIMIZADO:")
    print(texto_anon)

    print("\n📋 REPORTE:")
    print(f"  🔒 Datos personales anonimizados ({len(anonimizados)}):")
    for e in sorted(anonimizados, key=lambda x: x.start):
        frag = TEXTO_EJEMPLO[e.start:e.end]
        print(f"     [{e.entity_type:18s}] '{frag}'")

    print(f"\n  🛡️  Terminos medicos protegidos — NO anonimizados ({len(protegidos)}):")
    for e in sorted(protegidos, key=lambda x: x.start):
        frag = TEXTO_EJEMPLO[e.start:e.end]
        print(f"     [PROTEGIDO] '{frag}'")

    print(f"\n{sep}")
    print("  ✅ Todo procesado LOCALMENTE. Ningun dato salio de tu PC.")
    print(f"{sep}\n")


# ══════════════════════════════════════════════════════════
#  9. PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════

def main():
    print("\n⏳ Cargando modelos NLP (puede tardar unos segundos)...")

    # Cargar términos extra desde archivo externo
    terminos_extra = cargar_terminos_extra()
    if terminos_extra:
        LISTA_BLANCA_MEDICA.update(terminos_extra)
        print(f"📚 {len(terminos_extra)} término(s) extra cargados desde terminos_extra.txt")
    else:
        print(f"📄 Sin términos extra  (editá terminos_extra.txt para agregar)")

    nlp_engine = crear_motor_nlp()
    reconocedores = crear_reconocedores_argentina()

    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["es"])
    for rec in reconocedores:
        analyzer.registry.add_recognizer(rec)

    anonymizer = AnonymizerEngine()
    print("✅ Modelos listos.\n")

    # Cargar términos aprendidos en sesiones anteriores
    aprendidos = cargar_terminos_aprendidos()
    _terminos_sesion.update(aprendidos)

    # Detectar flag --revisar
    modo_revision = "--revisar" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--revisar"]

    if modo_revision:
        print("🔍 MODO REVISIÓN activado — se preguntará por cada detección dudosa.\n")

    if len(args) == 0:
        modo_interactivo(analyzer, anonymizer)
    elif len(args) == 1:
        ruta = args[0]
        if os.path.isdir(ruta):
            procesar_carpeta(ruta, analyzer, anonymizer, modo_revision)
        elif os.path.isfile(ruta) and ruta.endswith(".txt"):
            procesar_archivo(ruta, analyzer, anonymizer, modo_revision)
        else:
            print(f"❌ No se encontro '{ruta}'. Debe ser un .txt o una carpeta.")
            sys.exit(1)
    else:
        print("Uso:")
        print("  python anonimizar_clinico.py                        → demo")
        print("  python anonimizar_clinico.py archivo.txt            → procesar")
        print("  python anonimizar_clinico.py archivo.txt --revisar  → con revisión")
        print("  python anonimizar_clinico.py carpeta/               → carpeta entera")
        print("  python anonimizar_clinico.py carpeta/ --revisar     → carpeta con revisión")


if __name__ == "__main__":
    main()