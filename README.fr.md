# MXReady

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | **Français** | [Deutsch](README.de.md) | [Русский](README.ru.md)

Vous avez du code PyTorch qui tourne sur des cartes NVIDIA et vous voulez le porter sur un GPU MetaX. Vous ne savez pas encore ce qui va casser.

MXReady lit le code sans l'exécuter et liste les endroits qui risquent de poser problème :

- là où le compilateur NVIDIA est appelé directement ;
- là où l'on suppose des groupes de 32 threads (MetaX en utilise 64) ;
- là où l'on utilise de l'assembleur en ligne propre à NVIDIA ;
- là où l'on dépend d'une bibliothèque absente de la nouvelle carte.

Chaque résultat indique le fichier, la ligne, la raison du problème et la correction suggérée.

## Utilisation

Téléchargez l'archive ZIP de votre système, décompressez-la et lancez l'installeur.

```bash
# Linux / macOS
bash install.sh
bash start.sh
```

```powershell
# Windows
.\install.ps1
.\start.ps1
```

Ouvrez ensuite <http://127.0.0.1:8000> et collez l'adresse du dépôt.

Cela fonctionne aussi en ligne de commande :

```bash
mxready-scan ./my-repo \
  --repo-url https://github.com/example/my-repo \
  --commit <commit de 40 caractères> \
  --output reports
```

## Ce qu'il ne fait pas

- Il ne réécrit pas votre code.
- Il n'affiche pas de « pourcentage de compatibilité ». Le nombre de règles déclenchées ne dit rien sur le fait que le projet fonctionnera.
- Une analyse statique propre signifie seulement que rien d'évident n'a été trouvé. La vraie réponse vient de l'exécution du même commit sur une machine MetaX.

## Pour aller plus loin

- [Documentation complète (chinois)](README.md)
- [Full documentation (English)](README.en.md)
- [Liste des règles](docs/rules.md)
- [Architecture](docs/architecture.md)

Licence [Apache-2.0](LICENSE).
