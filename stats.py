import os
from github import Github

# instancias de Github
github = Github(os.getenv("SECRET_TOKEN"))
hyromy = github.get_user()

# varibles de commits
total_commits = 0
total_insertions = 0
total_deletions = 0
efective_lines = 0
efectivity = 0
ave_lines_per_commit = 0

# variables de lenguajes
languages_data = {}
total_bytes = 0

# iterar repositorios
for repo in hyromy.get_repos():
    # descartar repositorios bifurcados
    if repo.fork:
        continue

    # obtener lenguajes
    languages = repo.get_languages()
    for language, bytes in languages.items():
        # lenguaje inexistente
        if language not in languages_data:
            languages_data[language] = {"bytes": bytes}
        
        # lenguaje existente
        else:
            languages_data[language]["bytes"] += bytes

        # sumar bytes totales
        total_bytes += bytes

    # calcular porcentaje de uso de lenguajes
    for language, data in languages_data.items():
        data["percentage"] = (data["bytes"] / total_bytes) * 100

    # ordenar lenguajes por porcentaje
    languages_data = dict(sorted(languages_data.items(), 
                                 key = lambda x: x[1]["percentage"], 
                                 reverse = True))

    # obtener commits
    insertions = 0
    deletions = 0
    commits = repo.get_commits(author = hyromy.login)
    total_commits += commits.totalCount
    for commit in commits:
        stats = commit.stats
        
        # sumar inserciones y eliminaciones
        insertions += stats.additions
        deletions += stats.deletions
        total_insertions += insertions
        total_deletions += deletions

# calcular estadisticas
efective_lines = total_insertions - total_deletions
efectivity = (efective_lines * 100) / total_insertions
ave_lines_per_commit = efective_lines // total_commits

# leer README.md
with open("README.md", "r", encoding = "utf-8") as f:
    readme = f.read()

# identificar seccion de estadisticas
part1, _, rest = readme.partition("<!-- stats -->")
_, _, part3 = rest.partition("<!-- /stats -->")

# generar informacion de estadisticas
info = "## Lenguajes de programación\n\n"
for language, data in languages_data.items():
    info += f"- {language} **{data['percentage']:.2f}%**\n"

info += f"\n\n## Actividad en github\n"
info += f"- Commits totales: **{total_commits}**\n"
info += f"- Inserciones totales: **{total_insertions}**\n"
info += f"- Eliminaciones totales: **{total_deletions}**\n"
info += f"- Lineas efectivas: **{efective_lines}**\n"
info += f"- Efectividad: **{efectivity:.2f}%**\n"
info += f"- Lineas por commit: **{ave_lines_per_commit}**\n"

# actualizar informacion de estadisticas en README.md
data = f"<!-- stats -->\n{info}<!-- /stats -->"
data = part1 + data + part3

# escribir informacion en README.md
with open("README.md", "w", encoding = "utf-8") as f:
    f.write(data)