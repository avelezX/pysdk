from data_collectors.suameca.SuamecaCollector import SuamecaCollector
from db_connection.supabase.Client import SupabaseConnection

collector = SuamecaCollector()

# Full SUAMECA series catalog (858 series)
# Mapping: suameca_id = SUAMECA catalog ID, internal_id = our banrep_series_value_v2.id_serie
# IDs 1-33 were assigned by legacy collectors (totoro SDMX + file-based)
# IDs 34+ are new series from the expanded SUAMECA catalog

series = [

    # === Inflación y meta (1 series) ===
    {"suameca_id":   853, "internal_id":  34, "name": "META-INFLACION"},

    # === Indice de Precios al Consumidor (IPC) por ciudad - Base 2018 (23 series) ===
    {"suameca_id": 15017, "internal_id":  35, "name": "IPC-ARMENIA"},
    {"suameca_id": 15016, "internal_id":  36, "name": "IPC-BARRANQUILLA"},
    {"suameca_id": 15013, "internal_id":  37, "name": "IPC-BOGOTA-D.C."},
    {"suameca_id": 15018, "internal_id":  38, "name": "IPC-BUCARAMANGA"},
    {"suameca_id": 15014, "internal_id":  39, "name": "IPC-CALI"},
    {"suameca_id": 15019, "internal_id":  40, "name": "IPC-CARTAGENA-DE-IN"},
    {"suameca_id": 15020, "internal_id":  41, "name": "IPC-CUCUTA"},
    {"suameca_id": 15021, "internal_id":  42, "name": "IPC-FLORENCIA"},
    {"suameca_id": 15022, "internal_id":  43, "name": "IPC-IBAGUE"},
    {"suameca_id": 15023, "internal_id":  44, "name": "IPC-MANIZALES"},
    {"suameca_id": 15015, "internal_id":  45, "name": "IPC-MEDELLIN"},
    {"suameca_id": 15024, "internal_id":  46, "name": "IPC-MONTERIA"},
    {"suameca_id": 15025, "internal_id":  47, "name": "IPC-NEIVA"},
    {"suameca_id": 15035, "internal_id":  48, "name": "IPC-OTRAS-AREAS-URB"},
    {"suameca_id": 15026, "internal_id":  49, "name": "IPC-PASTO"},
    {"suameca_id": 15027, "internal_id":  50, "name": "IPC-PEREIRA"},
    {"suameca_id": 15028, "internal_id":  51, "name": "IPC-POPAYAN"},
    {"suameca_id": 15029, "internal_id":  52, "name": "IPC-RIOHACHA"},
    {"suameca_id": 15030, "internal_id":  53, "name": "IPC-SANTA-MARTA"},
    {"suameca_id": 15031, "internal_id":  54, "name": "IPC-SINCELEJO"},
    {"suameca_id": 15032, "internal_id":  55, "name": "IPC-TUNJA"},
    {"suameca_id": 15033, "internal_id":  56, "name": "IPC-VALLEDUPAR"},
    {"suameca_id": 15034, "internal_id":  57, "name": "IPC-VILLAVICENCIO"},

    # === Indice de Precios al Consumidor (IPC) total y por división de gasto - Base 2018 (31 series) ===
    {"suameca_id": 15270, "internal_id":   7, "name": "IPC-VAR"},
    {"suameca_id": 15000, "internal_id":  58, "name": "IPC-TOTAL"},
    {"suameca_id": 15001, "internal_id":  59, "name": "IPC-ALIM-BEB"},
    {"suameca_id": 15002, "internal_id":  60, "name": "IPC-BEB-ALC"},
    {"suameca_id": 15003, "internal_id":  61, "name": "IPC-VESTIDO"},
    {"suameca_id": 15004, "internal_id":  62, "name": "IPC-ALOJAM"},
    {"suameca_id": 15005, "internal_id":  63, "name": "IPC-MUEBLES"},
    {"suameca_id": 15006, "internal_id":  64, "name": "IPC-SALUD"},
    {"suameca_id": 15007, "internal_id":  65, "name": "IPC-TRANSPORTE"},
    {"suameca_id": 15008, "internal_id":  66, "name": "IPC-INFO-COM"},
    {"suameca_id": 15009, "internal_id":  67, "name": "IPC-RECREAC"},
    {"suameca_id": 15010, "internal_id":  68, "name": "IPC-EDUCACION"},
    {"suameca_id": 15011, "internal_id":  69, "name": "IPC-REST-HOT"},
    {"suameca_id": 15012, "internal_id":  70, "name": "IPC-DIVERSOS"},
    {"suameca_id": 15387, "internal_id":  71, "name": "INFL-TOTAL-A"},
    {"suameca_id": 15404, "internal_id":  72, "name": "INFL-ALIM"},
    {"suameca_id": 15405, "internal_id":  73, "name": "INFL-BEB"},
    {"suameca_id": 15406, "internal_id":  74, "name": "INFL-VEST"},
    {"suameca_id": 15407, "internal_id":  75, "name": "INFL-ALOJ"},
    {"suameca_id": 15408, "internal_id":  76, "name": "INFL-MUEB"},
    {"suameca_id": 15409, "internal_id":  77, "name": "INFL-SALUD"},
    {"suameca_id": 15410, "internal_id":  78, "name": "INFL-TRANSP"},
    {"suameca_id": 15411, "internal_id":  79, "name": "INFL-INFO"},
    {"suameca_id": 15412, "internal_id":  80, "name": "INFL-RECREAC"},
    {"suameca_id": 15413, "internal_id":  81, "name": "INFL-EDUC"},
    {"suameca_id": 15414, "internal_id":  82, "name": "INFL-REST"},
    {"suameca_id": 15415, "internal_id":  83, "name": "INFL-DIV"},
    {"suameca_id": 17252, "internal_id":  84, "name": "IPC-ALIMENTOS"},
    {"suameca_id": 17253, "internal_id":  85, "name": "IPC-ALIM-REG"},
    {"suameca_id": 17254, "internal_id":  86, "name": "INFL-ALIM-REG"},
    {"suameca_id": 17255, "internal_id":  87, "name": "INFL-ALIM-REG-A"},

    # === Indice de Precios del Productor (IPP) según actividad económica - Base 2014 (8 series) ===
    {"suameca_id":     3, "internal_id":  88, "name": "IPP-TOTAL"},
    {"suameca_id":   348, "internal_id":  89, "name": "IPP-PN-AGRO"},
    {"suameca_id":   349, "internal_id":  90, "name": "IPP-PN-MINAS"},
    {"suameca_id":   350, "internal_id":  91, "name": "IPP-PN-IND"},
    {"suameca_id":   351, "internal_id":  92, "name": "IPP-OI-TOTAL"},
    {"suameca_id":   352, "internal_id":  93, "name": "IPP-OI-AGRO"},
    {"suameca_id":   353, "internal_id":  94, "name": "IPP-OI-MINAS"},
    {"suameca_id":   354, "internal_id":  95, "name": "IPP-OI-IND"},

    # === Indice de Precios del Productor (IPP) según procedencia de bienes - Base 2014 (3 series) ===
    {"suameca_id":   355, "internal_id":  96, "name": "IPP-PROD-CONS"},
    {"suameca_id":   356, "internal_id":  97, "name": "IPP-IMPORT"},
    {"suameca_id":   358, "internal_id":  98, "name": "IPP-EXPORT"},

    # === Indice de Precios del Productor (IPP) según uso o destino económico - Base 2014 (4 series) ===
    {"suameca_id":   359, "internal_id":  99, "name": "IPP-CONS-INT"},
    {"suameca_id":   360, "internal_id": 100, "name": "IPP-CONS-FIN"},
    {"suameca_id":   361, "internal_id": 101, "name": "IPP-CAPITAL"},
    {"suameca_id":   362, "internal_id": 102, "name": "IPP-CONSTR"},

    # === Indice de Precios de la Vivienda Nueva (IPVNBR) (10 series) ===
    {"suameca_id": 17260, "internal_id": 103, "name": "IPVNBR-NOM-BOG"},
    {"suameca_id": 17261, "internal_id": 104, "name": "IPVNBR-REAL-BOG"},
    {"suameca_id": 17262, "internal_id": 105, "name": "IPVNBR-NOM-ALRED"},
    {"suameca_id": 17263, "internal_id": 106, "name": "IPVNBR-REAL-ALRED"},
    {"suameca_id": 17264, "internal_id": 107, "name": "IPVNBR-NOM-MED"},
    {"suameca_id": 17265, "internal_id": 108, "name": "IPVNBR-REAL-MED"},
    {"suameca_id": 17266, "internal_id": 109, "name": "IPVNBR-NOM-CALI"},
    {"suameca_id": 17267, "internal_id": 110, "name": "IPVNBR-REAL-CALI"},
    {"suameca_id": 17268, "internal_id": 111, "name": "IPVNBR-NOM-AGG"},
    {"suameca_id": 17269, "internal_id": 112, "name": "IPVNBR-REAL-AGG"},

    # === Indice de Precios de la Vivienda Usada (IPVU) (4 series) ===
    {"suameca_id":    56, "internal_id": 113, "name": "IPVU-NOM-T"},
    {"suameca_id":    57, "internal_id": 114, "name": "IPVU-REAL-T"},
    {"suameca_id": 17540, "internal_id": 115, "name": "IPVU-NOM-A"},
    {"suameca_id": 17541, "internal_id": 116, "name": "IPVU-REAL-A"},

    # === Unidad de Valor Real (UVR) (1 series) ===
    {"suameca_id":   850, "internal_id":  19, "name": "UVR"},

    # === Unidad de Poder Adquisitivo Constante (UPAC) (1 series) ===
    {"suameca_id":    90, "internal_id": 117, "name": "UPAC"},

    # === Inflación básica - Base 2018 (24 series) ===
    {"suameca_id": 15314, "internal_id": 118, "name": "IPC-SIN-ALIM"},
    {"suameca_id": 15315, "internal_id": 119, "name": "IPC-SIN-ALIM-REG"},
    {"suameca_id": 15316, "internal_id": 120, "name": "IPC-NUCLEO15"},
    {"suameca_id": 15317, "internal_id": 121, "name": "IPC-BIENES-SIN"},
    {"suameca_id": 15318, "internal_id": 122, "name": "IPC-SERV-SIN"},
    {"suameca_id": 15319, "internal_id": 123, "name": "IPC-REGULADOS"},
    {"suameca_id": 15388, "internal_id": 124, "name": "INFL-SIN-ALIM"},
    {"suameca_id": 15389, "internal_id": 125, "name": "INFL-SIN-ALIM-A"},
    {"suameca_id": 15390, "internal_id": 126, "name": "INFL-SIN-ALIMREG"},
    {"suameca_id": 15391, "internal_id": 127, "name": "INFL-SIN-ALIMREG-A"},
    {"suameca_id": 15392, "internal_id": 128, "name": "INFL-NUC15"},
    {"suameca_id": 15393, "internal_id": 129, "name": "INFL-NUC15-A"},
    {"suameca_id": 15394, "internal_id": 130, "name": "INFL-BIENES"},
    {"suameca_id": 15395, "internal_id": 131, "name": "INFL-BIENES-A"},
    {"suameca_id": 15396, "internal_id": 132, "name": "INFL-SERVICIOS"},
    {"suameca_id": 15397, "internal_id": 133, "name": "INFL-SERVICIOS-A"},
    {"suameca_id": 15398, "internal_id": 134, "name": "INFL-REG"},
    {"suameca_id": 15399, "internal_id": 135, "name": "INFL-REG-A"},
    {"suameca_id": 15400, "internal_id": 136, "name": "INFL-SIN-ALIM-BR"},
    {"suameca_id": 15401, "internal_id": 137, "name": "INFL-SIN-ALIMREG-BR"},
    {"suameca_id": 15402, "internal_id": 138, "name": "INFL-SIN-ALIMPRIM"},
    {"suameca_id": 15403, "internal_id": 139, "name": "INFL-NUC20"},
    {"suameca_id": 17250, "internal_id": 140, "name": "INFL-ALIMENTOS"},
    {"suameca_id": 17251, "internal_id": 141, "name": "INFL-ALIMENTOS-A"},

    # === Precios de metales preciosos - regalías (3 series) ===
    {"suameca_id": 15293, "internal_id": 142, "name": "ORO-REGAL"},
    {"suameca_id": 15654, "internal_id": 143, "name": "PLATA-REGAL"},
    {"suameca_id": 15655, "internal_id": 144, "name": "PLATINO-REGAL"},

    # === Precios de metales preciosos - precios diarios (2 series) ===
    {"suameca_id":    52, "internal_id": 145, "name": "PLATINO-COMPRA"},
    {"suameca_id":    55, "internal_id": 146, "name": "PLATINO-VENTA"},

    # === Tasas de captación diarias (47 series) ===
    {"suameca_id": 17322, "internal_id": 147, "name": "CAPT-CDT-OFIC-M"},
    {"suameca_id": 17301, "internal_id": 148, "name": "CAPT-CDT-OFIC"},
    {"suameca_id": 17323, "internal_id": 149, "name": "CAPT-CDT-TESOR-M"},
    {"suameca_id": 17302, "internal_id": 150, "name": "CAPT-CDT-TESOR"},
    {"suameca_id": 15632, "internal_id": 151, "name": "INTERBANCARIA-MONTO"},
    {"suameca_id": 17329, "internal_id": 152, "name": "CDAT181+D-M"},
    {"suameca_id": 17308, "internal_id": 153, "name": "CDAT181+D"},
    {"suameca_id": 17326, "internal_id": 154, "name": "CDAT30D-M"},
    {"suameca_id": 17305, "internal_id": 155, "name": "CDAT30D"},
    {"suameca_id": 17330, "internal_id": 156, "name": "CDATOFICD-M"},
    {"suameca_id": 17309, "internal_id": 157, "name": "CDATOFICD"},
    {"suameca_id": 17325, "internal_id": 158, "name": "CDAT15-29D-M"},
    {"suameca_id": 17304, "internal_id": 159, "name": "CDAT15-29D"},
    {"suameca_id": 17324, "internal_id": 160, "name": "CDAT2-14D-M"},
    {"suameca_id": 17303, "internal_id": 161, "name": "CDAT2-14D"},
    {"suameca_id": 17327, "internal_id": 162, "name": "CDAT31-90D-M"},
    {"suameca_id": 17306, "internal_id": 163, "name": "CDAT31-90D"},
    {"suameca_id": 17328, "internal_id": 164, "name": "CDAT91-180D-M"},
    {"suameca_id": 17307, "internal_id": 165, "name": "CDAT91-180D"},
    {"suameca_id": 17318, "internal_id": 166, "name": "CDT120D-M"},
    {"suameca_id": 17297, "internal_id": 167, "name": "CDT120D"},
    {"suameca_id": 17332, "internal_id": 168, "name": "CDT180D-M"},
    {"suameca_id":   239, "internal_id": 169, "name": "CDT180D"},
    {"suameca_id": 17311, "internal_id": 170, "name": "CDT30D-M"},
    {"suameca_id": 17290, "internal_id": 171, "name": "CDT30D"},
    {"suameca_id": 17333, "internal_id": 172, "name": "CDT360D-M"},
    {"suameca_id":   240, "internal_id": 173, "name": "CDT360D"},
    {"suameca_id": 17313, "internal_id": 174, "name": "CDT45D-M"},
    {"suameca_id": 17292, "internal_id": 175, "name": "CDT45D"},
    {"suameca_id": 17315, "internal_id": 176, "name": "CDT60D-M"},
    {"suameca_id": 17294, "internal_id": 177, "name": "CDT60D"},
    {"suameca_id": 17331, "internal_id": 178, "name": "CDT90D-M"},
    {"suameca_id":   238, "internal_id": 179, "name": "CDT90D"},
    {"suameca_id": 17319, "internal_id": 180, "name": "CDT121-179D-M"},
    {"suameca_id": 17298, "internal_id": 181, "name": "CDT121-179D"},
    {"suameca_id": 17320, "internal_id": 182, "name": "CDT181-359D-M"},
    {"suameca_id": 17299, "internal_id": 183, "name": "CDT181-359D"},
    {"suameca_id": 17312, "internal_id": 184, "name": "CDT31-44D-M"},
    {"suameca_id": 17291, "internal_id": 185, "name": "CDT31-44D"},
    {"suameca_id": 17314, "internal_id": 186, "name": "CDT46-59D-M"},
    {"suameca_id": 17293, "internal_id": 187, "name": "CDT46-59D"},
    {"suameca_id": 17316, "internal_id": 188, "name": "CDT61-89D-M"},
    {"suameca_id": 17295, "internal_id": 189, "name": "CDT61-89D"},
    {"suameca_id": 17317, "internal_id": 190, "name": "CDT91-119D-M"},
    {"suameca_id": 17296, "internal_id": 191, "name": "CDT91-119D"},
    {"suameca_id": 17321, "internal_id": 192, "name": "CDT360+D-M"},
    {"suameca_id": 17300, "internal_id": 193, "name": "CDT360+D"},

    # === Tasas de captación semanales (3 series) ===
    {"suameca_id":    65, "internal_id":  21, "name": "DTF90S"},
    {"suameca_id":    67, "internal_id":  17, "name": "CDT180S"},
    {"suameca_id":    68, "internal_id":  18, "name": "CDT360S"},

    # === Tasas de captación mensuales (2 series) ===
    {"suameca_id":    70, "internal_id":  20, "name": "DTF90M"},
    {"suameca_id": 17334, "internal_id":  30, "name": "DTF90D"},

    # IBR deposit rates (1d, 1m, 3m, 6m, 12m — nominal + efectiva) are collected
    # by run_collect_ibr_marks.py which runs on a dedicated schedule. Do NOT add
    # them here to avoid duplicate rows in banrep_series_value_v2.

    # === Tasa Interbancaria (TIB) (1 series) ===
    {"suameca_id":    89, "internal_id":  24, "name": "TIB"},

    # === Tasas de colocación semanales (19 series) ===
    {"suameca_id": 15105, "internal_id": 196, "name": "COL-ADQ-NOVIS-COP-S"},
    {"suameca_id": 15106, "internal_id": 197, "name": "COL-ADQ-NOVIS-UVR-S"},
    {"suameca_id": 15107, "internal_id": 198, "name": "COL-ADQ-VIS-COP-S"},
    {"suameca_id": 15108, "internal_id": 199, "name": "COL-ADQ-VIS-UVR-S"},
    {"suameca_id": 15101, "internal_id": 200, "name": "COL-CONSTR-NOVIS-COP-S"},
    {"suameca_id": 15102, "internal_id": 201, "name": "COL-CONSTR-NOVIS-UVR-S"},
    {"suameca_id": 15103, "internal_id": 202, "name": "COL-CONSTR-VIS-COP-S"},
    {"suameca_id": 15104, "internal_id": 203, "name": "COL-CONSTR-VIS-UVR-S"},
    {"suameca_id": 15111, "internal_id": 204, "name": "COL-CONSUMO-S"},
    {"suameca_id": 17281, "internal_id": 205, "name": "COL-POP-PROD-S"},
    {"suameca_id": 17282, "internal_id": 206, "name": "COL-PRODUCTIVO-S"},
    {"suameca_id": 17283, "internal_id": 207, "name": "COL-PROD-MAYOR-S"},
    {"suameca_id": 15113, "internal_id": 208, "name": "COL-COMER-ORD-S"},
    {"suameca_id": 15114, "internal_id": 209, "name": "COL-COMER-PREF-S"},
    {"suameca_id": 15115, "internal_id": 210, "name": "COL-COMER-TESOR-S"},
    {"suameca_id": 15112, "internal_id": 211, "name": "COL-MICRO-S"},
    {"suameca_id": 15109, "internal_id": 212, "name": "COL-BANREP-S"},
    {"suameca_id": 17280, "internal_id": 213, "name": "COL-SIN-TESOR-S"},
    {"suameca_id": 15110, "internal_id": 214, "name": "COL-TOTAL-S"},

    # === Tasas de colocación mensuales (19 series) ===
    {"suameca_id": 15116, "internal_id": 215, "name": "COL-CONSTR-NOVIS-COP-M"},
    {"suameca_id": 15117, "internal_id": 216, "name": "COL-CONSTR-NOVIS-UVR-M"},
    {"suameca_id": 15118, "internal_id": 217, "name": "COL-CONSTR-VIS-COP-M"},
    {"suameca_id": 15119, "internal_id": 218, "name": "COL-CONSTR-VIS-UVR-M"},
    {"suameca_id": 15120, "internal_id": 219, "name": "COL-ADQ-NOVIS-COP-M"},
    {"suameca_id": 15121, "internal_id": 220, "name": "COL-ADQ-NOVIS-UVR-M"},
    {"suameca_id": 15122, "internal_id": 221, "name": "COL-ADQ-VIS-COP-M"},
    {"suameca_id": 15123, "internal_id": 222, "name": "COL-ADQ-VIS-UVR-M"},
    {"suameca_id": 15124, "internal_id": 223, "name": "COL-BANREP-M"},
    {"suameca_id": 15125, "internal_id": 224, "name": "COL-TOTAL-M"},
    {"suameca_id": 15126, "internal_id": 225, "name": "COL-CONSUMO-M"},
    {"suameca_id": 15127, "internal_id": 226, "name": "COL-MICRO-M"},
    {"suameca_id": 15128, "internal_id": 227, "name": "COL-COMER-ORD-M"},
    {"suameca_id": 15129, "internal_id": 228, "name": "COL-COMER-PREF-M"},
    {"suameca_id": 15130, "internal_id": 229, "name": "COL-COMER-TESOR-M"},
    {"suameca_id": 17284, "internal_id": 230, "name": "COL-SIN-TESOR-M"},
    {"suameca_id": 17285, "internal_id": 231, "name": "COL-POP-PROD-M"},
    {"suameca_id": 17286, "internal_id": 232, "name": "COL-PRODUCTIVO-M"},
    {"suameca_id": 17287, "internal_id": 233, "name": "COL-PROD-MAYOR-M"},

    # === Tasas de interés TES (14 series) ===
    {"suameca_id": 15272, "internal_id":  31, "name": "TES-1Y"},
    {"suameca_id": 15273, "internal_id":  32, "name": "TES-5Y"},
    {"suameca_id": 15274, "internal_id":  33, "name": "TES-10Y"},
    {"suameca_id": 15275, "internal_id": 234, "name": "TES-UVR-1Y"},
    {"suameca_id": 15276, "internal_id": 235, "name": "TES-UVR-5Y"},
    {"suameca_id": 15277, "internal_id": 236, "name": "TES-UVR-10Y"},
    {"suameca_id": 15278, "internal_id": 237, "name": "TES-BETA-COP-B0"},
    {"suameca_id": 15279, "internal_id": 238, "name": "TES-BETA-COP-B1"},
    {"suameca_id": 15280, "internal_id": 239, "name": "TES-BETA-COP-B2"},
    {"suameca_id": 15281, "internal_id": 240, "name": "TES-BETA-COP-TAU"},
    {"suameca_id": 15282, "internal_id": 241, "name": "TES-BETA-UVR-B0"},
    {"suameca_id": 15283, "internal_id": 242, "name": "TES-BETA-UVR-B1"},
    {"suameca_id": 15284, "internal_id": 243, "name": "TES-BETA-UVR-B2"},
    {"suameca_id": 15285, "internal_id": 244, "name": "TES-BETA-UVR-TAU"},

    # === Tasas de interés externa PRIME (1 series) ===
    {"suameca_id":    88, "internal_id": 245, "name": "PRIME"},

    # === Tasa de Interés de Política Monetaria (1 series) ===
    {"suameca_id":    59, "internal_id":   8, "name": "TPM"},

    # === Agregados Monetarios (42 series) ===
    {"suameca_id":   168, "internal_id":  27, "name": "M1-M"},
    {"suameca_id":   169, "internal_id":  28, "name": "M2-M"},
    {"suameca_id":   170, "internal_id":  29, "name": "M3-M"},
    {"suameca_id":   153, "internal_id": 246, "name": "BASE-MON-M"},
    {"suameca_id":   174, "internal_id": 247, "name": "BASE-MON-S"},
    {"suameca_id":   158, "internal_id": 248, "name": "CUASI-CDT-M"},
    {"suameca_id":   179, "internal_id": 249, "name": "CUASI-CDT-S"},
    {"suameca_id":   157, "internal_id": 250, "name": "CUASI-AHORRO-M"},
    {"suameca_id":   178, "internal_id": 251, "name": "CUASI-AHORRO-S"},
    {"suameca_id":   159, "internal_id": 252, "name": "CUASI-TOTAL-M"},
    {"suameca_id":   180, "internal_id": 253, "name": "CUASI-TOTAL-S"},
    {"suameca_id":   163, "internal_id": 254, "name": "DEP-BONOS-M"},
    {"suameca_id":   184, "internal_id": 255, "name": "DEP-BONOS-S"},
    {"suameca_id":   162, "internal_id": 256, "name": "DEP-CEDULAS-M"},
    {"suameca_id":   183, "internal_id": 257, "name": "DEP-CEDULAS-S"},
    {"suameca_id":   154, "internal_id": 258, "name": "DEP-CC-PRIV-M"},
    {"suameca_id":   175, "internal_id": 259, "name": "DEP-CC-PRIV-S"},
    {"suameca_id":   155, "internal_id": 260, "name": "DEP-CC-PUB-M"},
    {"suameca_id":   176, "internal_id": 261, "name": "DEP-CC-PUB-S"},
    {"suameca_id":   156, "internal_id": 262, "name": "DEP-CC-TOT-M"},
    {"suameca_id":   177, "internal_id": 263, "name": "DEP-CC-TOT-S"},
    {"suameca_id":   167, "internal_id": 264, "name": "DEP-TOTAL-M"},
    {"suameca_id":   188, "internal_id": 265, "name": "DEP-TOTAL-S"},
    {"suameca_id":   161, "internal_id": 266, "name": "DEP-FIDUC-M"},
    {"suameca_id":   182, "internal_id": 267, "name": "DEP-FIDUC-S"},
    {"suameca_id":   171, "internal_id": 268, "name": "DEP-RESTR-M"},
    {"suameca_id":   192, "internal_id": 269, "name": "DEP-RESTR-S"},
    {"suameca_id":   151, "internal_id": 270, "name": "EFECTIVO-M"},
    {"suameca_id":   172, "internal_id": 271, "name": "EFECTIVO-S"},
    {"suameca_id":   189, "internal_id": 272, "name": "M1-S"},
    {"suameca_id":   190, "internal_id": 273, "name": "M2-S"},
    {"suameca_id":   191, "internal_id": 274, "name": "M3-S"},
    {"suameca_id":   160, "internal_id": 275, "name": "DEP-OTROS-M"},
    {"suameca_id":   181, "internal_id": 276, "name": "DEP-OTROS-S"},
    {"suameca_id":   152, "internal_id": 277, "name": "RES-BANC-M"},
    {"suameca_id":   173, "internal_id": 278, "name": "RES-BANC-S"},
    {"suameca_id":   165, "internal_id": 279, "name": "REPOS-NOFINL-M"},
    {"suameca_id":   186, "internal_id": 280, "name": "REPOS-NOFINL-S"},
    {"suameca_id":   164, "internal_id": 281, "name": "REPOS-DGCPTN-M"},
    {"suameca_id":   185, "internal_id": 282, "name": "REPOS-DGCPTN-S"},
    {"suameca_id":   166, "internal_id": 283, "name": "REPOS-TOTAL-M"},
    {"suameca_id":   187, "internal_id": 284, "name": "REPOS-TOTAL-S"},

    # === Agregados Crediticios (36 series) ===
    {"suameca_id":   364, "internal_id": 285, "name": "CART-COM-MEX-M"},
    {"suameca_id":   194, "internal_id": 286, "name": "CART-COM-MEX-S"},
    {"suameca_id":   363, "internal_id": 287, "name": "CART-COM-ML-M"},
    {"suameca_id":   193, "internal_id": 288, "name": "CART-COM-ML-S"},
    {"suameca_id":   196, "internal_id": 289, "name": "CART-CONS-MEX-S"},
    {"suameca_id":   195, "internal_id": 290, "name": "CART-CONS-ML-S"},
    {"suameca_id":   366, "internal_id": 291, "name": "CART-CONS-MEX-M"},
    {"suameca_id":   365, "internal_id": 292, "name": "CART-CONS-ML-M"},
    {"suameca_id":   368, "internal_id": 293, "name": "CART-MICRO-MEX-M"},
    {"suameca_id":   367, "internal_id": 294, "name": "CART-MICRO-ML-M"},
    {"suameca_id":   372, "internal_id": 295, "name": "CART-HIP-AJ-MEX-M"},
    {"suameca_id":   202, "internal_id": 296, "name": "CART-HIP-AJ-MEX-S"},
    {"suameca_id":   371, "internal_id": 297, "name": "CART-HIP-AJ-ML-M"},
    {"suameca_id":   201, "internal_id": 298, "name": "CART-HIP-AJ-ML-S"},
    {"suameca_id":   370, "internal_id": 299, "name": "CART-HIP-MEX-M"},
    {"suameca_id":   200, "internal_id": 300, "name": "CART-HIP-MEX-S"},
    {"suameca_id":   369, "internal_id": 301, "name": "CART-HIP-ML-M"},
    {"suameca_id":   199, "internal_id": 302, "name": "CART-HIP-ML-S"},
    {"suameca_id":   198, "internal_id": 303, "name": "CART-MICRO-MEX-S"},
    {"suameca_id":   197, "internal_id": 304, "name": "CART-MICRO-ML-S"},
    {"suameca_id":   376, "internal_id": 305, "name": "CART-BRUTA-AJ-MEX-M"},
    {"suameca_id":   206, "internal_id": 306, "name": "CART-BRUTA-AJ-MEX-S"},
    {"suameca_id":   375, "internal_id": 307, "name": "CART-BRUTA-AJ-ML-M"},
    {"suameca_id":   205, "internal_id": 308, "name": "CART-BRUTA-AJ-ML-S"},
    {"suameca_id":   374, "internal_id": 309, "name": "CART-BRUTA-MEX-M"},
    {"suameca_id":   204, "internal_id": 310, "name": "CART-BRUTA-MEX-S"},
    {"suameca_id":   373, "internal_id": 311, "name": "CART-BRUTA-ML-M"},
    {"suameca_id":   203, "internal_id": 312, "name": "CART-BRUTA-ML-S"},
    {"suameca_id":   380, "internal_id": 313, "name": "CART-NETA-AJ-MEX-M"},
    {"suameca_id":   210, "internal_id": 314, "name": "CART-NETA-AJ-MEX-S"},
    {"suameca_id":   379, "internal_id": 315, "name": "CART-NETA-AJ-ML-M"},
    {"suameca_id":   209, "internal_id": 316, "name": "CART-NETA-AJ-ML-S"},
    {"suameca_id":   378, "internal_id": 317, "name": "CART-NETA-MEX-M"},
    {"suameca_id":   208, "internal_id": 318, "name": "CART-NETA-MEX-S"},
    {"suameca_id":   377, "internal_id": 319, "name": "CART-NETA-ML-M"},
    {"suameca_id":   207, "internal_id": 320, "name": "CART-NETA-ML-S"},

    # === Sectorización monetaria y de crédito - Banco de la República / Sector Financiero (10 series) ===
    {"suameca_id": 16688, "internal_id": 321, "name": "M1-SIN-GNC"},
    {"suameca_id": 16690, "internal_id": 322, "name": "CRED-NETO-PUB"},
    {"suameca_id": 16691, "internal_id": 323, "name": "CRED-BRUTO-PRIV"},
    {"suameca_id": 16692, "internal_id": 324, "name": "ACT-NETOS-EXT"},
    {"suameca_id": 16693, "internal_id": 325, "name": "SECT-RES-MON"},
    {"suameca_id": 16694, "internal_id": 326, "name": "SECT-CRED-PUB"},
    {"suameca_id": 16695, "internal_id": 327, "name": "SECT-CRED-PRIV"},
    {"suameca_id": 16696, "internal_id": 328, "name": "SECT-CRED-BRUTO-FIN"},
    {"suameca_id": 16697, "internal_id": 329, "name": "SECT-CRED-NETO-FIN"},
    {"suameca_id": 16698, "internal_id": 330, "name": "SECT-ACT-EXT"},

    # === Encaje (15 series) ===
    {"suameca_id": 16580, "internal_id": 331, "name": "ENCAJE-DISP-D"},
    {"suameca_id": 16581, "internal_id": 332, "name": "ENCAJE-DISP-BI"},
    {"suameca_id": 16582, "internal_id": 333, "name": "ENCAJE-REQ-BI"},
    {"suameca_id": 16583, "internal_id": 334, "name": "ENCAJE-POS-BI"},
    {"suameca_id": 16584, "internal_id": 335, "name": "ENCAJE-CAJA"},
    {"suameca_id": 16585, "internal_id": 336, "name": "PSE-TOTAL"},
    {"suameca_id": 16586, "internal_id": 337, "name": "PSE-CC"},
    {"suameca_id": 16587, "internal_id": 338, "name": "PSE-CDT-TOT"},
    {"suameca_id": 16588, "internal_id": 339, "name": "PSE-CDT-18"},
    {"suameca_id": 16589, "internal_id": 340, "name": "PSE-AHORRO"},
    {"suameca_id": 16590, "internal_id": 341, "name": "PSE-FIDUC"},
    {"suameca_id": 16591, "internal_id": 342, "name": "PSE-REPOS"},
    {"suameca_id": 16592, "internal_id": 343, "name": "PSE-BONOS"},
    {"suameca_id": 16593, "internal_id": 344, "name": "PSE-OTROS"},
    {"suameca_id": 16594, "internal_id": 345, "name": "PSE-ABANDON"},

    # === Índice de mercado accionario - COLCAP (1 series) ===
    {"suameca_id":     6, "internal_id":  26, "name": "COLCAP"},

    # === Reservas internacionales (4 series) ===
    {"suameca_id": 15050, "internal_id": 346, "name": "RES-INT-BRUTAS"},
    {"suameca_id": 15051, "internal_id": 347, "name": "RES-INT-NETAS"},
    {"suameca_id": 15052, "internal_id": 348, "name": "RES-INT-BRUTAS-SF"},
    {"suameca_id": 15053, "internal_id": 349, "name": "RES-INT-NETAS-SF"},

    # === Operaciones forward NDF (6 series) ===
    {"suameca_id": 16656, "internal_id": 350, "name": "NDF-VENTA"},
    {"suameca_id": 16660, "internal_id": 351, "name": "NDF-CUPO"},
    {"suameca_id": 16661, "internal_id": 352, "name": "NDF-PRES"},
    {"suameca_id": 16662, "internal_id": 353, "name": "NDF-APROB"},
    {"suameca_id": 16663, "internal_id": 354, "name": "NDF-TASA"},
    {"suameca_id": 16664, "internal_id": 355, "name": "FXSWAP-CUPO"},

    # === Operaciones FX Swaps (4 series) ===
    {"suameca_id": 16657, "internal_id": 356, "name": "FXSWAP-VENTA"},
    {"suameca_id": 16665, "internal_id": 357, "name": "FXSWAP-DEM"},
    {"suameca_id": 16666, "internal_id": 358, "name": "FXSWAP-APROB"},
    {"suameca_id": 16667, "internal_id": 359, "name": "FXSWAP-TASA"},

    # === Subasta de compra directa de dólares (4 series) ===
    {"suameca_id": 16684, "internal_id": 360, "name": "COMPRA-USD-CUPO"},
    {"suameca_id": 16685, "internal_id": 361, "name": "COMPRA-USD-PRES"},
    {"suameca_id": 16686, "internal_id": 362, "name": "COMPRA-USD-APROB"},
    {"suameca_id": 16687, "internal_id": 363, "name": "COMPRA-USD-PRIMA"},

    # === Operaciones en el mercado monetario - expansión transitoria (37 series) ===
    {"suameca_id": 16770, "internal_id": 364, "name": "EXP-1D-CUPO"},
    {"suameca_id": 16771, "internal_id": 365, "name": "EXP-7D-CUPO"},
    {"suameca_id": 16772, "internal_id": 366, "name": "EXP-14D-CUPO"},
    {"suameca_id": 16773, "internal_id": 367, "name": "EXP-30D-CUPO"},
    {"suameca_id": 16774, "internal_id": 368, "name": "EXP-90D-CUPO"},
    {"suameca_id": 16775, "internal_id": 369, "name": "EXP-180D-CUPO"},
    {"suameca_id": 16776, "internal_id": 370, "name": "EXP-270D-CUPO"},
    {"suameca_id": 16777, "internal_id": 371, "name": "EXP-360D-CUPO"},
    {"suameca_id": 16778, "internal_id": 372, "name": "EXP-1D-DEM"},
    {"suameca_id": 16779, "internal_id": 373, "name": "EXP-7D-DEM"},
    {"suameca_id": 16780, "internal_id": 374, "name": "EXP-14D-DEM"},
    {"suameca_id": 16781, "internal_id": 375, "name": "EXP-30D-DEM"},
    {"suameca_id": 16782, "internal_id": 376, "name": "EXP-90D-DEM"},
    {"suameca_id": 16783, "internal_id": 377, "name": "EXP-180D-DEM"},
    {"suameca_id": 16784, "internal_id": 378, "name": "EXP-270D-DEM"},
    {"suameca_id": 16785, "internal_id": 379, "name": "EXP-360D-DEM"},
    {"suameca_id": 16786, "internal_id": 380, "name": "EXP-1D-APROB"},
    {"suameca_id": 16787, "internal_id": 381, "name": "EXP-7D-APROB"},
    {"suameca_id": 16788, "internal_id": 382, "name": "EXP-14D-APROB"},
    {"suameca_id": 16789, "internal_id": 383, "name": "EXP-30D-APROB"},
    {"suameca_id": 16790, "internal_id": 384, "name": "EXP-90D-APROB"},
    {"suameca_id": 16791, "internal_id": 385, "name": "EXP-180D-APROB"},
    {"suameca_id": 16792, "internal_id": 386, "name": "EXP-270D-APROB"},
    {"suameca_id": 16793, "internal_id": 387, "name": "EXP-360D-APROB"},
    {"suameca_id": 16794, "internal_id": 388, "name": "EXP-1D-TASA"},
    {"suameca_id": 16795, "internal_id": 389, "name": "EXP-7D-TASA"},
    {"suameca_id": 16796, "internal_id": 390, "name": "EXP-14D-TASA"},
    {"suameca_id": 16797, "internal_id": 391, "name": "EXP-30D-TASA"},
    {"suameca_id": 16798, "internal_id": 392, "name": "EXP-90D-TASA"},
    {"suameca_id": 16799, "internal_id": 393, "name": "EXP-180D-TASA"},
    {"suameca_id": 16800, "internal_id": 394, "name": "EXP-270D-TASA"},
    {"suameca_id": 16801, "internal_id": 395, "name": "EXP-360D-TASA"},
    {"suameca_id": 16803, "internal_id": 396, "name": "EXP-VENT-DEM"},
    {"suameca_id": 16804, "internal_id": 397, "name": "EXP-VENT-APROB"},
    {"suameca_id": 16805, "internal_id": 398, "name": "EXP-VENT-TASA"},
    {"suameca_id": 17500, "internal_id": 399, "name": "EXP-SALDO-1D"},
    {"suameca_id": 17501, "internal_id": 400, "name": "EXP-SALDO-OTROS"},

    # === Operaciones en el mercado monetario - depósitos remunerados de contracción (25 series) ===
    {"suameca_id": 16870, "internal_id": 401, "name": "CONTR-7D-CUPO"},
    {"suameca_id": 16871, "internal_id": 402, "name": "CONTR-14D-CUPO"},
    {"suameca_id": 16872, "internal_id": 403, "name": "CONTR-30D-CUPO"},
    {"suameca_id": 16873, "internal_id": 404, "name": "CONTR-90D-CUPO"},
    {"suameca_id": 16874, "internal_id": 405, "name": "CONTR-60D-CUPO"},
    {"suameca_id": 16875, "internal_id": 406, "name": "CONTR-7D-DEM"},
    {"suameca_id": 16876, "internal_id": 407, "name": "CONTR-14D-DEM"},
    {"suameca_id": 16877, "internal_id": 408, "name": "CONTR-30D-DEM"},
    {"suameca_id": 16878, "internal_id": 409, "name": "CONTR-90D-DEM"},
    {"suameca_id": 16879, "internal_id": 410, "name": "CONTR-60D-DEM"},
    {"suameca_id": 16880, "internal_id": 411, "name": "CONTR-7D-APROB"},
    {"suameca_id": 16881, "internal_id": 412, "name": "CONTR-14D-APROB"},
    {"suameca_id": 16882, "internal_id": 413, "name": "CONTR-30D-APROB"},
    {"suameca_id": 16883, "internal_id": 414, "name": "CONTR-90D-APROB"},
    {"suameca_id": 16884, "internal_id": 415, "name": "CONTR-60D-APROB"},
    {"suameca_id": 16885, "internal_id": 416, "name": "CONTR-7D-TASA"},
    {"suameca_id": 16886, "internal_id": 417, "name": "CONTR-14D-TASA"},
    {"suameca_id": 16887, "internal_id": 418, "name": "CONTR-30D-TASA"},
    {"suameca_id": 16888, "internal_id": 419, "name": "CONTR-90D-TASA"},
    {"suameca_id": 16889, "internal_id": 420, "name": "CONTR-60D-TASA"},
    {"suameca_id": 16891, "internal_id": 421, "name": "CONTR-VENT-DEM"},
    {"suameca_id": 16892, "internal_id": 422, "name": "CONTR-VENT-APROB"},
    {"suameca_id": 16893, "internal_id": 423, "name": "CONTR-VENT-TASA"},
    {"suameca_id": 17502, "internal_id": 424, "name": "CONTR-SALDO-SUB"},
    {"suameca_id": 17503, "internal_id": 425, "name": "CONTR-SALDO-VENT"},

    # === Tasa de cambio del peso colombiano (2 series) ===
    {"suameca_id":     1, "internal_id":  25, "name": "TRM"},
    {"suameca_id": 17716, "internal_id": 426, "name": "CERTIF-CAMBIO"},

    # === Tasas de cambio de países vecinos (10 series) ===
    {"suameca_id": 15640, "internal_id": 427, "name": "FX-PAB-C"},
    {"suameca_id": 15651, "internal_id": 428, "name": "FX-PAB-V"},
    {"suameca_id": 15642, "internal_id": 429, "name": "FX-VED-C"},
    {"suameca_id": 15653, "internal_id": 430, "name": "FX-VED-V"},
    {"suameca_id": 15641, "internal_id": 431, "name": "FX-PEN-C"},
    {"suameca_id": 15652, "internal_id": 432, "name": "FX-PEN-V"},
    {"suameca_id": 15638, "internal_id": 433, "name": "FX-BRL-C"},
    {"suameca_id": 15649, "internal_id": 434, "name": "FX-BRL-V"},
    {"suameca_id": 15639, "internal_id": 435, "name": "FX-ECS-C"},
    {"suameca_id": 15650, "internal_id": 436, "name": "FX-ECS-V"},

    # === Tasas de cambio de monedas de reserva (32 series) ===
    {"suameca_id": 15572, "internal_id": 437, "name": "FX-COPDKK-C"},
    {"suameca_id":    29, "internal_id": 438, "name": "FX-COPDKK"},
    {"suameca_id":    14, "internal_id": 439, "name": "FX-USDDKK"},
    {"suameca_id":    35, "internal_id": 440, "name": "FX-COPNOK"},
    {"suameca_id":    20, "internal_id": 441, "name": "FX-USDNOK"},
    {"suameca_id":    37, "internal_id": 442, "name": "FX-COPSEK"},
    {"suameca_id":    22, "internal_id": 443, "name": "FX-USDSEK"},
    {"suameca_id":    24, "internal_id": 444, "name": "FX-COPAUD"},
    {"suameca_id":     9, "internal_id": 445, "name": "FX-USDAUD"},
    {"suameca_id":    25, "internal_id": 446, "name": "FX-COPCAD"},
    {"suameca_id":    10, "internal_id": 447, "name": "FX-USDCAD"},
    {"suameca_id":    32, "internal_id": 448, "name": "FX-COPHKD"},
    {"suameca_id":    17, "internal_id": 449, "name": "FX-USDHKD"},
    {"suameca_id":    38, "internal_id": 450, "name": "FX-COPSGD"},
    {"suameca_id":    23, "internal_id": 451, "name": "FX-USDSGD"},
    {"suameca_id":    36, "internal_id": 452, "name": "FX-COPNZD"},
    {"suameca_id":    21, "internal_id": 453, "name": "FX-USDNZD"},
    {"suameca_id":    30, "internal_id": 454, "name": "FX-COPEUR"},
    {"suameca_id":    15, "internal_id": 455, "name": "FX-USDEUR"},
    {"suameca_id":    26, "internal_id": 456, "name": "FX-COPCHF"},
    {"suameca_id":    11, "internal_id": 457, "name": "FX-USDCHF"},
    {"suameca_id":    31, "internal_id": 458, "name": "FX-COPGBP"},
    {"suameca_id":    16, "internal_id": 459, "name": "FX-USDGBP"},
    {"suameca_id":    28, "internal_id": 460, "name": "FX-COPCNY"},
    {"suameca_id":    13, "internal_id": 461, "name": "FX-USDCNY"},
    {"suameca_id":    27, "internal_id": 462, "name": "FX-COPCNH"},
    {"suameca_id":    12, "internal_id": 463, "name": "FX-USDCNH"},
    {"suameca_id": 17100, "internal_id": 464, "name": "DEG"},
    {"suameca_id":    34, "internal_id": 465, "name": "FX-COPKRW"},
    {"suameca_id":    19, "internal_id": 466, "name": "FX-USDKRW"},
    {"suameca_id":    33, "internal_id": 467, "name": "FX-COPJPY"},
    {"suameca_id":    18, "internal_id": 468, "name": "FX-USDJPY"},

    # === Banda Cambiaria (14 series) ===
    {"suameca_id": 16700, "internal_id": 469, "name": "BCAM-CC-M"},
    {"suameca_id": 16701, "internal_id": 470, "name": "BCAM-CC-S"},
    {"suameca_id": 16702, "internal_id": 471, "name": "BCAM-COMERC-M"},
    {"suameca_id": 16703, "internal_id": 472, "name": "BCAM-COMERC-S"},
    {"suameca_id": 16704, "internal_id": 473, "name": "BCAM-SERV-M"},
    {"suameca_id": 16705, "internal_id": 474, "name": "BCAM-SERV-S"},
    {"suameca_id": 16706, "internal_id": 475, "name": "BCAM-CAP-M"},
    {"suameca_id": 16707, "internal_id": 476, "name": "BCAM-CAP-S"},
    {"suameca_id": 16708, "internal_id": 477, "name": "BCAM-FLUJO-M"},
    {"suameca_id": 16709, "internal_id": 478, "name": "BCAM-FLUJO-S"},
    {"suameca_id": 16710, "internal_id": 479, "name": "BCAM-OTRAS-M"},
    {"suameca_id": 16711, "internal_id": 480, "name": "BCAM-OTRAS-S"},
    {"suameca_id": 16712, "internal_id": 481, "name": "BCAM-VAR-RES-M"},
    {"suameca_id": 16713, "internal_id": 482, "name": "BCAM-VAR-RES-S"},

    # === Balanza de pagos - Metodología BPM6 (31 series) ===
    {"suameca_id": 15131, "internal_id": 483, "name": "BDP-IMP"},
    {"suameca_id": 15132, "internal_id": 484, "name": "BDP-EXP"},
    {"suameca_id": 15133, "internal_id": 485, "name": "BDP-IED"},
    {"suameca_id": 15134, "internal_id": 486, "name": "BDP-IDCE"},
    {"suameca_id": 15135, "internal_id": 487, "name": "BDP-BAL-COMERC"},
    {"suameca_id": 15136, "internal_id": 488, "name": "BDP-CC"},
    {"suameca_id": 15137, "internal_id": 489, "name": "BDP-VAR-RES"},
    {"suameca_id": 15138, "internal_id": 490, "name": "BDP-CF"},
    {"suameca_id": 15140, "internal_id": 491, "name": "BDP-ING-PRIM"},
    {"suameca_id": 15141, "internal_id": 492, "name": "BDP-ING-SEC"},
    {"suameca_id": 15703, "internal_id": 493, "name": "BDP-CC-BS"},
    {"suameca_id": 15706, "internal_id": 494, "name": "BDP-CC-BIENES"},
    {"suameca_id": 15707, "internal_id": 495, "name": "BDP-CC-EXP"},
    {"suameca_id": 15708, "internal_id": 496, "name": "BDP-CC-IMP"},
    {"suameca_id": 15717, "internal_id": 497, "name": "BDP-CC-ORO"},
    {"suameca_id": 15719, "internal_id": 498, "name": "BDP-CC-SERV"},
    {"suameca_id": 15917, "internal_id": 499, "name": "BDP-CC-SERV-IP"},
    {"suameca_id": 16052, "internal_id": 500, "name": "BDP-CC-SERV-IS"},
    {"suameca_id": 16142, "internal_id": 501, "name": "BDP-CF2"},
    {"suameca_id": 16143, "internal_id": 502, "name": "BDP-CF-ID"},
    {"suameca_id": 16144, "internal_id": 503, "name": "BDP-CF-ID-ACT"},
    {"suameca_id": 16170, "internal_id": 504, "name": "BDP-CF-ID-PAS"},
    {"suameca_id": 16196, "internal_id": 505, "name": "BDP-CF-IC"},
    {"suameca_id": 16197, "internal_id": 506, "name": "BDP-CF-IC-ACT"},
    {"suameca_id": 16234, "internal_id": 507, "name": "BDP-CF-IC-PAS"},
    {"suameca_id": 16271, "internal_id": 508, "name": "BDP-CF-DERIV"},
    {"suameca_id": 16303, "internal_id": 509, "name": "BDP-CF-OTRA"},
    {"suameca_id": 16527, "internal_id": 510, "name": "BDP-CF-RES"},
    {"suameca_id": 16544, "internal_id": 511, "name": "BDP-ERRORES"},
    {"suameca_id": 15290, "internal_id": 512, "name": "CC-PIB-T"},
    {"suameca_id": 15311, "internal_id": 513, "name": "CC-PIB-A"},

    # === Remesas de trabajadores - Ingresos/Egresos de remesas de trabajadores en Colombia (5 series) ===
    {"suameca_id": 15363, "internal_id": 514, "name": "REMESAS-ING-M"},
    {"suameca_id": 15364, "internal_id": 515, "name": "REMESAS-ING-T"},
    {"suameca_id": 15365, "internal_id": 516, "name": "REMESAS-ING-A"},
    {"suameca_id": 17370, "internal_id": 517, "name": "REMESAS-EGR-T"},
    {"suameca_id": 17371, "internal_id": 518, "name": "REMESAS-EGR-A"},

    # === Remesas de trabajadores - Ingresos de remesas país Origen (35 series) ===
    {"suameca_id": 17377, "internal_id": 519, "name": "REM-ORIG-ALEMANIA"},
    {"suameca_id": 17378, "internal_id": 520, "name": "REM-ORIG-ARGENTIN"},
    {"suameca_id": 17379, "internal_id": 521, "name": "REM-ORIG-ARUBA"},
    {"suameca_id": 17380, "internal_id": 522, "name": "REM-ORIG-AUSTRALI"},
    {"suameca_id": 17381, "internal_id": 523, "name": "REM-ORIG-BOLIVIA"},
    {"suameca_id": 17382, "internal_id": 524, "name": "REM-ORIG-BRASIL"},
    {"suameca_id": 17383, "internal_id": 525, "name": "REM-ORIG-BELGICA"},
    {"suameca_id": 17384, "internal_id": 526, "name": "REM-ORIG-CANADA"},
    {"suameca_id": 17385, "internal_id": 527, "name": "REM-ORIG-CHILE"},
    {"suameca_id": 17386, "internal_id": 528, "name": "REM-ORIG-CHINA"},
    {"suameca_id": 17387, "internal_id": 529, "name": "REM-ORIG-COSTARI"},
    {"suameca_id": 17388, "internal_id": 530, "name": "REM-ORIG-CURAZAO"},
    {"suameca_id": 17389, "internal_id": 531, "name": "REM-ORIG-ECUADOR"},
    {"suameca_id": 17390, "internal_id": 532, "name": "REM-ORIG-EMIRATOS"},
    {"suameca_id": 17391, "internal_id": 533, "name": "REM-ORIG-ESPANA"},
    {"suameca_id": 17392, "internal_id": 534, "name": "REM-ORIG-ESTADOS"},
    {"suameca_id": 17393, "internal_id": 535, "name": "REM-ORIG-FRANCIA"},
    {"suameca_id": 17394, "internal_id": 536, "name": "REM-ORIG-GUATEMAL"},
    {"suameca_id": 17395, "internal_id": 537, "name": "REM-ORIG-HONDURAS"},
    {"suameca_id": 17396, "internal_id": 538, "name": "REM-ORIG-ISLASCA"},
    {"suameca_id": 17397, "internal_id": 539, "name": "REM-ORIG-ISRAEL"},
    {"suameca_id": 17398, "internal_id": 540, "name": "REM-ORIG-ITALIA"},
    {"suameca_id": 17399, "internal_id": 541, "name": "REM-ORIG-MEXICO"},
    {"suameca_id": 17400, "internal_id": 542, "name": "REM-ORIG-PANAMA"},
    {"suameca_id": 17401, "internal_id": 543, "name": "REM-ORIG-PAISESB"},
    {"suameca_id": 17402, "internal_id": 544, "name": "REM-ORIG-PERU"},
    {"suameca_id": 17403, "internal_id": 545, "name": "REM-ORIG-REINOUN"},
    {"suameca_id": 17404, "internal_id": 546, "name": "REM-ORIG-REPUBLIC"},
    {"suameca_id": 17405, "internal_id": 547, "name": "REM-ORIG-SUECIA"},
    {"suameca_id": 17406, "internal_id": 548, "name": "REM-ORIG-SUIZA"},
    {"suameca_id": 17407, "internal_id": 549, "name": "REM-ORIG-TRINIDAD"},
    {"suameca_id": 17408, "internal_id": 550, "name": "REM-ORIG-VENEZUEL"},
    {"suameca_id": 17409, "internal_id": 551, "name": "REM-ORIG-SINDISC"},
    {"suameca_id": 17410, "internal_id": 552, "name": "REM-ORIG-RESTOPA"},
    {"suameca_id": 17411, "internal_id": 553, "name": "REM-ORIG-TOTALPA"},

    # === Remesas de trabajadores - Egresos de remesas país Destino (32 series) ===
    {"suameca_id": 17412, "internal_id": 554, "name": "REM-DEST-ALEMANIA"},
    {"suameca_id": 17413, "internal_id": 555, "name": "REM-DEST-ARGENTIN"},
    {"suameca_id": 17414, "internal_id": 556, "name": "REM-DEST-ARUBA"},
    {"suameca_id": 17415, "internal_id": 557, "name": "REM-DEST-AUSTRALI"},
    {"suameca_id": 17416, "internal_id": 558, "name": "REM-DEST-BOLIVIA"},
    {"suameca_id": 17417, "internal_id": 559, "name": "REM-DEST-BRASIL"},
    {"suameca_id": 17418, "internal_id": 560, "name": "REM-DEST-CANADA"},
    {"suameca_id": 17419, "internal_id": 561, "name": "REM-DEST-CHILE"},
    {"suameca_id": 17420, "internal_id": 562, "name": "REM-DEST-COSTARI"},
    {"suameca_id": 17421, "internal_id": 563, "name": "REM-DEST-ECUADOR"},
    {"suameca_id": 17422, "internal_id": 564, "name": "REM-DEST-ESPANA"},
    {"suameca_id": 17423, "internal_id": 565, "name": "REM-DEST-ESTADOS"},
    {"suameca_id": 17424, "internal_id": 566, "name": "REM-DEST-FRANCIA"},
    {"suameca_id": 17425, "internal_id": 567, "name": "REM-DEST-GUATEMAL"},
    {"suameca_id": 17426, "internal_id": 568, "name": "REM-DEST-HONDURAS"},
    {"suameca_id": 17427, "internal_id": 569, "name": "REM-DEST-ITALIA"},
    {"suameca_id": 17428, "internal_id": 570, "name": "REM-DEST-LIBANO"},
    {"suameca_id": 17429, "internal_id": 571, "name": "REM-DEST-MALASIA"},
    {"suameca_id": 17430, "internal_id": 572, "name": "REM-DEST-MEXICO"},
    {"suameca_id": 17431, "internal_id": 573, "name": "REM-DEST-NICARAGU"},
    {"suameca_id": 17432, "internal_id": 574, "name": "REM-DEST-NIGERIA"},
    {"suameca_id": 17433, "internal_id": 575, "name": "REM-DEST-PANAMA"},
    {"suameca_id": 17434, "internal_id": 576, "name": "REM-DEST-PARAGUAY"},
    {"suameca_id": 17435, "internal_id": 577, "name": "REM-DEST-PAISESB"},
    {"suameca_id": 17436, "internal_id": 578, "name": "REM-DEST-PERU"},
    {"suameca_id": 17437, "internal_id": 579, "name": "REM-DEST-REINOUN"},
    {"suameca_id": 17438, "internal_id": 580, "name": "REM-DEST-REPUBLIC"},
    {"suameca_id": 17439, "internal_id": 581, "name": "REM-DEST-SUIZA"},
    {"suameca_id": 17440, "internal_id": 582, "name": "REM-DEST-URUGUAY"},
    {"suameca_id": 17441, "internal_id": 583, "name": "REM-DEST-VENEZUEL"},
    {"suameca_id": 17442, "internal_id": 584, "name": "REM-DEST-OTROSPA"},
    {"suameca_id": 17443, "internal_id": 585, "name": "REM-DEST-TOTALPA"},

    # === Remesas de trabajadores - Distribución de los ingresos de remesas por departamentos (33 series) ===
    {"suameca_id": 17449, "internal_id": 586, "name": "REM-DEPT-AMAZONAS"},
    {"suameca_id": 17450, "internal_id": 587, "name": "REM-DEPT-ANTIOQUIA"},
    {"suameca_id": 17451, "internal_id": 588, "name": "REM-DEPT-ARAUCA"},
    {"suameca_id": 17452, "internal_id": 589, "name": "REM-DEPT-ATLANTICO"},
    {"suameca_id": 17453, "internal_id": 590, "name": "REM-DEPT-BOLIVAR"},
    {"suameca_id": 17454, "internal_id": 591, "name": "REM-DEPT-BOYACA"},
    {"suameca_id": 17455, "internal_id": 592, "name": "REM-DEPT-CALDAS"},
    {"suameca_id": 17456, "internal_id": 593, "name": "REM-DEPT-CAQUETA"},
    {"suameca_id": 17457, "internal_id": 594, "name": "REM-DEPT-CASANARE"},
    {"suameca_id": 17458, "internal_id": 595, "name": "REM-DEPT-CAUCA"},
    {"suameca_id": 17459, "internal_id": 596, "name": "REM-DEPT-CESAR"},
    {"suameca_id": 17460, "internal_id": 597, "name": "REM-DEPT-CHOCO"},
    {"suameca_id": 17461, "internal_id": 598, "name": "REM-DEPT-CUNDINAMAR"},
    {"suameca_id": 17462, "internal_id": 599, "name": "REM-DEPT-CORDOBA"},
    {"suameca_id": 17463, "internal_id": 600, "name": "REM-DEPT-GUAINIA"},
    {"suameca_id": 17464, "internal_id": 601, "name": "REM-DEPT-GUAVIARE"},
    {"suameca_id": 17465, "internal_id": 602, "name": "REM-DEPT-HUILA"},
    {"suameca_id": 17466, "internal_id": 603, "name": "REM-DEPT-LAGUAJIRA"},
    {"suameca_id": 17467, "internal_id": 604, "name": "REM-DEPT-MAGDALENA"},
    {"suameca_id": 17468, "internal_id": 605, "name": "REM-DEPT-META"},
    {"suameca_id": 17469, "internal_id": 606, "name": "REM-DEPT-NARINO"},
    {"suameca_id": 17470, "internal_id": 607, "name": "REM-DEPT-NORTESANT"},
    {"suameca_id": 17471, "internal_id": 608, "name": "REM-DEPT-PUTUMAYO"},
    {"suameca_id": 17472, "internal_id": 609, "name": "REM-DEPT-QUINDIO"},
    {"suameca_id": 17473, "internal_id": 610, "name": "REM-DEPT-RISARALDA"},
    {"suameca_id": 17474, "internal_id": 611, "name": "REM-DEPT-SANANDRES"},
    {"suameca_id": 17475, "internal_id": 612, "name": "REM-DEPT-SANTANDER"},
    {"suameca_id": 17476, "internal_id": 613, "name": "REM-DEPT-SUCRE"},
    {"suameca_id": 17477, "internal_id": 614, "name": "REM-DEPT-TOLIMA"},
    {"suameca_id": 17478, "internal_id": 615, "name": "REM-DEPT-VALLE"},
    {"suameca_id": 17479, "internal_id": 616, "name": "REM-DEPT-VAUPES"},
    {"suameca_id": 17480, "internal_id": 617, "name": "REM-DEPT-VICHADA"},
    {"suameca_id": 17481, "internal_id": 618, "name": "REM-DEPT-SINDISCRI"},

    # === Remesas de trabajadores - Ingresos de remesas por modalidad de pago (2 series) ===
    {"suameca_id": 17447, "internal_id": 619, "name": "REM-ABONO-A"},
    {"suameca_id": 17448, "internal_id": 620, "name": "REM-VENTANILLA-A"},

    # === Deuda externa (pública y privada) mensual (4 series) ===
    {"suameca_id": 15329, "internal_id": 621, "name": "DEUDA-EXT-PIB"},
    {"suameca_id": 15330, "internal_id": 622, "name": "DEUDA-EXT-TOTAL"},
    {"suameca_id": 15331, "internal_id": 623, "name": "DEUDA-EXT-PUB"},
    {"suameca_id": 15332, "internal_id": 624, "name": "DEUDA-EXT-PRIV"},

    # === Índice de la tasa de cambio real (ITCR) (6 series) ===
    {"suameca_id":   232, "internal_id": 625, "name": "ITCR-IPP-NT"},
    {"suameca_id":   233, "internal_id": 626, "name": "ITCR-IPC-NT"},
    {"suameca_id":   234, "internal_id": 627, "name": "ITCR-IPP-T"},
    {"suameca_id":   235, "internal_id": 628, "name": "ITCR-IPC-T"},
    {"suameca_id":   236, "internal_id": 629, "name": "ITCR-C"},
    {"suameca_id":   237, "internal_id": 630, "name": "ITCR-FMI"},

    # === Índice de la tasa de cambio real (ITCR) - Índices bilaterales (22 series) ===
    {"suameca_id":   211, "internal_id": 631, "name": "ITCR-BI-ALEMAN"},
    {"suameca_id":   212, "internal_id": 632, "name": "ITCR-BI-ARGENT"},
    {"suameca_id":   213, "internal_id": 633, "name": "ITCR-BI-BRASIL"},
    {"suameca_id":   214, "internal_id": 634, "name": "ITCR-BI-BELGIC"},
    {"suameca_id":   215, "internal_id": 635, "name": "ITCR-BI-CANADA"},
    {"suameca_id":   216, "internal_id": 636, "name": "ITCR-BI-CHILE"},
    {"suameca_id":   217, "internal_id": 637, "name": "ITCR-BI-ECUADO"},
    {"suameca_id":   218, "internal_id": 638, "name": "ITCR-BI-ESPANA"},
    {"suameca_id":   219, "internal_id": 639, "name": "ITCR-BI-ESTADO"},
    {"suameca_id":   220, "internal_id": 640, "name": "ITCR-BI-FRANCI"},
    {"suameca_id":   221, "internal_id": 641, "name": "ITCR-BI-HOLAND"},
    {"suameca_id":   223, "internal_id": 642, "name": "ITCR-BI-INGLAT"},
    {"suameca_id":   224, "internal_id": 643, "name": "ITCR-BI-ITALIA"},
    {"suameca_id":   225, "internal_id": 644, "name": "ITCR-BI-JAPON"},
    {"suameca_id":   226, "internal_id": 645, "name": "ITCR-BI-MEXICO"},
    {"suameca_id":   227, "internal_id": 646, "name": "ITCR-BI-PANAMA"},
    {"suameca_id":   228, "internal_id": 647, "name": "ITCR-BI-PERU"},
    {"suameca_id":   229, "internal_id": 648, "name": "ITCR-BI-SUECIA"},
    {"suameca_id":   230, "internal_id": 649, "name": "ITCR-BI-SUIZA"},
    {"suameca_id":   231, "internal_id": 650, "name": "ITCR-BI-VENEZU"},
    {"suameca_id":   310, "internal_id": 651, "name": "ITCR-BI-CHINA"},
    {"suameca_id":   311, "internal_id": 652, "name": "ITCR-BI-COREA"},

    # === Índice de términos de intercambio de bienes - Según índices de precios del productor (3 series) ===
    {"suameca_id": 17510, "internal_id": 653, "name": "TI-IPP"},
    {"suameca_id": 17511, "internal_id": 654, "name": "TI-EXP-IPP"},
    {"suameca_id": 17512, "internal_id": 655, "name": "TI-IMP-IPP"},

    # === Índice de términos de intercambio de bienes - Según índices encadenados de precios de exportación e importación (3 series) ===
    {"suameca_id": 15360, "internal_id": 656, "name": "TI-ENCAD"},
    {"suameca_id": 15361, "internal_id": 657, "name": "TI-ENCAD-15361"},
    {"suameca_id": 15362, "internal_id": 658, "name": "TI-ENCAD-15362"},

    # === Inversión directa - Inversión extranjera directa en Colombia (IED) (11 series) ===
    {"suameca_id": 15368, "internal_id": 659, "name": "IED-AGRO"},
    {"suameca_id": 15366, "internal_id": 660, "name": "IED-TOTAL-A"},
    {"suameca_id": 15373, "internal_id": 661, "name": "IED-COMER"},
    {"suameca_id": 15372, "internal_id": 662, "name": "IED-CONSTR"},
    {"suameca_id": 15371, "internal_id": 663, "name": "IED-ELEC"},
    {"suameca_id": 15370, "internal_id": 664, "name": "IED-IND"},
    {"suameca_id": 15369, "internal_id": 665, "name": "IED-MINAS"},
    {"suameca_id": 15377, "internal_id": 666, "name": "IED-PETRO"},
    {"suameca_id": 15376, "internal_id": 667, "name": "IED-COMUNAL"},
    {"suameca_id": 15375, "internal_id": 668, "name": "IED-FINAN"},
    {"suameca_id": 15374, "internal_id": 669, "name": "IED-TRANSP"},

    # === Inversión directa - Inversión directa de Colombia en el exterior (IDCE) (10 series) ===
    {"suameca_id": 15378, "internal_id": 670, "name": "IDCE-AGRO"},
    {"suameca_id": 15383, "internal_id": 671, "name": "IDCE-COMER"},
    {"suameca_id": 15382, "internal_id": 672, "name": "IDCE-CONSTR"},
    {"suameca_id": 15379, "internal_id": 673, "name": "IDCE-MINAS"},
    {"suameca_id": 15381, "internal_id": 674, "name": "IDCE-ELEC"},
    {"suameca_id": 15380, "internal_id": 675, "name": "IDCE-IND"},
    {"suameca_id": 15386, "internal_id": 676, "name": "IDCE-COMUNAL"},
    {"suameca_id": 15385, "internal_id": 677, "name": "IDCE-FINAN"},
    {"suameca_id": 15384, "internal_id": 678, "name": "IDCE-TRANSP"},
    {"suameca_id": 15367, "internal_id": 679, "name": "IDCE-TOTAL-A"},

    # === Posición de inversión internacional (3 series) ===
    {"suameca_id": 16600, "internal_id": 680, "name": "PII-NETA"},
    {"suameca_id": 16601, "internal_id": 681, "name": "PII-ACTIVOS"},
    {"suameca_id": 16602, "internal_id": 682, "name": "PII-PASIVOS"},

    # === Posición de liquidez internacional (PLI) (13 series) ===
    {"suameca_id": 16850, "internal_id": 683, "name": "PLI-16850"},
    {"suameca_id": 16851, "internal_id": 684, "name": "PLI-16851"},
    {"suameca_id": 16852, "internal_id": 685, "name": "PLI-16852"},
    {"suameca_id": 16853, "internal_id": 686, "name": "PLI-16853"},
    {"suameca_id": 16854, "internal_id": 687, "name": "PLI-16854"},
    {"suameca_id": 16855, "internal_id": 688, "name": "PLI-16855"},
    {"suameca_id": 16856, "internal_id": 689, "name": "PLI-16856"},
    {"suameca_id": 16857, "internal_id": 690, "name": "PLI-16857"},
    {"suameca_id": 16858, "internal_id": 691, "name": "PLI-16858"},
    {"suameca_id": 16859, "internal_id": 692, "name": "PLI-16859"},
    {"suameca_id": 16860, "internal_id": 693, "name": "PLI-16860"},
    {"suameca_id": 16861, "internal_id": 694, "name": "PLI-16861"},
    {"suameca_id": 16862, "internal_id": 695, "name": "PLI-16862"},

    # === Flujo de inversión extranjera de cartera en el mercado local (4 series) ===
    {"suameca_id": 17373, "internal_id": 696, "name": "INV-CART-LOCAL"},
    {"suameca_id": 17374, "internal_id": 697, "name": "INV-CART-CAPITAL"},
    {"suameca_id": 17375, "internal_id": 698, "name": "INV-CART-DEUDA"},
    {"suameca_id": 17376, "internal_id": 699, "name": "INV-CART-DEP"},

    # === Producto Interno Bruto (PIB) - Metodología 2015 - Total y por habitante a precios corrientes y constantes (12 series) ===
    {"suameca_id": 15304, "internal_id": 700, "name": "CREC-N-15-T"},
    {"suameca_id": 15303, "internal_id": 701, "name": "CREC-N-15-T-AE"},
    {"suameca_id": 15271, "internal_id": 702, "name": "CREC-R-15-T"},
    {"suameca_id": 15295, "internal_id": 703, "name": "CREC-R-15-T-AE"},
    {"suameca_id": 15153, "internal_id": 704, "name": "PIB-N-15-T"},
    {"suameca_id": 15151, "internal_id": 705, "name": "PIB-N-15-T-AE"},
    {"suameca_id": 15154, "internal_id": 706, "name": "PIB-R-15-T"},
    {"suameca_id": 15152, "internal_id": 707, "name": "PIB-R-15-T-AE"},
    {"suameca_id": 15291, "internal_id": 708, "name": "PIB-N-15-A"},
    {"suameca_id": 15292, "internal_id": 709, "name": "PIB-R-15-A"},
    {"suameca_id": 15294, "internal_id": 710, "name": "CREC-R-15-A"},
    {"suameca_id": 15302, "internal_id": 711, "name": "CREC-N-15-A"},

    # === Producto Interno Bruto (PIB) - Metodología 2015 - Grandes ramas de actividades económicas a precios corrientes y constantes trimestral (8 series) ===
    {"suameca_id": 15155, "internal_id": 712, "name": "PIB-CONS-N"},
    {"suameca_id": 15156, "internal_id": 713, "name": "PIB-CONS-R"},
    {"suameca_id": 15322, "internal_id": 714, "name": "PIB-EXP-N"},
    {"suameca_id": 15320, "internal_id": 715, "name": "PIB-EXP-R"},
    {"suameca_id": 15159, "internal_id": 716, "name": "PIB-FBK-N"},
    {"suameca_id": 15160, "internal_id": 717, "name": "PIB-FBK-R"},
    {"suameca_id": 15323, "internal_id": 718, "name": "PIB-IMP-N"},
    {"suameca_id": 15321, "internal_id": 719, "name": "PIB-IMP-R"},

    # === Producto Interno Bruto (PIB) - Metodología 2005 (4 series) ===
    {"suameca_id": 15296, "internal_id": 720, "name": "CREC-R-05-T-AE"},
    {"suameca_id": 15299, "internal_id": 721, "name": "PIB-R-05-T-AE"},
    {"suameca_id": 15305, "internal_id": 722, "name": "CREC-N-05-T-AE"},
    {"suameca_id": 15308, "internal_id": 723, "name": "PIB-N-05-T-AE"},

    # === Producto Interno Bruto (PIB) - Metodología 2000 (4 series) ===
    {"suameca_id": 15297, "internal_id": 724, "name": "CREC-R-00-T-AE"},
    {"suameca_id": 15300, "internal_id": 725, "name": "PIB-R-00-T-AE"},
    {"suameca_id": 15306, "internal_id": 726, "name": "CREC-N-00-T-AE"},
    {"suameca_id": 15309, "internal_id": 727, "name": "PIB-N-00-T-AE"},

    # === Producto Interno Bruto (PIB) - Metodología 1994 (4 series) ===
    {"suameca_id": 15298, "internal_id": 728, "name": "CREC-R-94-T-AE"},
    {"suameca_id": 15301, "internal_id": 729, "name": "PIB-R-94-T-AE"},
    {"suameca_id": 15307, "internal_id": 730, "name": "CREC-N-94-T-AE"},
    {"suameca_id": 15310, "internal_id": 731, "name": "PIB-N-94-T-AE"},

    # === Mercado laboral y población - Tasa de ocupación y desempleo (27 series) ===
    {"suameca_id": 15312, "internal_id": 732, "name": "DESEMPLEO"},
    {"suameca_id": 15313, "internal_id": 733, "name": "OCUPACION"},
    {"suameca_id":   900, "internal_id": 734, "name": "TGP"},
    {"suameca_id":   901, "internal_id": 735, "name": "TGP-H"},
    {"suameca_id":   902, "internal_id": 736, "name": "TGP-M"},
    {"suameca_id":   903, "internal_id": 737, "name": "TGP-EDUC0"},
    {"suameca_id":   904, "internal_id": 738, "name": "TGP-EDUC12"},
    {"suameca_id":   905, "internal_id": 739, "name": "TGP-EDUC15"},
    {"suameca_id":   906, "internal_id": 740, "name": "TGP-AGE-25"},
    {"suameca_id":   907, "internal_id": 741, "name": "TGP-AGE2645"},
    {"suameca_id":   908, "internal_id": 742, "name": "TGP-AGE4665"},
    {"suameca_id":   910, "internal_id": 743, "name": "TO-H"},
    {"suameca_id":   911, "internal_id": 744, "name": "TO-M"},
    {"suameca_id":   912, "internal_id": 745, "name": "TO-EDUC0"},
    {"suameca_id":   913, "internal_id": 746, "name": "TO-EDUC12"},
    {"suameca_id":   914, "internal_id": 747, "name": "TO-EDUC15"},
    {"suameca_id":   919, "internal_id": 748, "name": "TD-H"},
    {"suameca_id":   920, "internal_id": 749, "name": "TD-M"},
    {"suameca_id":   921, "internal_id": 750, "name": "TD-EDUC0"},
    {"suameca_id":   922, "internal_id": 751, "name": "TD-EDUC12"},
    {"suameca_id":   923, "internal_id": 752, "name": "TD-EDUC15"},
    {"suameca_id":   924, "internal_id": 753, "name": "TD-AGE-25"},
    {"suameca_id":   925, "internal_id": 754, "name": "TD-AGE2645"},
    {"suameca_id":   926, "internal_id": 755, "name": "TD-AGE4665"},
    {"suameca_id":   942, "internal_id": 756, "name": "TO-AGE-25"},
    {"suameca_id":   943, "internal_id": 757, "name": "TO-AGE2645"},
    {"suameca_id":   944, "internal_id": 758, "name": "TO-AGE4665"},

    # === Mercado laboral y población - Vacantes u ofertas de empleo (7 series) ===
    {"suameca_id": 16570, "internal_id": 759, "name": "VAC-MANIZA"},
    {"suameca_id": 16571, "internal_id": 760, "name": "VAC-CALI"},
    {"suameca_id": 16572, "internal_id": 761, "name": "VAC-BUCARA"},
    {"suameca_id": 16573, "internal_id": 762, "name": "VAC-MEDELL"},
    {"suameca_id": 16574, "internal_id": 763, "name": "VAC-BARRAN"},
    {"suameca_id": 16575, "internal_id": 764, "name": "VAC-PASTO"},
    {"suameca_id": 16576, "internal_id": 765, "name": "VAC-BOGOTA"},

    # === Mercado laboral y población - Salarios (3 series) ===
    {"suameca_id": 15416, "internal_id": 766, "name": "SAL-MIN-M"},
    {"suameca_id": 15417, "internal_id": 767, "name": "SAL-MIN-D"},
    {"suameca_id": 15418, "internal_id": 768, "name": "SAL-MIN-VAR"},

    # === Mercado laboral y población - Población (1 series) ===
    {"suameca_id": 16610, "internal_id": 769, "name": "POBLACION"},

    # === Cuentas financieras - Saldos y Flujos - Metodología 2008 - Saldos y flujos por sector y contraparte (26 series) ===
    {"suameca_id": 16810, "internal_id": 770, "name": "CF-SAL-NETO"},
    {"suameca_id": 16811, "internal_id": 771, "name": "CF-SAL-SNF"},
    {"suameca_id": 16812, "internal_id": 772, "name": "CF-SAL-SF"},
    {"suameca_id": 16813, "internal_id": 773, "name": "CF-SAL-GOB"},
    {"suameca_id": 16814, "internal_id": 774, "name": "CF-SAL-HOG"},
    {"suameca_id": 16815, "internal_id": 775, "name": "CF-SAL-ISFL"},
    {"suameca_id": 16816, "internal_id": 776, "name": "CF-FLU-NETO"},
    {"suameca_id": 16817, "internal_id": 777, "name": "CF-FLU-ORO"},
    {"suameca_id": 16818, "internal_id": 778, "name": "CF-FLU-DEP"},
    {"suameca_id": 16819, "internal_id": 779, "name": "CF-FLU-TIT"},
    {"suameca_id": 16820, "internal_id": 780, "name": "CF-FLU-PREST"},
    {"suameca_id": 16821, "internal_id": 781, "name": "CF-FLU-ACC"},
    {"suameca_id": 16822, "internal_id": 782, "name": "CF-FLU-SEG"},
    {"suameca_id": 16823, "internal_id": 783, "name": "CF-FLU-CXP"},
    {"suameca_id": 17522, "internal_id": 784, "name": "CF-FLU-SNF"},
    {"suameca_id": 17523, "internal_id": 785, "name": "CF-FLU-SF"},
    {"suameca_id": 17524, "internal_id": 786, "name": "CF-FLU-GOB"},
    {"suameca_id": 17525, "internal_id": 787, "name": "CF-FLU-HOG"},
    {"suameca_id": 17526, "internal_id": 788, "name": "CF-FLU-ISFL"},
    {"suameca_id": 17528, "internal_id": 789, "name": "CF-SAL-ORO"},
    {"suameca_id": 17529, "internal_id": 790, "name": "CF-SAL-DEP"},
    {"suameca_id": 17530, "internal_id": 791, "name": "CF-SAL-TIT"},
    {"suameca_id": 17531, "internal_id": 792, "name": "CF-SAL-PREST"},
    {"suameca_id": 17532, "internal_id": 793, "name": "CF-SAL-ACC"},
    {"suameca_id": 17533, "internal_id": 794, "name": "CF-SAL-SEG"},
    {"suameca_id": 17534, "internal_id": 795, "name": "CF-SAL-CXP"},

    # === Deuda pública - Bid Ask Spread (2 series) ===
    {"suameca_id": 16720, "internal_id": 796, "name": "BIDASK-TES-COP"},
    {"suameca_id": 16721, "internal_id": 797, "name": "BIDASK-TES-UVR"},

    # === Gobierno Nacional Central - Balance fiscal (7 series) ===
    {"suameca_id": 16722, "internal_id": 798, "name": "GNC-ING"},
    {"suameca_id": 15327, "internal_id": 799, "name": "BALANCE-GNC-PIB"},
    {"suameca_id": 16723, "internal_id": 800, "name": "GNC-GAST"},
    {"suameca_id": 16724, "internal_id": 801, "name": "GNC-INT"},
    {"suameca_id": 16725, "internal_id": 802, "name": "GNC-DEFICIT"},
    {"suameca_id": 16726, "internal_id": 803, "name": "GNC-FIN-INT"},
    {"suameca_id": 16727, "internal_id": 804, "name": "GNC-FIN-EXT"},

    # === Gobierno Nacional Central - Saldo de deuda total (1 series) ===
    {"suameca_id": 15328, "internal_id": 805, "name": "DEUDA-GNC-PIB"},

    # === Sector público no financiero (7 series) ===
    {"suameca_id": 16728, "internal_id": 806, "name": "SPNF-ING"},
    {"suameca_id": 16729, "internal_id": 807, "name": "SPNF-GAST"},
    {"suameca_id": 16730, "internal_id": 808, "name": "SPNF-INT"},
    {"suameca_id": 16731, "internal_id": 809, "name": "SPNF-DEFICIT"},
    {"suameca_id": 16732, "internal_id": 810, "name": "SPNF-FIN-INT"},
    {"suameca_id": 16733, "internal_id": 811, "name": "SPNF-FIN-EXT"},
    {"suameca_id": 16734, "internal_id": 812, "name": "SPNF-EMPUB"},

    # === Gobiernos territoriales - Gasto sectorial (18 series) ===
    {"suameca_id": 16735, "internal_id": 813, "name": "GDEP-ING-CERV"},
    {"suameca_id": 16736, "internal_id": 814, "name": "GDEP-ING-CIG"},
    {"suameca_id": 16737, "internal_id": 815, "name": "GDEP-ING-LIC"},
    {"suameca_id": 16738, "internal_id": 816, "name": "GDEP-ING-TRIB-OTR"},
    {"suameca_id": 16739, "internal_id": 817, "name": "GDEP-ING-TRIB"},
    {"suameca_id": 16740, "internal_id": 818, "name": "GDEP-ING-NOTRIB"},
    {"suameca_id": 16741, "internal_id": 819, "name": "GDEP-ING-TRANSF"},
    {"suameca_id": 16742, "internal_id": 820, "name": "GDEP-ING-CAP"},
    {"suameca_id": 16743, "internal_id": 821, "name": "GDEP-ING-TOT"},
    {"suameca_id": 16744, "internal_id": 822, "name": "GDEP-GAST-FUNC"},
    {"suameca_id": 16745, "internal_id": 823, "name": "GDEP-GAST-INT"},
    {"suameca_id": 16746, "internal_id": 824, "name": "GDEP-GAST-TRANSF"},
    {"suameca_id": 16747, "internal_id": 825, "name": "GDEP-GAST-CORR"},
    {"suameca_id": 16748, "internal_id": 826, "name": "GDEP-GAST-CAP"},
    {"suameca_id": 16749, "internal_id": 827, "name": "GDEP-GAST-TOT"},
    {"suameca_id": 16750, "internal_id": 828, "name": "GDEP-PREST-NETO"},
    {"suameca_id": 16751, "internal_id": 829, "name": "GDEP-AJ-TRANSF"},
    {"suameca_id": 16752, "internal_id": 830, "name": "GDEP-BALANCE"},

    # === Subastas de opciones (22 series) ===
    {"suameca_id": 16650, "internal_id": 831, "name": "SUB-INTERV-DISC"},
    {"suameca_id": 16651, "internal_id": 832, "name": "SUB-COMPRA-DIR"},
    {"suameca_id": 16652, "internal_id": 833, "name": "SUB-PUT-VOL"},
    {"suameca_id": 16653, "internal_id": 834, "name": "SUB-CALL-VOL-RES"},
    {"suameca_id": 16654, "internal_id": 835, "name": "SUB-PUT-ACUM"},
    {"suameca_id": 16655, "internal_id": 836, "name": "SUB-CALL-DESAC"},
    {"suameca_id": 16668, "internal_id": 837, "name": "SUB-PUT-ACUM-CUPO"},
    {"suameca_id": 16669, "internal_id": 838, "name": "SUB-PUT-ACUM-PRES"},
    {"suameca_id": 16670, "internal_id": 839, "name": "SUB-PUT-ACUM-APROB"},
    {"suameca_id": 16671, "internal_id": 840, "name": "SUB-PUT-ACUM-PRIMA"},
    {"suameca_id": 16672, "internal_id": 841, "name": "SUB-PUT-VOL-CUPO"},
    {"suameca_id": 16673, "internal_id": 842, "name": "SUB-PUT-VOL-PRES"},
    {"suameca_id": 16674, "internal_id": 843, "name": "SUB-PUT-VOL-APROB"},
    {"suameca_id": 16675, "internal_id": 844, "name": "SUB-PUT-VOL-PRIMA"},
    {"suameca_id": 16676, "internal_id": 845, "name": "SUB-CALL-DES-CUPO"},
    {"suameca_id": 16677, "internal_id": 846, "name": "SUB-CALL-DES-PRES"},
    {"suameca_id": 16678, "internal_id": 847, "name": "SUB-CALL-DES-APROB"},
    {"suameca_id": 16679, "internal_id": 848, "name": "SUB-CALL-DES-PRIMA"},
    {"suameca_id": 16680, "internal_id": 849, "name": "SUB-CALL-VOL-CUPO"},
    {"suameca_id": 16681, "internal_id": 850, "name": "SUB-CALL-VOL-PRES"},
    {"suameca_id": 16682, "internal_id": 851, "name": "SUB-CALL-VOL-APROB"},
    {"suameca_id": 16683, "internal_id": 852, "name": "SUB-CALL-VOL-PRIMA"},

    # === Pulso económico regional (14 series) ===
    {"suameca_id": 16630, "internal_id": 853, "name": "PER-COMERCIO"},
    {"suameca_id": 16631, "internal_id": 854, "name": "PER-INDUSTRIA"},
    {"suameca_id": 16632, "internal_id": 855, "name": "PER-TRANSPORTE"},
    {"suameca_id": 16633, "internal_id": 856, "name": "PER-AGROPECUARIO"},
    {"suameca_id": 16634, "internal_id": 857, "name": "PER-FINANCIERO"},
    {"suameca_id": 16635, "internal_id": 858, "name": "PER-VIVIENDA"},
    {"suameca_id": 16636, "internal_id": 859, "name": "PER-NACIONAL"},
    {"suameca_id": 16637, "internal_id": 860, "name": "PER-ANTIOQUIA"},
    {"suameca_id": 16638, "internal_id": 861, "name": "PER-SUROCCIDENTE"},
    {"suameca_id": 16639, "internal_id": 862, "name": "PER-CARIBE"},
    {"suameca_id": 16640, "internal_id": 863, "name": "PER-NORORIENTE"},
    {"suameca_id": 16641, "internal_id": 864, "name": "PER-CENTRAL-CAFE"},
    {"suameca_id": 16642, "internal_id": 865, "name": "PER-LLANOS-ORIEN"},
    {"suameca_id": 16643, "internal_id": 866, "name": "PER-BOGOTA"},
]

