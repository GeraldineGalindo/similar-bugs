# methods for 
import pandas as pd
from openai import OpenAI
import numpy as np
import tiktoken
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
token = os.getenv("GITHUB_TOKEN")
years = list(range(2010, 2026))
url = 'https://api.github.com/graphql'
headers = {"Authorization": f"Bearer {token}"}

def get_reduced_tokens(tokens, max_tokens):
    extra_tokens = len(tokens) - max_tokens 
    if extra_tokens % 2 != 0: extra_tokens += 1 

    half = len(tokens) // 2
    left_kept = max(0, half - extra_tokens//2)
    right_kept = min(len(tokens), half + extra_tokens//2)
    
    tokens = tokens[:left_kept] + tokens[right_kept:]
    return tokens

def reduce_tokens(text):
    max_tokens = 8190
    enc = tiktoken.encoding_for_model("text-embedding-3-large")
    tokens = enc.encode(text, allowed_special={'<|endoftext|>', '<|fim_prefix|>', '<|fim_suffix|>', '<|fim_middle|>'})

    if len(tokens) <= max_tokens:
        return text 

    print(f"Reducing tokens from {len(tokens)} to {max_tokens}")
    tokens = get_reduced_tokens(tokens, max_tokens)
    reduced_text = enc.decode(tokens)
    return reduced_text

def reduce_tokens_with_comments(text, comments, max_tokens=8190):
    enc = tiktoken.encoding_for_model("text-embedding-3-large")
    #total length
    combined_text = text + "\n" + comments
    tokens = enc.encode(combined_text, allowed_special={'<|endoftext|>', '<|fim_prefix|>', '<|fim_suffix|>', '<|fim_middle|>'})
    if(len(tokens) <= max_tokens):
        return text, comments
    
    print(f"Reducing tokens from {len(tokens)} to {max_tokens}")
    tokens_issue_description = enc.encode(text, allowed_special={'<|endoftext|>', '<|fim_prefix|>', '<|fim_suffix|>', '<|fim_middle|>'})
    tokens_comments = enc.encode(comments, allowed_special={'<|endoftext|>', '<|fim_prefix|>', '<|fim_suffix|>', '<|fim_middle|>'})
    reduced_comments_tokens = get_reduced_tokens(tokens_comments, max_tokens - len(tokens_issue_description))
    reduced_comments = enc.decode(reduced_comments_tokens)
    return text, reduced_comments

def normalize_comments(nodes):
    bot_names = ['github-actions', 'stale', 'dependabot', 'renovate', 'web-flow', 'codecov', 'snyk-bot', 'Issues-translate-bot']
    comments_list = nodes['nodes']
    if not comments_list:
        return "No comments for this issue."
    comments = []
    for comment in comments_list:
        author = comment['author']['login'] if comment['author'] else 'Unknown'
        if author.lower() not in bot_names:
            body = comment['body']
            comments.append(f"_user_comment_: {body}")
    return " ".join(comments)
