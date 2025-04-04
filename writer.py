import re
import json

def write_in_json(data:dict):
    with open(".json", "w") as f:
        json.dump(data, f, indent = 4)

def read_json():
    with open(".json", "r") as f:
        data = json.load(f)
        
    return data

def write_readme(*lines):
    with open("README.md", "w", encoding = "utf-8") as f:
        for line in lines:
            f.write(line + "\n")

def split_by_tag_comment(tag: str) -> tuple:
    with open("README.md", "r") as f:
        content = f.read()
    
    start_tag = f"<!-- #{tag} -->"
    end_tag = f"<!-- #/{tag} -->"
    
    pattern = re.compile(
        rf"(.*?{re.escape(start_tag)}\n?)(.*?)(\n?{re.escape(end_tag)}.*)",
        re.DOTALL
    )

    match = pattern.match(content)
    if match:
        return (
            match.group(1).splitlines(),
            match.group(2).splitlines(),
            match.group(3).splitlines()[1:]
        )

    else:
        raise ValueError(f"Tags {start_tag} y {end_tag} no encontrados.")
    
def main():
    before, _, after = split_by_tag_comment("stats")

    data = read_json()
    repos = data["repos"]

    repos_len = len(repos)
    commits = sum([repo["my_commits"] for repo in repos.values()])
    
    insertions = 0
    for repo_name, repo_data in repos.items():
        for lang, lang_data in repo_data["langs"].items():
            insertions += lang_data.get("insertions", 0)
    
    deletions = 0
    for repo_name, repo_data in repos.items():
        for lang, lang_data in repo_data["langs"].items():
            deletions += lang_data.get("deletions", 0)
    
    lines = insertions - deletions
    lines_per_commit = (lines // commits if commits > 0 else 0)
    lines_per_repo = lines // repos_len if repos_len > 0 else 0
    eficiency = (lines / insertions * 100) if commits > 0 else 0

    langs_len = len(data["langs_details"])
    
    langs_details = data["langs_details"]
    sorted_langs = sorted(
        langs_details.items(),
        key=lambda item: item[1]["usage"],
        reverse=True
    )

    content = [
        f"### Estadísticas Generales",
        f"- **Total de repositorios:** {repos_len}",
        f"- **Total de commits:** {commits}",
        f"- **Total de líneas añadidas:** {insertions}",
        f"- **Total de líneas eliminadas:** {deletions}",
        f"- **Total de líneas netas:** {lines}",
        f"- **Líneas por commit:** {lines_per_commit}",
        f"- **Líneas por repositorio:** {lines_per_repo}",
        f"- **Eficiencia:** {eficiency:.2f}%",
        "",
        f"### Lenguajes Utilizados",
        f"- **Total de lenguajes:** {langs_len}",
    ]

    content.append("#### Lenguajes ordenados por uso:")
    for lang, details in sorted_langs:
        content.append(f"  - {lang}: {details['usage']:.2f}%")

    write_readme(*before, *content, *after)
    before, _, after = split_by_tag_comment("process")

    content = [
        "<!--",
        f"\tcores: {data['process']['cores']}",
        f"\truntime: {data['process']['runtime']}s",
        "-->"
    ]

    write_readme(*before, *content, *after)

if __name__ == "__main__":
    main()
