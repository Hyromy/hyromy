import os
import re
from multiprocessing import Process, Manager
from time import time

import requests
from dotenv import load_dotenv

import writer

load_dotenv()

URL = "https://api.github.com/"
LANGS = {
    ".js": "JavaScript",
    ".html": "HTML",
    ".css": "CSS",
    ".java": "Java",
    ".php": "PHP",
    ".cs": "C#",
    ".py": "Python",
    ".cpp": "C++"
}

def get_repos(token:str) -> list[dict]:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    repos = []
    params = {"per_page": 100, "page": 1}

    while True:
        response = requests.get(URL + "user/repos", headers = headers, params = params)
        if response.status_code != 200:
            raise Exception(f"Error al obtener repos: {response.status_code} - {response.text}")
        
        data = response.json()
        if not data:
            break
        
        repos.extend(data)
        params["page"] += 1

    return repos

def get_commits(token:str, repo_full_name:str) -> list[dict]:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    commits = []
    params = {"per_page": 100, "page": 1}

    while True:
        response = requests.get(URL + f"repos/{repo_full_name}/commits", headers = headers, params = params)
        if response.status_code != 200:
            raise Exception(f"Error al obtener commits: {response.status_code} - {response.text}")
        
        data = response.json()
        if not data:
            break
        
        commits.extend(data)
        params["page"] += 1

    return commits

def filter_commits_by_author(commits: list[dict], author: str) -> list[dict]:
    return [commit for commit in commits if commit["commit"]["author"]["name"] == author]

def exclude_merge_commits(commits: list[dict]) -> list[dict]:
    return [commit for commit in commits if not len(commit["parents"]) > 1]

def get_commit_details(token:str, repo_full_name:str, sha:str) -> dict:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(URL + f"repos/{repo_full_name}/commits/{sha}", headers = headers)
    if response.status_code != 200:
        raise Exception(f"Error al obtener commit: {response.status_code} - {response.text}")
    
    return response.json()

def create_process(repos: list[dict], token, user, shared_data) -> list[Process]:
    process = []
    for repo in repos:
        process.append(
            Process(
                name = repo["name"],
                target = extract,
                args = (token, user, repo, shared_data)
            )
        )

    return process

def extract(token: str, user: str, repo: dict, shared_data):
    start = time()

    try:
        total_commits = get_commits(token, repo["full_name"])
    except Exception as e:
        print(f"Error en el repo {repo['name']}: {e}")
        return

    util_commits = exclude_merge_commits(total_commits)
    commits = filter_commits_by_author(util_commits, user)

    len_total_commits = len(total_commits)
    len_commits = len(commits)
    len_util_commits = len(util_commits)
    
    langs = {}
    for commit in commits:
        for file in get_commit_details(token, repo["full_name"], commit["sha"])["files"]:
            file_ext = re.search(r"\.[a-zA-Z0-9]+$", file["filename"])
            file_ext = file_ext.group(0) if file_ext else None

            if file_ext in LANGS:
                if file_ext in langs:
                    langs[file_ext]["insertions"] += file["additions"]
                    langs[file_ext]["deletions"] += file["deletions"]

                else:
                    langs[file_ext] = {
                        "insertions": file["additions"],
                        "deletions": file["deletions"]
                    }

    shared_data[repo["name"]] = {
        "total_commits": len_total_commits,
        "util_commits": len_util_commits,
        "my_commits": len_commits,
        "owner": repo["owner"]["login"],
        "participation": len_commits / len_util_commits * 100,
        "langs": calculate_usage(langs),
        "run_time": time() - start
    }    

def do_process(process:list[Process]):
    waiting:list[Process] = process.copy()
    in_run:list[Process] = []
    finisthed:list[Process] = []

    in_run_c = 0
    finisthed_c = 0
    process_amount = len(waiting)

    all_startted = False
    all_finisthed = False

    while len(finisthed) < process_amount:
        if len(waiting) > 0:
            in_run.append(waiting.pop(0))

            for p in in_run:
                if p.exitcode is None and not p.is_alive():
                    in_run_c += 1
                    print(f"Proceso {p.name} iniciando ({in_run_c}/{process_amount}).")
                    p.start()

        if len(in_run) > 0:
            for p in in_run:
                if not p.is_alive():
                    finisthed_c += 1
                    print(f"Proceso {p.name} terminado ({finisthed_c}/{process_amount}).")
                    finisthed.append(p)
                    in_run.remove(p)

        if in_run_c == process_amount and not all_startted:
            all_startted = True
            print("\nTodos los procesos han sido iniciados.\n")
        
        if finisthed_c == process_amount and not all_finisthed:
            all_finisthed = True
            print("\nTodos los procesos han terminado.\n")

def rename_keys(data: dict) -> dict:
    returnable = {}
    for key in data.keys():
        if key in LANGS:
            returnable[LANGS[key]] = data[key]

        else:
            returnable[key] = data[key]

    return returnable

def calculate_usage(data: dict) -> dict:
    total_lines = 0
    for lang, lang_data in data.items():
        total_lines += lang_data["insertions"] - lang_data["deletions"]

    for lang, lang_data in data.items():
        lang_data["usage"] = (lang_data["insertions"] - lang_data["deletions"]) / total_lines * 100

    return data

def get_lang_details(repos_data: dict) -> dict:
    total_lines = 0
    tiers = {}
    for repo, data in repos_data.items():
        for lang in data["langs"]:
            insertions = repos_data[repo]["langs"][lang]["insertions"]
            deletions = repos_data[repo]["langs"][lang]["deletions"]
            total_lines += insertions - deletions

            if lang not in tiers:
                tiers[lang] = {
                    "lines": insertions - deletions,
                    "usage": 0,
                }

            else:
                tiers[lang]["lines"] += insertions - deletions

    for lang in tiers:
        tiers[lang]["usage"] = (tiers[lang]["lines"] / total_lines) * 100

    return tiers

def main():
    start_time = time()

    TOKEN = os.getenv("TOKEN") or os.environ("TOKEN")
    USER = "Hyromy"

    repos_data = None
    with Manager() as manager:
        shared_data = manager.dict()

        repos = get_repos(TOKEN)
        do_process(create_process(repos, TOKEN, USER, shared_data))

        repos_data = dict(shared_data)

    for repo_name, repo_data in repos_data.items():
        if "langs" in repo_data:
            repo_data["langs"] = rename_keys(repo_data["langs"])
            repos_data[repo_name] = repo_data

    user_stats = {
        "repos": repos_data,
        "langs_details": get_lang_details(repos_data),
        "user": {
            "name": USER,
            "url": "https://github.com/" + USER,
        },
        "process": {
            "cores": os.cpu_count(),
            "runtime": time() - start_time,
        }
    }

    writer.write_in_json(user_stats)

if __name__ == "__main__":
    main()
    