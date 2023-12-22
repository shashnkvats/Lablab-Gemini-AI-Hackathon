PROMPT_SUMMARY = """
In the give text, what is the location, website and email id of incluencer? Give output in following format
example :
prompt - Building rockets 📍NY abc@rockets.com
{
  "location": "New York",
  "country": "USA",
  "email": "abc@rockets.com",
  "website": ""
}
"""

PROMPT_HASHTAG = """
Given below are some tags. Give me 5 most frequent tags in the list.
example :
["hashtag1", "hashtag3] ["hashtag1", "hashtag2"] ["hashtag2", "hashtag4"]
output format:
["#hashtag1', "#hashtag2"]
"""

PROMPT_CAPTIONS = """
Given are the captions from an influencer's instagram post. Can you summaries it giving details about kinds of post, the theme behind it.
"""

PROMPT_LOCATION = """
Give a one word answer. Which city is the person based in? Return empty string if no info is available.
"""

PROMPT_COUNTRY = """
Give a one word answer. Which country is the person based in? Return empty string if no info is available.
"""

PROMPT_EMAIL = """
Give a one word answer. How can the person be contacted? Return empty string if no info is available.
"""

PROMPT_WEBSITE = """
Give a one word answer. What is the website of the person? Return empty string if no info is available.
"""