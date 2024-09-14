

import forum_api
#Arranges api result into needed format.

def post_transformation(post):
    # count = 0
    # for post in p_db:
    if "content" not in post.keys():
        print("No content:" + str(post["id"]))
        post["content"] = ""
    scores = forum_api.sentiment(str(post["content"]), post["author"]["username"])
    usr_obj = scores
    post["pos"] = scores["pos"]
    post["neg"] = scores["neg"]
    post["neu"] = scores["neu"]
    post["length"] = scores["length"]
    post["compound"] = scores["compound"]
    post["user_id"] = post["author"]["id"]
    post["username"] = post["author"]["username"]
    post["karma"] = post["author"]["karma"]
    try:
        del post["author"]
    except:
        pass
    return post

        
def thread_transformation(thread):
    if "content" not in thread.keys():
        print("No content:" + str(thread["id"]))
        thread["content"] = ""
    scores = forum_api.sentiment(str(thread["content"]), thread["author"]["username"])
    usr_obj = scores
    thread["pos"] = scores["pos"]
    thread["neg"] = scores["neg"]
    thread["neu"] = scores["neu"]
    thread["compound"] = scores["compound"]
    thread["user_id"] = thread["author"]["id"]
    thread["username"] = thread["author"]["username"]
    thread["karma"] = thread["author"]["karma"]
    try:
        del thread["author"]
    except:
        pass
    try:
        del thread["last_poster"]
    except:
        pass
    try:
        del thread["content_raw"]
    except:
        pass
    try:
        del thread["poll"]
    except:
        pass
    return thread
      
        
def content_cleaning(content):
    return content
    


