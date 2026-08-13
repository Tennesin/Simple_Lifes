import random

MALE_NAMES = [
    "Liam", "Noah", "Oliver", "Elijah", "James", "William", "Benjamin", "Lucas",
    "Henry", "Alexander", "Daniel", "Matthew", "Jackson", "Sebastian", "Jack", "Owen",
    "Samuel", "Wyatt", "John", "David", "Leo", "Julian", "Hudson", "Ezra",
    "Gabriel", "Carter", "Isaac", "Jayden", "Luca", "Anthony", "Dylan", "Christopher",
    "Joshua", "Andrew", "Theodore", "Caleb", "Ryan", "Asher", "Nathan", "Adrian",
    "Miles", "Eli", "Ivan", "Nikolai", "Dmitri", "Sergei", "Pavel", "Anton",
    "Viktor", "Igor", "Boris", "Yuri", "Stefan", "Mikhail", "Alexei", "Roman",
    "Vlad", "Kai", "Ren", "Haruto", "Sora", "Yuto", "Riku", "Daiki",
    "Hikaru", "Kenji", "Takeshi", "Akira", "Hiroshi", "Satoru", "Ahmed", "Youssef",
    "Karim", "Tariq", "Rashid", "Omar", "Hassan", "Malik", "Zaid", "Amir",
    "Kwame", "Kofi", "Sekou", "Jabari", "Chidi", "Amadi", "Diego", "Mateo",
    "Santiago", "Rafael", "Alejandro", "Pablo", "Emilio", "Gustavo", "Ricardo", "Fernando",
    "Marco", "Giovanni", "Matteo", "Lorenzo", "Enzo", "Dante", "Adriano", "Massimo",
    "Alessandro", "Felix", "Hugo", "Klaus", "Otto", "Friedrich", "Heinrich", "Lukas",
    "Bastian", "Erik", "Anders", "Bjorn", "Magnus", "Sven", "Gunnar", "Oskar",
    "Finn", "Rowan", "Callum", "Declan", "Cormac", "Fintan", "Tadhg", "Cian",
    "Aidan", "Cyrus", "Darius", "Kian", "Arash", "Farid",
]

FEMALE_NAMES = [
    "Olivia", "Emma", "Ava", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia",
    "Harper", "Evelyn", "Abigail", "Emily", "Elizabeth", "Sofia", "Avery", "Ella",
    "Scarlett", "Grace", "Chloe", "Victoria", "Riley", "Aria", "Lily", "Aurora",
    "Zoey", "Penelope", "Layla", "Nora", "Hazel", "Violet", "Stella", "Aaliyah",
    "Savannah", "Audrey", "Brooklyn", "Bella", "Claire", "Skylar", "Natalia", "Nadia",
    "Katarina", "Yelena", "Irina", "Anastasia", "Olga", "Larisa", "Svetlana", "Tatiana",
    "Ksenia", "Vera", "Yuki", "Hana", "Sakura", "Ayaka", "Mei", "Rin",
    "Aoi", "Yui", "Emiko", "Naoko", "Fatima", "Amira", "Zainab", "Yasmin",
    "Noor", "Leila", "Samira", "Aisha", "Amara", "Zola", "Nia", "Amani",
    "Adaeze", "Chiamaka", "Valentina", "Camila", "Lucia", "Isabela", "Gabriela", "Daniela",
    "Carmen", "Elena", "Rosa", "Ines", "Giulia", "Francesca", "Bianca", "Alessia",
    "Chiara", "Serena", "Ilaria", "Greta", "Ingrid", "Freya", "Astrid", "Signe",
    "Karin", "Elsa", "Liv", "Saga", "Maja", "Siobhan", "Niamh", "Aoife",
    "Ciara", "Maeve", "Roisin", "Fiona", "Deirdre", "Bridget", "Selene", "Athena",
    "Daphne", "Iris", "Calliope", "Thalia",
]

DEFAULT_NAME_POOLS = {
    "male": MALE_NAMES,
    "female": FEMALE_NAMES,
}

def random_name(gender_key, pools=None):
    pools = pools or DEFAULT_NAME_POOLS
    pool = pools.get(gender_key)
    if not pool:
        pool = next(iter(pools.values()), [])
    return random.choice(pool) if pool else ""