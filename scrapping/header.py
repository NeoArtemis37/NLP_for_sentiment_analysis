import pandas as pd

# Charger le fichier
df = pd.read_csv("UVBF_fb.csv")

# Afficher les entêtes actuelles
print("Anciennes entêtes :", df.columns.tolist())

# Sauvegarder le fichier modifié
df.drop(columns=['Tweet'], inplace=True)
df.to_csv("UVBF_fb.csv", index=False)
