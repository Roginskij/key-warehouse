"""The first characteristics list (before the admin edits it). Used by the migration
that creates the tables, and by the tests to restore a clean database.

Labels in 7 languages; uk and en are required for fields the admin adds later.
"""

import json
import uuid

from sqlalchemy import Connection, insert

from app.modules.catalog.models import AttributeDef, AttributeOption

SEED = json.loads(
    r"""[
 {
  "kind": "blank",
  "key": "blade_shape",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Тип леза",
   "en": "Blade type",
   "pl": "Rodzaj ostrza",
   "de": "Bartart",
   "fr": "Type de lame",
   "es": "Tipo de hoja",
   "it": "Tipo di lama"
  },
  "options": [
   {
    "key": "standard",
    "labels": {
     "uk": "звичайне",
     "en": "standard",
     "pl": "zwykłe",
     "de": "Standard",
     "fr": "standard",
     "es": "estándar",
     "it": "standard"
    }
   },
   {
    "key": "laser",
    "labels": {
     "uk": "лазерне (high security)",
     "en": "laser (high security)",
     "pl": "laserowe (high security)",
     "de": "Laser (Hochsicherheit)",
     "fr": "laser (haute sécurité)",
     "es": "láser (alta seguridad)",
     "it": "laser (alta sicurezza)"
    }
   },
   {
    "key": "dimple",
    "labels": {
     "uk": "точкове (dimple)",
     "en": "dimple",
     "pl": "nawiercane (dimple)",
     "de": "Bohrmulden (Dimple)",
     "fr": "à points (dimple)",
     "es": "de puntos (dimple)",
     "it": "a punti (dimple)"
    }
   },
   {
    "key": "tubular",
    "labels": {
     "uk": "трубчасте",
     "en": "tubular",
     "pl": "rurkowe",
     "de": "Röhrchen",
     "fr": "tubulaire",
     "es": "tubular",
     "it": "tubolare"
    }
   },
   {
    "key": "flat",
    "labels": {
     "uk": "плоске",
     "en": "flat",
     "pl": "płaskie",
     "de": "Flach",
     "fr": "plate",
     "es": "plana",
     "it": "piatta"
    }
   }
  ]
 },
 {
  "kind": "blank",
  "key": "head",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Головка",
   "en": "Head",
   "pl": "Główka",
   "de": "Kopf",
   "fr": "Tête",
   "es": "Cabeza",
   "it": "Testa"
  },
  "options": [
   {
    "key": "metal",
    "labels": {
     "uk": "металева",
     "en": "metal",
     "pl": "metalowa",
     "de": "Metall",
     "fr": "métal",
     "es": "metálica",
     "it": "metallo"
    }
   },
   {
    "key": "plastic",
    "labels": {
     "uk": "пластикова",
     "en": "plastic",
     "pl": "plastikowa",
     "de": "Kunststoff",
     "fr": "plastique",
     "es": "de plástico",
     "it": "plastica"
    }
   },
   {
    "key": "none",
    "labels": {
     "uk": "немає",
     "en": "none",
     "pl": "brak",
     "de": "keine",
     "fr": "aucune",
     "es": "ninguna",
     "it": "nessuna"
    }
   }
  ]
 },
 {
  "kind": "blank",
  "key": "material",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Матеріал",
   "en": "Material",
   "pl": "Materiał",
   "de": "Material",
   "fr": "Matériau",
   "es": "Material",
   "it": "Materiale"
  },
  "options": [
   {
    "key": "brass",
    "labels": {
     "uk": "латунь",
     "en": "brass",
     "pl": "mosiądz",
     "de": "Messing",
     "fr": "laiton",
     "es": "latón",
     "it": "ottone"
    }
   },
   {
    "key": "nickel_silver",
    "labels": {
     "uk": "нейзильбер",
     "en": "nickel silver",
     "pl": "nowe srebro",
     "de": "Neusilber",
     "fr": "maillechort",
     "es": "alpaca",
     "it": "alpacca"
    }
   },
   {
    "key": "steel",
    "labels": {
     "uk": "сталь",
     "en": "steel",
     "pl": "stal",
     "de": "Stahl",
     "fr": "acier",
     "es": "acero",
     "it": "acciaio"
    }
   }
  ]
 },
 {
  "kind": "blank",
  "key": "chip_slot",
  "type": "bool",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Місце під чип",
   "en": "Chip slot",
   "pl": "Miejsce na chip",
   "de": "Chipfach",
   "fr": "Logement de puce",
   "es": "Hueco para chip",
   "it": "Alloggio chip"
  },
  "options": []
 },
 {
  "kind": "car_key",
  "key": "buttons",
  "type": "number",
  "min": 0,
  "max": 8,
  "labels": {
   "uk": "Кнопок",
   "en": "Buttons",
   "pl": "Przycisków",
   "de": "Tasten",
   "fr": "Boutons",
   "es": "Botones",
   "it": "Tasti"
  },
  "options": []
 },
 {
  "kind": "car_key",
  "key": "blade",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Лезо",
   "en": "Blade",
   "pl": "Ostrze",
   "de": "Bart",
   "fr": "Lame",
   "es": "Hoja",
   "it": "Lama"
  },
  "options": [
   {
    "key": "fixed",
    "labels": {
     "uk": "звичайне",
     "en": "fixed",
     "pl": "stałe",
     "de": "fest",
     "fr": "fixe",
     "es": "fija",
     "it": "fissa"
    }
   },
   {
    "key": "flip",
    "labels": {
     "uk": "викидне",
     "en": "flip",
     "pl": "składane",
     "de": "Klapp",
     "fr": "rétractable",
     "es": "plegable",
     "it": "a scatto"
    }
   },
   {
    "key": "emergency",
    "labels": {
     "uk": "аварійне",
     "en": "emergency",
     "pl": "awaryjne",
     "de": "Notschlüssel",
     "fr": "de secours",
     "es": "de emergencia",
     "it": "d’emergenza"
    }
   },
   {
    "key": "none",
    "labels": {
     "uk": "немає",
     "en": "none",
     "pl": "brak",
     "de": "keine",
     "fr": "aucune",
     "es": "ninguna",
     "it": "nessuna"
    }
   }
  ]
 },
 {
  "kind": "car_key",
  "key": "blade_shape",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Тип леза",
   "en": "Blade type",
   "pl": "Rodzaj ostrza",
   "de": "Bartart",
   "fr": "Type de lame",
   "es": "Tipo de hoja",
   "it": "Tipo di lama"
  },
  "options": [
   {
    "key": "standard",
    "labels": {
     "uk": "звичайне",
     "en": "standard",
     "pl": "zwykłe",
     "de": "Standard",
     "fr": "standard",
     "es": "estándar",
     "it": "standard"
    }
   },
   {
    "key": "laser",
    "labels": {
     "uk": "лазерне (high security)",
     "en": "laser (high security)",
     "pl": "laserowe (high security)",
     "de": "Laser (Hochsicherheit)",
     "fr": "laser (haute sécurité)",
     "es": "láser (alta seguridad)",
     "it": "laser (alta sicurezza)"
    }
   },
   {
    "key": "dimple",
    "labels": {
     "uk": "точкове (dimple)",
     "en": "dimple",
     "pl": "nawiercane (dimple)",
     "de": "Bohrmulden (Dimple)",
     "fr": "à points (dimple)",
     "es": "de puntos (dimple)",
     "it": "a punti (dimple)"
    }
   },
   {
    "key": "tubular",
    "labels": {
     "uk": "трубчасте",
     "en": "tubular",
     "pl": "rurkowe",
     "de": "Röhrchen",
     "fr": "tubulaire",
     "es": "tubular",
     "it": "tubolare"
    }
   },
   {
    "key": "flat",
    "labels": {
     "uk": "плоске",
     "en": "flat",
     "pl": "płaskie",
     "de": "Flach",
     "fr": "plate",
     "es": "plana",
     "it": "piatta"
    }
   }
  ]
 },
 {
  "kind": "car_key",
  "key": "keyless",
  "type": "bool",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Безключовий доступ",
   "en": "Keyless entry",
   "pl": "Dostęp bezkluczykowy",
   "de": "Keyless",
   "fr": "Mains libres",
   "es": "Acceso sin llave",
   "it": "Accesso senza chiave"
  },
  "options": []
 },
 {
  "kind": "car_key",
  "key": "battery",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Батарейка",
   "en": "Battery",
   "pl": "Bateria",
   "de": "Batterie",
   "fr": "Pile",
   "es": "Pila",
   "it": "Batteria"
  },
  "options": [
   {
    "key": "CR2032",
    "labels": {
     "uk": "CR2032",
     "en": "CR2032",
     "pl": "CR2032",
     "de": "CR2032",
     "fr": "CR2032",
     "es": "CR2032",
     "it": "CR2032"
    }
   },
   {
    "key": "CR2025",
    "labels": {
     "uk": "CR2025",
     "en": "CR2025",
     "pl": "CR2025",
     "de": "CR2025",
     "fr": "CR2025",
     "es": "CR2025",
     "it": "CR2025"
    }
   },
   {
    "key": "CR2016",
    "labels": {
     "uk": "CR2016",
     "en": "CR2016",
     "pl": "CR2016",
     "de": "CR2016",
     "fr": "CR2016",
     "es": "CR2016",
     "it": "CR2016"
    }
   },
   {
    "key": "CR1632",
    "labels": {
     "uk": "CR1632",
     "en": "CR1632",
     "pl": "CR1632",
     "de": "CR1632",
     "fr": "CR1632",
     "es": "CR1632",
     "it": "CR1632"
    }
   },
   {
    "key": "CR1620",
    "labels": {
     "uk": "CR1620",
     "en": "CR1620",
     "pl": "CR1620",
     "de": "CR1620",
     "fr": "CR1620",
     "es": "CR1620",
     "it": "CR1620"
    }
   },
   {
    "key": "CR1616",
    "labels": {
     "uk": "CR1616",
     "en": "CR1616",
     "pl": "CR1616",
     "de": "CR1616",
     "fr": "CR1616",
     "es": "CR1616",
     "it": "CR1616"
    }
   },
   {
    "key": "CR2450",
    "labels": {
     "uk": "CR2450",
     "en": "CR2450",
     "pl": "CR2450",
     "de": "CR2450",
     "fr": "CR2450",
     "es": "CR2450",
     "it": "CR2450"
    }
   },
   {
    "key": "CR2430",
    "labels": {
     "uk": "CR2430",
     "en": "CR2430",
     "pl": "CR2430",
     "de": "CR2430",
     "fr": "CR2430",
     "es": "CR2430",
     "it": "CR2430"
    }
   },
   {
    "key": "CR1220",
    "labels": {
     "uk": "CR1220",
     "en": "CR1220",
     "pl": "CR1220",
     "de": "CR1220",
     "fr": "CR1220",
     "es": "CR1220",
     "it": "CR1220"
    }
   },
   {
    "key": "LR44",
    "labels": {
     "uk": "LR44",
     "en": "LR44",
     "pl": "LR44",
     "de": "LR44",
     "fr": "LR44",
     "es": "LR44",
     "it": "LR44"
    }
   },
   {
    "key": "other",
    "labels": {
     "uk": "інша",
     "en": "other",
     "pl": "inna",
     "de": "andere",
     "fr": "autre",
     "es": "otra",
     "it": "altra"
    }
   }
  ]
 },
 {
  "kind": "remote",
  "key": "buttons",
  "type": "number",
  "min": 0,
  "max": 8,
  "labels": {
   "uk": "Кнопок",
   "en": "Buttons",
   "pl": "Przycisków",
   "de": "Tasten",
   "fr": "Boutons",
   "es": "Botones",
   "it": "Tasti"
  },
  "options": []
 },
 {
  "kind": "remote",
  "key": "keyless",
  "type": "bool",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Безключовий доступ",
   "en": "Keyless entry",
   "pl": "Dostęp bezkluczykowy",
   "de": "Keyless",
   "fr": "Mains libres",
   "es": "Acceso sin llave",
   "it": "Accesso senza chiave"
  },
  "options": []
 },
 {
  "kind": "remote",
  "key": "battery",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Батарейка",
   "en": "Battery",
   "pl": "Bateria",
   "de": "Batterie",
   "fr": "Pile",
   "es": "Pila",
   "it": "Batteria"
  },
  "options": [
   {
    "key": "CR2032",
    "labels": {
     "uk": "CR2032",
     "en": "CR2032",
     "pl": "CR2032",
     "de": "CR2032",
     "fr": "CR2032",
     "es": "CR2032",
     "it": "CR2032"
    }
   },
   {
    "key": "CR2025",
    "labels": {
     "uk": "CR2025",
     "en": "CR2025",
     "pl": "CR2025",
     "de": "CR2025",
     "fr": "CR2025",
     "es": "CR2025",
     "it": "CR2025"
    }
   },
   {
    "key": "CR2016",
    "labels": {
     "uk": "CR2016",
     "en": "CR2016",
     "pl": "CR2016",
     "de": "CR2016",
     "fr": "CR2016",
     "es": "CR2016",
     "it": "CR2016"
    }
   },
   {
    "key": "CR1632",
    "labels": {
     "uk": "CR1632",
     "en": "CR1632",
     "pl": "CR1632",
     "de": "CR1632",
     "fr": "CR1632",
     "es": "CR1632",
     "it": "CR1632"
    }
   },
   {
    "key": "CR1620",
    "labels": {
     "uk": "CR1620",
     "en": "CR1620",
     "pl": "CR1620",
     "de": "CR1620",
     "fr": "CR1620",
     "es": "CR1620",
     "it": "CR1620"
    }
   },
   {
    "key": "CR1616",
    "labels": {
     "uk": "CR1616",
     "en": "CR1616",
     "pl": "CR1616",
     "de": "CR1616",
     "fr": "CR1616",
     "es": "CR1616",
     "it": "CR1616"
    }
   },
   {
    "key": "CR2450",
    "labels": {
     "uk": "CR2450",
     "en": "CR2450",
     "pl": "CR2450",
     "de": "CR2450",
     "fr": "CR2450",
     "es": "CR2450",
     "it": "CR2450"
    }
   },
   {
    "key": "CR2430",
    "labels": {
     "uk": "CR2430",
     "en": "CR2430",
     "pl": "CR2430",
     "de": "CR2430",
     "fr": "CR2430",
     "es": "CR2430",
     "it": "CR2430"
    }
   },
   {
    "key": "CR1220",
    "labels": {
     "uk": "CR1220",
     "en": "CR1220",
     "pl": "CR1220",
     "de": "CR1220",
     "fr": "CR1220",
     "es": "CR1220",
     "it": "CR1220"
    }
   },
   {
    "key": "LR44",
    "labels": {
     "uk": "LR44",
     "en": "LR44",
     "pl": "LR44",
     "de": "LR44",
     "fr": "LR44",
     "es": "LR44",
     "it": "LR44"
    }
   },
   {
    "key": "other",
    "labels": {
     "uk": "інша",
     "en": "other",
     "pl": "inna",
     "de": "andere",
     "fr": "autre",
     "es": "otra",
     "it": "altra"
    }
   }
  ]
 },
 {
  "kind": "transponder",
  "key": "chip_kind",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Тип чипа",
   "en": "Chip type",
   "pl": "Rodzaj chipa",
   "de": "Chiptyp",
   "fr": "Type de puce",
   "es": "Tipo de chip",
   "it": "Tipo di chip"
  },
  "options": [
   {
    "key": "fixed_code",
    "labels": {
     "uk": "фіксований код",
     "en": "fixed code",
     "pl": "kod stały",
     "de": "Festcode",
     "fr": "code fixe",
     "es": "código fijo",
     "it": "codice fisso"
    }
   },
   {
    "key": "crypto",
    "labels": {
     "uk": "криптований",
     "en": "crypto",
     "pl": "szyfrowany",
     "de": "verschlüsselt",
     "fr": "crypté",
     "es": "encriptado",
     "it": "criptato"
    }
   },
   {
    "key": "rolling_code",
    "labels": {
     "uk": "плаваючий код",
     "en": "rolling code",
     "pl": "kod zmienny",
     "de": "Wechselcode",
     "fr": "code tournant",
     "es": "código variable",
     "it": "codice variabile"
    }
   }
  ]
 },
 {
  "kind": "transponder",
  "key": "cloneable",
  "type": "bool",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Можна клонувати",
   "en": "Cloneable",
   "pl": "Można sklonować",
   "de": "Klonbar",
   "fr": "Clonable",
   "es": "Clonable",
   "it": "Clonabile"
  },
  "options": []
 },
 {
  "kind": "cylinder",
  "key": "length_mm",
  "type": "number",
  "min": 20,
  "max": 200,
  "labels": {
   "uk": "Довжина, мм",
   "en": "Length, mm",
   "pl": "Długość, mm",
   "de": "Länge, mm",
   "fr": "Longueur, mm",
   "es": "Longitud, mm",
   "it": "Lunghezza, mm"
  },
  "options": []
 },
 {
  "kind": "cylinder",
  "key": "keys_included",
  "type": "number",
  "min": 0,
  "max": 20,
  "labels": {
   "uk": "Ключів у комплекті",
   "en": "Keys included",
   "pl": "Kluczy w zestawie",
   "de": "Schlüssel im Set",
   "fr": "Clés fournies",
   "es": "Llaves incluidas",
   "it": "Chiavi incluse"
  },
  "options": []
 },
 {
  "kind": "cylinder",
  "key": "security_class",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Клас захисту",
   "en": "Security class",
   "pl": "Klasa zabezpieczenia",
   "de": "Sicherheitsklasse",
   "fr": "Classe de sécurité",
   "es": "Clase de seguridad",
   "it": "Classe di sicurezza"
  },
  "options": [
   {
    "key": "none",
    "labels": {
     "uk": "немає",
     "en": "none",
     "pl": "brak",
     "de": "keine",
     "fr": "aucune",
     "es": "ninguna",
     "it": "nessuna"
    }
   },
   {
    "key": "a",
    "labels": {
     "uk": "клас A",
     "en": "class A",
     "pl": "klasa A",
     "de": "Klasse A",
     "fr": "classe A",
     "es": "clase A",
     "it": "classe A"
    }
   },
   {
    "key": "b",
    "labels": {
     "uk": "клас B",
     "en": "class B",
     "pl": "klasa B",
     "de": "Klasse B",
     "fr": "classe B",
     "es": "clase B",
     "it": "classe B"
    }
   },
   {
    "key": "c",
    "labels": {
     "uk": "клас C",
     "en": "class C",
     "pl": "klasa C",
     "de": "Klasse C",
     "fr": "classe C",
     "es": "clase C",
     "it": "classe C"
    }
   }
  ]
 },
 {
  "kind": "cylinder",
  "key": "anti_snap",
  "type": "bool",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Захист від зламу (anti-snap)",
   "en": "Anti-snap",
   "pl": "Ochrona anti-snap",
   "de": "Anti-Snap",
   "fr": "Anti-casse (anti-snap)",
   "es": "Antirrotura (anti-snap)",
   "it": "Anti-strappo (anti-snap)"
  },
  "options": []
 },
 {
  "kind": "key_shell",
  "key": "buttons",
  "type": "number",
  "min": 0,
  "max": 8,
  "labels": {
   "uk": "Кнопок",
   "en": "Buttons",
   "pl": "Przycisków",
   "de": "Tasten",
   "fr": "Boutons",
   "es": "Botones",
   "it": "Tasti"
  },
  "options": []
 },
 {
  "kind": "key_shell",
  "key": "blade",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Лезо",
   "en": "Blade",
   "pl": "Ostrze",
   "de": "Bart",
   "fr": "Lame",
   "es": "Hoja",
   "it": "Lama"
  },
  "options": [
   {
    "key": "fixed",
    "labels": {
     "uk": "звичайне",
     "en": "fixed",
     "pl": "stałe",
     "de": "fest",
     "fr": "fixe",
     "es": "fija",
     "it": "fissa"
    }
   },
   {
    "key": "flip",
    "labels": {
     "uk": "викидне",
     "en": "flip",
     "pl": "składane",
     "de": "Klapp",
     "fr": "rétractable",
     "es": "plegable",
     "it": "a scatto"
    }
   },
   {
    "key": "emergency",
    "labels": {
     "uk": "аварійне",
     "en": "emergency",
     "pl": "awaryjne",
     "de": "Notschlüssel",
     "fr": "de secours",
     "es": "de emergencia",
     "it": "d’emergenza"
    }
   },
   {
    "key": "none",
    "labels": {
     "uk": "немає",
     "en": "none",
     "pl": "brak",
     "de": "keine",
     "fr": "aucune",
     "es": "ninguna",
     "it": "nessuna"
    }
   }
  ]
 },
 {
  "kind": "key_shell",
  "key": "with_blade",
  "type": "bool",
  "min": null,
  "max": null,
  "labels": {
   "uk": "З лезом",
   "en": "With blade",
   "pl": "Z ostrzem",
   "de": "Mit Bart",
   "fr": "Avec lame",
   "es": "Con hoja",
   "it": "Con lama"
  },
  "options": []
 },
 {
  "kind": "key_shell",
  "key": "logo",
  "type": "bool",
  "min": null,
  "max": null,
  "labels": {
   "uk": "З логотипом",
   "en": "With logo",
   "pl": "Z logo",
   "de": "Mit Logo",
   "fr": "Avec logo",
   "es": "Con logo",
   "it": "Con logo"
  },
  "options": []
 },
 {
  "kind": "battery",
  "key": "size",
  "type": "select",
  "min": null,
  "max": null,
  "labels": {
   "uk": "Типорозмір",
   "en": "Size",
   "pl": "Rozmiar",
   "de": "Größe",
   "fr": "Format",
   "es": "Tamaño",
   "it": "Formato"
  },
  "options": [
   {
    "key": "CR2032",
    "labels": {
     "uk": "CR2032",
     "en": "CR2032",
     "pl": "CR2032",
     "de": "CR2032",
     "fr": "CR2032",
     "es": "CR2032",
     "it": "CR2032"
    }
   },
   {
    "key": "CR2025",
    "labels": {
     "uk": "CR2025",
     "en": "CR2025",
     "pl": "CR2025",
     "de": "CR2025",
     "fr": "CR2025",
     "es": "CR2025",
     "it": "CR2025"
    }
   },
   {
    "key": "CR2016",
    "labels": {
     "uk": "CR2016",
     "en": "CR2016",
     "pl": "CR2016",
     "de": "CR2016",
     "fr": "CR2016",
     "es": "CR2016",
     "it": "CR2016"
    }
   },
   {
    "key": "CR1632",
    "labels": {
     "uk": "CR1632",
     "en": "CR1632",
     "pl": "CR1632",
     "de": "CR1632",
     "fr": "CR1632",
     "es": "CR1632",
     "it": "CR1632"
    }
   },
   {
    "key": "CR1620",
    "labels": {
     "uk": "CR1620",
     "en": "CR1620",
     "pl": "CR1620",
     "de": "CR1620",
     "fr": "CR1620",
     "es": "CR1620",
     "it": "CR1620"
    }
   },
   {
    "key": "CR1616",
    "labels": {
     "uk": "CR1616",
     "en": "CR1616",
     "pl": "CR1616",
     "de": "CR1616",
     "fr": "CR1616",
     "es": "CR1616",
     "it": "CR1616"
    }
   },
   {
    "key": "CR2450",
    "labels": {
     "uk": "CR2450",
     "en": "CR2450",
     "pl": "CR2450",
     "de": "CR2450",
     "fr": "CR2450",
     "es": "CR2450",
     "it": "CR2450"
    }
   },
   {
    "key": "CR2430",
    "labels": {
     "uk": "CR2430",
     "en": "CR2430",
     "pl": "CR2430",
     "de": "CR2430",
     "fr": "CR2430",
     "es": "CR2430",
     "it": "CR2430"
    }
   },
   {
    "key": "CR1220",
    "labels": {
     "uk": "CR1220",
     "en": "CR1220",
     "pl": "CR1220",
     "de": "CR1220",
     "fr": "CR1220",
     "es": "CR1220",
     "it": "CR1220"
    }
   },
   {
    "key": "LR44",
    "labels": {
     "uk": "LR44",
     "en": "LR44",
     "pl": "LR44",
     "de": "LR44",
     "fr": "LR44",
     "es": "LR44",
     "it": "LR44"
    }
   },
   {
    "key": "other",
    "labels": {
     "uk": "інша",
     "en": "other",
     "pl": "inna",
     "de": "andere",
     "fr": "autre",
     "es": "otra",
     "it": "altra"
    }
   }
  ]
 }
]"""
)


def seed(conn: Connection) -> None:
    """Inserts the list (sync connection: works in Alembic and via run_sync)."""
    order: dict[str, int] = {}
    for f in SEED:
        order[f["kind"]] = order.get(f["kind"], 0) + 1
        def_id = uuid.uuid4()
        conn.execute(
            insert(AttributeDef.__table__).values(
                id=def_id,
                kind=f["kind"],
                key=f["key"],
                type=f["type"],
                labels=f["labels"],
                min_value=f["min"],
                max_value=f["max"],
                sort_order=order[f["kind"]],
                is_hidden=False,
            )
        )
        for i, o in enumerate(f["options"], start=1):
            conn.execute(
                insert(AttributeOption.__table__).values(
                    id=uuid.uuid4(),
                    attribute_id=def_id,
                    key=o["key"],
                    labels=o["labels"],
                    sort_order=i,
                    is_hidden=False,
                )
            )
