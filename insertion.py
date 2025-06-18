from pymongo import MongoClient
from datetime import datetime, timedelta
import random

# 1) Connexion à MongoDB locale
client = MongoClient("mongodb://localhost:27017/")
db = client.appleSales
sales = db.sales

# 2) Pays d'Europe en français
countries = [
    "Albanie", "Andorre", "Autriche", "Biélorussie", "Belgique",
    "Bosnie-Herzégovine", "Bulgarie", "Croatie", "Chypre",
    "République tchèque", "Danemark", "Estonie", "Finlande",
    "France", "Allemagne", "Grèce", "Hongrie", "Islande",
    "Irlande", "Italie", "Kosovo", "Lettonie", "Liechtenstein",
    "Lituanie", "Luxembourg", "Malte", "Moldavie", "Monaco",
    "Monténégro", "Pays-Bas", "Macédoine du Nord", "Norvège",
    "Pologne", "Portugal", "Roumanie", "Saint-Marin", "Serbie",
    "Slovaquie", "Slovénie", "Espagne", "Suède", "Suisse",
    "Ukraine", "Royaume-Uni"
]

# 3) Génération des documents pour 2025
docs = []
base_date = datetime(2025, 1, 1)

for country in countries:
    n_sales = random.randint(50, 150)
    for _ in range(n_sales):
        purchase_dt = base_date + timedelta(
            days=random.randint(0, 364),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        docs.append({
            "purchaseDate": purchase_dt,
            "country":      country,
            "quantity":     random.randint(1, 20)
        })

# 4) Réinitialisation + insertion en base
sales.drop()
res = sales.insert_many(docs)
print(f"✅ Inséré {len(res.inserted_ids)} documents dans appleSales.sales")
