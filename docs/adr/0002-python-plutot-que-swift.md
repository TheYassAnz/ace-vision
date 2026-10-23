# Python plutôt que Swift pour l'analyse

L'analyse (et l'appli web locale qui l'expose) est écrite en Python, bien que Vision d'Apple sache repérer le corps humain nativement en Swift. Le suivi de balle (TrackNet), le réentraînement des modèles et la plupart des projets d'analyse de tennis open source sont en Python : en Swift, il faudrait développer ces modèles en Python puis les convertir, donc écrire le travail deux fois. Python tourne bien sur la puce Apple (M4 Pro) via PyTorch/MPS.
