"""
This file defines methods to generate LLM responses to discussion posts and then saved in csv format.
NOTE: this file will only work if you have a GOOGLE_API_KEY environment variable that gives you access
to the gemini-pro model api

By: Matthew Mattei
Date: 3/14/24
Credits: ChatGPT was used for planning and writing elements of the code in this file
"""

# Imports
from collections import Counter
import csv
import env
import google.generativeai as genai
import os
import re

# Same as REMOVE_EXTRA_CHARS_RE except this doesn't include \n since \n needs to be handled specially
REMOVE_EXTRA_CHARS_RE_2 = r'[\[\]\r\t?".,\/#!$%^&*;:{}=_`~()\[\]-]+'

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-pro')

def read_from_csv(csv_path: str):
    """
    Helper function to load csv of discussion topics + contents in as a list.
    csv_path must be a properly formatted file pathway.
    """

    data = []
    with open(csv_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            data.append(row)
    return data

def generate_llm_response(game_title: str, formatted_topic: list):
    """
    Helper function that takes in a topic in the format [title, content] and will generate
    a response from gemini and a game_title.
    """

    # Note that the llm is encouraged to act more anonmyously to generate a response
    # meant to mimic a generic user on the thread
    llm_text_input = "You are a player (do not act like a dev, that is dishonest and unhelpful) on a forum discussing " + game_title + ". Reply to a post with the title [" + formatted_topic[0] + "] with content [" + formatted_topic[1] + "]"
    response = model.generate_content(llm_text_input)

    # Necessary try/except since response can fail to return and accessing it will cause a crash
    try:
        return response.text
    except:
        return ""

def generate_llm_dataset(responses: list, filename: str):
    """
    Helper function that takes a list of LLM generated responses and converts it into a csv
    file of words with the name filename.
    """

    total_contents = []
    
    # Takes each response and breaks it into the individual words, making total_contents a list of words
    words = [response.split() for response in responses]
    for sublist in words:
        total_contents += sublist
    
    # Write the list of LLM response contents to the CSV file
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(total_contents)

def generate_all_responses(game_title: str, old_csv_path: str, new_csv_path: str):
    """
    Generate LLM responses about a game to each discussion post available in the file referenced
    by old_csv_path and save them to new_csv_path.
    """

    print("Starting LLM Generation")
    topics = read_from_csv(old_csv_path)
    all_responses = []
    for topic in topics:
        print("Processing new topic.")
        all_responses.append(generate_llm_response(game_title, topic))
    
    cleaned_responses = [re.sub(REMOVE_EXTRA_CHARS_RE_2, '', content.replace("/", " ")).replace("\n", " ").strip().lower() for content in all_responses]

    generate_llm_dataset(cleaned_responses, new_csv_path)
    
    cleaned_responses = [Counter(i.split()) for i in all_responses]

    # Returns dicts of words and their counts in each response
    return cleaned_responses