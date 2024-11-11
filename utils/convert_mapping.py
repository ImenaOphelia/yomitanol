# Convert mapping to tag bank format
verbs = {
    "acertar": "17",
    "adquirir": "18",
    "agradecer": "19",
    "andar": "20",
    "asir": "21",
    "bendecir": "22",
    "caber": "23",
    "caer": "24",
    "ceñir": "25",
    "conducir": "26",
    "construir": "27",
    "contar": "28",
    "dar": "29",
    "decir": "30",
    "discernir": "31",
    "dormir": "32",
    "entender": "33",
    "erguir": "34",
    "errar": "35",
    "estar": "36",
    "haber": "37",
    "hacer": "38",
    "huir": "39",
    "ir": "40",
    "jugar": "41",
    "leer": "42",
    "lucir": "43",
    "mover": "44",
    "mullir": "45",
    "oír": "46",
    "oler": "47",
    "pedir": "48",
    "poder": "49",
    "poner": "50",
    "predecir": "51",
    "pudrir": "52",
    "podrir": "52",
    "querer": "53",
    "reír": "54",
    "roer": "55",
    "saber": "56",
    "salir": "57",
    "sentir": "58",
    "ser": "59",
    "sonreír": "60",
    "tañer": "61",
    "tener": "62",
    "traer": "63",
    "valer": "64",
    "venir": "65",
    "ver": "66",
    "yacer": "67"
}

category = "modeloIrregular"

converted_list = [
    [f"{value}", f"{category}", 0, f"Conjugación como {verb}", 0]
    for verb, value in verbs.items()
]

for item in converted_list:
    print(item)
