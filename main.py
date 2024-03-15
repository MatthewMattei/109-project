"""
This file runs scraper and llm generation methods to develop datasets for Steam forum
community texts and LLM-generated texts for the purposes of comparing the statistical
probabilities certain words appear in each.
NOTE: The LLM dataset generation only works if you have a GOOGLE_API_KEY to access
the gemini-pro model api

By: Matthew Mattei
Date: 3/14/24
Credits: ChatGPT was used for planning and writing elements of the code in this file
and the unigram_freq.csv dataset used in this file was uploaded and made
publically availabe by Rachel Tatman on Kaggle
"""

# Imports
from collections import Counter
import csv
from generate_llm_responses import generate_all_responses
import json
from langdetect import detect
import random
from steam_discussion_scraper import combined_scrape

NUM_COMMON_WORDS = 10
NUM_MOST_ENGLISH_WORDS = 0

def x_most_common_words(x: int):
    """
    Helper function that reads in the x most common words in unigram_freq.csv
    (dataset sourced from https://www.kaggle.com/datasets/rtatman/english-word-frequency)
    """

    data = []
    with open("unigram_freq.csv", 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for i, row in enumerate(reader):
            if i >= x:
                break
            data.append(row[0])
    return data

def dataset_to_list(file_path: str):
    """
    Helper function to convert a csv with one line of comma-separated words into a list.
    """

    with open(file_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            return row

def make_y_most_common_word_dicts(y: int, x: int, discussion_csv: str, llm_csv: str):
    """
    Finds the y most common words in discussion_csv when the x most common english words
    are removed and returns dicts of how many times those y most common words in discussion_csv
    appear in discussion_csv and llm_csv. Also filters out contractions and non-english
    words.
    """

    words_to_exclude = set(x_most_common_words(x))
    discussion_list = dataset_to_list(discussion_csv)
    llm_list = dataset_to_list(llm_csv)
    discussion_list = [word for word in discussion_list if word not in words_to_exclude]
    llm_list = [word for word in llm_list if word not in words_to_exclude]
    counts = Counter(discussion_list)
    discussion_dict = Counter({})
    for word in counts:
        try:
            if detect(word) == 'en' and "'" not in word:
                discussion_dict[word] = counts[word]
        except:
            continue
    counts = Counter(llm_list)
    discussion_dict = {i: discussion_dict[i] for i in discussion_dict}
    llm_dict = {i: counts[i] for i in counts}
    common_keys_set = set(discussion_dict.keys()) & set(llm_dict.keys())
    return {i[0]: i[1] for i in Counter({key: discussion_dict[key] for key in common_keys_set}).most_common(y)}

def write_all_relevant_data(num_common_word_intervals: int = 500, num_common_word_trials: int = 3, url: str = "https://steamcommunity.com/app/1055540/discussions/0/", game_title: str = "A Short Hike", contents_filename: str = "words.csv", op_filename: str = "op.csv", new_csv_path: str = "llm.csv"):
    """
    Takes scraper functionality and llm generation functionality to produce the scraper dataset, the LLM dataset, and num_common_word_trials dicts
    with the NUM_COMMON_WORDS of most common words in the scraper dataset (in intervals) when the NUM_MOST_ENGLISH_WORDS + interval
    most common english words are removed as well as how many times those words appear in both the scraper dataset and the
    llm dataset and write them to a json file. Then, dicts of all posts, llm responses, and the common word dict are written
    to json files.
    """
    posts = combined_scrape(url, contents_filename, op_filename)
    llm_responses = generate_all_responses(game_title, op_filename, new_csv_path)
    words_to_check = []
    for i in range(num_common_word_trials):
        words_to_check.append(make_y_most_common_word_dicts(NUM_COMMON_WORDS, NUM_MOST_ENGLISH_WORDS + (i * num_common_word_intervals), contents_filename, new_csv_path))
    base_json_path = "dump.json"
    paths = []
    for index, d in enumerate(words_to_check):
        with open(str(index) + base_json_path, 'w') as file:
            json.dump([posts, llm_responses, d], file)
        paths.append(str(index) + base_json_path)
    return paths

def format_posts(json_path: str):
    """
    Takes the json file produced by write_all_relevant_data, removes any words counted in each post and llm response
    that aren't included in the most common words and writes to a second json file.
    (Note: json_path should be the same as in write_all_relevant_data)
    """
    dicts = []
    with open(json_path, 'r') as file:
        dicts = json.load(file)
    words_to_check = set(dicts[2].keys())
    posts = dicts[0]
    llm_responses = dicts[1]
    for post in posts:
        # Convert the keys of the dictionary to a list to avoid RuntimeError during modification
        keys_to_remove = [key for key in post if key not in words_to_check]
        for key in keys_to_remove:
            del post[key]
    for response in llm_responses:
        # Convert the keys of the dictionary to a list to avoid RuntimeError during modification
        keys_to_remove = [key for key in response if key not in words_to_check]
        for key in keys_to_remove:
            del response[key]
    with open("second_" + json_path, 'w') as file:
        json.dump([posts, llm_responses, list(words_to_check)], file)
    
def calculate_p_value(posts: list, llm_responses: list, word: str):
    """
    Calculates the p-value for the for the observed difference in
    the mean number of times the given word appears across all posts and all llm responses.
    """
    post_nums = [post.get(word, 0) for post in posts]
    llm_response_nums = [response.get(word, 0) for response in llm_responses]
    n = len(post_nums)
    m = len(llm_response_nums)
    observed_diff = abs((sum(post_nums)/n - sum(llm_response_nums)/m))
    uni_sample = post_nums + llm_response_nums
    count = 0

    for x in range(10000):
        a_resample = [uni_sample[random.randint(0, len(uni_sample) - 1)] for i in range(n)]
        b_resample = [uni_sample[random.randint(0, len(uni_sample) - 1)] for i in range(m)]
        mua = sum(a_resample)/n
        mub = sum(b_resample)/m
        diff = abs(mua - mub)
        if diff >= observed_diff:
            count += 1
    return [abs(sum(post_nums)/n - sum(llm_response_nums)/m), float(count / 10000)]

def calculate_p_values(json_path: str = "dump.json"):
    """
    Calculates the p-values for the for the observed difference in
    the mean number of times each common word appears across all posts and all llm responses.
    """
    dicts = []
    with open("second_" + json_path, 'r') as file:
        dicts = json.load(file)
    posts = dicts[0]
    llm_responses = dicts[1]
    words_to_check = dicts[2]
    final_p_values = {}
    for word in words_to_check:
        final_p_values[word] = calculate_p_value(posts, llm_responses, word)
    return final_p_values

def calculate_p_values_from_scratch():
    """
    Brings together all other functions.
    """
    paths = write_all_relevant_data()
    p_values = []
    for path in paths:
        format_posts(path)
        p_values.append(calculate_p_values(path))
    combined_dict = {}
    for p_value_dict in p_values:
        combined_dict.update(p_value_dict)
    print(combined_dict)
    return combined_dict

if __name__ == "main":
    # run entire program
    calculate_p_values_from_scratch()