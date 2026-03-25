import pandas as pd

# Charger le fichier CSV
df = pd.read_csv('uvbf_data.csv')

# Fusionner 'Author' et 'Auteur' dans une seule colonne 'Author'
df['Author'] = df['Author'].fillna('') + ' ' + df['Auteur'].fillna('')
df['Author'] = df['Author'].str.strip()  # Nettoyer les espaces inutiles

# Fusionner 'Tweet' et 'Texte' dans une seule colonne 'Tweet'
df['Tweet'] = df['Tweet'].fillna('') + ' ' + df['Texte'].fillna('')
df['Tweet'] = df['Tweet'].str.strip()

# Supprimer les colonnes devenues inutiles
df.drop(columns=['Auteur', 'Texte'], inplace=True)

# Sauvegarder le fichier modifié
df.to_csv('uvb_all.csv', index=False)
