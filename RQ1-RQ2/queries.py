# queries for GraphQL and OpenAI API interactions
import pandas as pd
from openai import OpenAI
import requests
import time
import json
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
token = os.getenv("GITHUB_TOKEN")
years = list(range(2020, 2026))
url = 'https://api.github.com/graphql'
headers = {"Authorization": f"Bearer {token}"}


def get_commit_main_branch(begin, end, repo_owner, repo_name):
    next_page = True
    cursor = None
    commits = []

    while next_page:
        query = f"""
        {{
           repository(owner: "{repo_owner}", name: "{repo_name}") {{
                ref(qualifiedName: "refs/heads/dev") {{
                target {{
                    ... on Commit {{
                            history(
                                since: "{begin}T00:00:00Z",
                                until: "{end}T00:00:00Z",
                                first: 100{f', after: "{cursor}"' if cursor else ''}
                            ) {{
                                pageInfo {{
                                    endCursor
                                    hasNextPage
                                }}
                                edges {{
                                    node {{
                                        oid
                                        associatedPullRequests(first:10){{
                                            nodes {{
                                                number
                                            }}
                                        }}
                                    }}  
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        response = requests.post(url, json = {'query': query}, headers=headers)
        data = response.json()
        print(data)
        history = data['data']['repository']['ref']['target']['history']
        for edge in history['edges']:
            commits.append(edge['node'])

        next_page = history['pageInfo']['hasNextPage']
        cursor = history['pageInfo']['endCursor']
        time.sleep(2)

    return commits 

def check_commit_pr(sha, owner, repo):
    query = """
        query($owner: String!, $name: String!, $oid: GitObjectID!) {
          repository(owner: $owner, name: $name) {
            object(oid: $oid) {
              ... on Commit {
                oid
                associatedPullRequests(first: 5) {
                  nodes {
                    number
                  }
                }
              }
            }
          }
        }
        """

    variables = {"owner": owner, "name": repo, "oid": sha}
    response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
    data = response.json()["data"]["repository"]["object"]

    if data and "associatedPullRequests" in data:
        prs = data["associatedPullRequests"]["nodes"]
    else:
        prs = []

    return prs



def get_merged_pr(begin, end, repo_owner, repo_name):
    next_page = True
    cursor = None
    prs = []

    while next_page:
        query = f"""
        {{
           search(
            query: "repo:{repo_owner}/{repo_name} is:pr is:merged closed:{begin}..{end}",
            type: ISSUE,
            first: 100{f', after: "{cursor}"' if cursor else ''}
            ){{
                pageInfo{{
                    endCursor
                    hasNextPage
                }}
                edges {{
                    node {{
                        ... on PullRequest {{
                            number
                            title
                            url
                            bodyText
                            createdAt
                            mergedAt
                        }}
                    }}
                }}
            }}
        }}
        """
        response = requests.post(url, json = {'query': query}, headers=headers)
        data = response.json()
        #print(data)
        search = data['data']['search']
        for edge in search['edges']:
            prs.append(edge['node'])
        next_page = search['pageInfo']['hasNextPage']
        cursor = search['pageInfo']['endCursor']
        time.sleep(2)

    return prs    


def get_embedding(text, model='text-embedding-3-large'):
    response = client.embeddings.create(
        model = model, 
        input = text
    )
    return response.data[0].embedding

def run_query(query, variables=None):
    response = requests.post(url, json={'query': query, 'variables': variables or {}}, headers=headers)
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            print(response.text[:500]) 
            raise Exception("Failed to parse JSON response")
    else:
        raise Exception(f"Query failed with status code {response.status_code}. {response.text}")

def get_defect_issues(begin, end, repo_owner, repo_name):
    next_page = True
    cursor = None
    issues = []

    while next_page:
        query = f"""
        {{
           search(
            query: "repo:{repo_owner}/{repo_name} is:issue state:closed closed:{begin}..{end} reason:completed",
            type: ISSUE,
            first: 100{f', after: "{cursor}"' if cursor else ''}
            ){{
                pageInfo{{
                    endCursor
                    hasNextPage
                }}
                edges {{
                    node {{
                        ... on Issue {{
                            number
                            title
                            url
                            bodyText
                            comments(first: 50) {{
                              nodes {{
                                author {{
                                    login
                                }}
                                body
                              }}
                            }}
                            createdAt
                            assignees (first: 10) {{
                                nodes {{
                                    login
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        response = requests.post(url, json = {'query': query}, headers=headers)
        data = response.json()
        #print(data)
        search = data['data']['search']
        for edge in search['edges']:
            issues.append(edge['node'])
        next_page = search['pageInfo']['hasNextPage']
        cursor = search['pageInfo']['endCursor']
        time.sleep(2)

    return issues


def get_diff_pr(repo_owner, repo_name, pr_number):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff",
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.text 

def get_diff_commit(repo_owner, repo_name, commit_sha):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits/{commit_sha}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff",
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.text 

def get_diff(url):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff",
    }
    r = requests.get(url + '.diff', headers=headers)
    r.raise_for_status()
    return r.text 

def get_info_issue(repo_owner, repo_name, issue_number):
    next_page = True
    cursor = None
    issues = []
    query = f"""
    {{
        repository(owner: "{repo_owner}", name: "{repo_name}") {{
            issue(number: {issue_number}) {{
                number
                body
                closedAt
            }}
        }}
    }}

    """
    response = requests.post(url, json = {'query': query}, headers=headers)
    data = response.json()
    time.sleep(1)
    return data.get('data', {}).get('repository', {}).get('issue', {})

def obtain_issues_monthly(year, owner, repo, fun):
    months= {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    year_issues = []
    for month, days in months.items():
        if month == 2:
            if (year % 400 == 0) or (year % 4 == 0 and year % 100 != 0):
                days = 29
        if month < 10:
            begin = f"{year}-0{month}-01"
            end = f"{year}-0{month}-{days}"
        else:
            begin = f"{year}-{month}-01"
            end = f"{year}-{month}-{days}"
        issues = fun(begin, end, owner, repo)
        year_issues.extend(issues)
    return year_issues
        

def get_closed_issues(year, owner, repo):
    all_issues = []
    for year in years:
        issues = obtain_issues_monthly(year, owner, repo, get_defect_issues)
        print(f"Year {year}: Retrieved {len(issues)} closed issues.")
        pd.to_pickle(pd.DataFrame(issues), f"issues_cross_references/{repo}_{year}.pkl")
        all_issues.extend(issues)
    return all_issues


def get_repo_info(owner, repo, entity):
    if entity == 'issues':
        fun =  get_defect_issues
    if entity == 'prs':
        fun =  get_merged_pr
    if entity == 'commit':
        fun = get_commit_main_branch

    all_items = []
    for year in years:
        items = obtain_issues_monthly(year, owner, repo, fun)
        print(f"Year {year}: Retrieved {len(items)} {entity}.")
        pd.to_pickle(pd.DataFrame(items), f"{entity}/{repo}_{year}.pkl")
        all_items.extend(items)
    return all_items
    

