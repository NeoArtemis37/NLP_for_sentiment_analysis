#author: artemis
import pandas as pd
import glob

chemin = "*.csv"  
fichiers = glob.glob(chemin)
df_combine = pd.concat([pd.read_csv(f) for f in fichiers], ignore_index=True)
df_combine.drop_duplicates(inplace=True)
df_combine.to_csv("uvbf_data.csv", index=False)
