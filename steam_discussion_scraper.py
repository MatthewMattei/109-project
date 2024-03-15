"""
This file defines methods to scrape Steam discussion posts and comments for the purpose
of creating a dataset representative of the text written by a given game's Steam community.

By: Matthew Mattei
Date: 3/14/24
Credits: ChatGPT was used for planning and writing elements of the code in this file
"""

# Imports
from bs4 import BeautifulSoup
import csv
import re
import requests
from collections import Counter

REMOVE_EXTRA_CHARS_RE = r'[\[\]\n\r\t?\".,\/#!$%\^&\*;:{}=\-_`~()\[\]]'

def url_to_soup(url: str):
    """
    Helper function to convert url to parsed html content.
    """

    # Send a GET request to the URL
    response = requests.get(url)

    if (response.status_code != 200):
        ValueError("Response status code must be 200 to scrape page.")

    # Parse the HTML content of the page
    return BeautifulSoup(response.content, 'html.parser')

def scrape_for_posts(url: str):
    """
    Performs the overarching scrape on the discussion forum specified by the url to find all discussion posts.
    The url should link to the 0th page of the general discussions for a given Steam game.
    Example of a properly formatted URL: https://steamcommunity.com/app/1055540/discussions/0/
    Only the '1055540' portion should be different for a valid url.
    """

    # Used to iterate through discussion post pages, number indicates page index so it starts at 1
    index = 1
    url += "?fp=" + str(index)

    # List of links to discussion posts
    links = []

    still_posts_to_find = True

    while(still_posts_to_find):

        soup = url_to_soup(url)

        # Find all elements with class "forum_topic_overlay", which is the class name for each discussion post link's tag
        elements = soup.find_all('a', class_='forum_topic_overlay')

        if not elements:
            still_posts_to_find = False
            break

        # Extract and print the text and href attribute of these elements
        links += [element['href'] for element in elements]
        
        # Go to next page
        index += 1
        url = url[:url.rfind("=") + 1] + str(index)
        
    return links

def scrape_for_content(url: str, filter_non_responsive: bool = True):
    """
    Performs the scrape for discussion post text. Generally, should be given urls found by scrape_for_posts
    but can also be used to scrape individual disucssion post link given by user, just less likely to produce
    ideal results due to filtering.
    Example url format: https://steamcommunity.com/app/1055540/discussions/0/1639792569850161500/
    """

    # Used to iterate through discussion pages, number indicates page index so it starts at 1
    index = 1
    url += "?ctp=" + str(index)

    # List of post/comment content
    contents = []

    # OP Topic and Content
    op = []

    # Makes sure attempt to filter out unreponsive posts only happens once
    checked_responsiveness = False
    saved_title = False

    still_posts_to_read = True

    while (still_posts_to_read):

        soup = url_to_soup(url)

        # Find all <a> tags and remove them (to remove links that are unnecessary to dataset)
        for a_tag in soup.find_all('a'):
            a_tag.extract()

        # Find all comment quotes and remove them (to avoid doublecounting)
        for blockquote_tag in soup.find_all('blockquote'):
            blockquote_tag.extract()
        
        if filter_non_responsive and not checked_responsiveness:
            # Find the tag with the class name "topicstats_value" and extract the text, second value will give number of responses to post
            tags_with_class = soup.findAll(class_='topicstats_value')
            if int(tags_with_class[1].get_text()) <= 0:
                print("Filtered discussion post without replies.")
                break
            checked_responsiveness = True
        
        if not saved_title:
            # Save original post title
            op.append(soup.find(class_="topic").get_text())
            # Save original post content
            op_content = soup.find(class_="forum_op").find(class_="content").get_text(separator=' ')
            op.append(op_content)
            saved_title = True
        
        # add in all comment contents
        comments = soup.findAll(class_="commentthread_comment_text")

        if not comments:
            still_posts_to_read = False
            break

        contents += [comment.get_text(separator=' ') for comment in comments]

        # Go to next page
        index += 1
        url = url[:url.rfind("=") + 1] + str(index)
    
    # Process and clean scrapped text
    op = [re.sub(REMOVE_EXTRA_CHARS_RE, '', content.replace("/", " ")).strip().lower() for content in op]
    contents = [re.sub(REMOVE_EXTRA_CHARS_RE, '', content.replace("/", " ")).strip().lower() for content in contents]
    
    return op, contents

def combined_scrape(url: str, contents_filename: str = "words.csv", op_filename: str = "op.csv"):
    """
    Combines scrape_for_posts and scrape_for_content to scrape all discussion threads and posts for a Steam
    game's "General Discussions".
    Example of a properly formatted URL: https://steamcommunity.com/app/1055540/discussions/0/
    Only the '1055540' portion should be different for a valid url.
    Filename must be a valid csv filename to write correctly.
    Example of filename: words.csv
    """

    links = scrape_for_posts(url)

    total_ops = []
    total_contents = []
    reply_contents = []

    for link in links:
        op_content, thread_content = scrape_for_content(link)
        if not op_content or not thread_content:
            continue

        total_ops.append(op_content)

        words = [content.split() for content in thread_content]
        for sublist in words:
            total_contents += sublist
            reply_contents.append(Counter(sublist))
    
    # Write the list of comments contents to the CSV file
    with open(contents_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(total_contents)
    
    # Write the list of op contents to the CSV file
    with open(op_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        for op in total_ops:
            writer.writerow(op)

    print(str(len(total_contents)) + " words successfully scraped and writen to " + contents_filename)
    return reply_contents