# Total: 858 series (25 legacy + 833 new)

connection = SupabaseConnection()
connection.sign_in_as_collector()

success = 0
failures = 0
skipped = 0

# Process in batches of 20 series per API call
BATCH_SIZE = 20

for i in range(0, len(series), BATCH_SIZE):
    batch = series[i:i + BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1
    total_batches = (len(series) + BATCH_SIZE - 1) // BATCH_SIZE
    print("\n--- Batch {}/{} (series {}-{}) ---".format(batch_num, total_batches, i + 1, min(i + BATCH_SIZE, len(series))))

    try:
        frames = collector.get_batch_series_data(batch)

        for serie in batch:
            internal_id = serie['internal_id']
            df = frames.get(internal_id)

            if df is None or len(df) == 0:
                skipped += 1
                continue

            try:
                last = connection.get_last_by(
                    table_name='banrep_series_value_v2',
                    column_name='fecha',
                    filter_by=('id_serie', internal_id)
                )

                if len(last) > 0:
                    filter_date = last[0]['fecha']
                    filtering = df[df['fecha'] > filter_date].copy(deep=True)
                else:
                    filtering = df.copy(deep=True)

                if len(filtering) > 0:
                    print("New data for {} (id {}): {} rows".format(serie['name'], internal_id, len(filtering)))
                    connection.insert_dataframe(frame=filtering, table_name='banrep_series_value_v2')
                    success += 1
                else:
                    success += 1

            except Exception as e:
                failures += 1
                print("Failed {} (id {}): {}".format(serie['name'], internal_id, str(e)))

    except Exception as e:
        failures += len(batch)
        print("Batch failed: {}".format(str(e)))

print("\nCollection complete: {} successful, {} failures, {} skipped out of {} total".format(success, failures, skipped, len(series)))
