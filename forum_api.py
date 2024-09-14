#https://api.torn.com/v2/forum/?selections=categories&key=

#https://api.torn.com/v2/forum/?selections=threads&key=&limit=100&sort=DESC&to=1551512

#https://api.torn.com/v2/forum/?selections=thread&key=&id=16369757
#https://api.torn.com/v2/forum/?selections=thread&key=&id=16414239

#https://api.torn.com/v2/forum/?selections=posts&key=&offset=0&cat=plain&id=16414239
import requests
import time
import datetime
import math
import forum_trans
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import string
from collections import defaultdict
import ConfigSetup

config = ConfigSetup.read_cfg()
api_root_forum = "https://api.torn.com/v2/forum/?selections="

#### API Keys here. Comma seperated as strings. ####
#### Public key only. Runs at 80 calls per minute. ####
api_keys = [] 
           
api_index = 0
gbl_time = time.time()

try:
    with open(str(config['main']['thread_file']) + ".json", 'r') as f:
        thd_obj = json.load(f)
except:
    thd_obj = {}
try:
    with open(str(config['main']['post_file']) + ".json", 'r') as f:
        pst_obj = json.load(f)
except:
    pst_obj = {}
try:
    with open(str(config['main']['user_file']) + ".json", 'r') as f:
        usr_obj = json.load(f)
except:
    usr_obj = {}



def get_forum_categories(key):
    #key = "NFn4l8NpPSaBuAkN"

    str_url = api_root_forum + "categories&key="
    
    response = get_api_resp(str_url, key)["categories"]
    if response == False:
        return False
    return response

#Gets the thread list back to the specified starting time.
def get_forum_threads(key, unix_from, unix_to):
    global thd_obj
    
    #key = "NFn4l8NpPSaBuAkN"
    counts = {}
    url_to = unix_to
    count_threads = 0
    while True:
        
        counts["Threads"] = 0
        counts["Updates"] = 0
        counts["Inserts"] = 0
        counts["Skips"] = 0
        if url_to <= unix_from:
            break
        url_from = url_to - 21600
        str_url = api_root_forum + "threads&from=" + str(url_from) + "&to=" + str(url_to) + "&limit=100&sort=DESC&key="
        url_to = url_from
        response = get_api_resp(str_url, key)["threads"]
        if response == False:
            return False
        #Exits if empty
        print("Time block: " + str(datetime.datetime.utcfromtimestamp(int(url_to)).strftime('%Y-%m-%d %H:%M:%S')) + " Responses: " + str(len(response)))
        counts["Threads"] += len(response) #This may be a bit off due to slight overlap
        for thread in response:
            if str(thread["id"]) in thd_obj.keys():
                existing_rec = thd_obj[str(thread["id"])]  
                if int(existing_rec["last_post_time"]) < int(thread["last_post_time"]):
                    #print(str(int(existing_rec["last_post_time"]))+" < " + str(int(thread["last_post_time"])))
                    count_threads += 1
                    if int(thread["posts"]) != int(existing_rec["posts"]):
                        #print(str(int(thread["posts"]))+" != " + str(int(existing_rec["posts"])))
                        get_forum_posts(key, thread["id"], thread["posts"], thread["posts"]-existing_rec["posts"], thread["forum_id"])
                        
                    str_url = api_root_forum + "thread&id=" + str(thread["id"]) + "&key="
                    try:
                        thread_details = get_api_resp(str_url, key)["thread"]
                    except:
                        continue
                    thd_obj[thread["id"]] = forum_trans.thread_transformation(thread_details)
                    
                    counts["Updates"] += 1
                
                #Exists (not updated)
                else:
                    counts["Skips"] += 1
            #New
            else:
                #print("Thread not in keys")
                count_threads += 1
                get_forum_posts(key, thread["id"], thread["posts"], thread["posts"], thread["forum_id"])
                str_url = api_root_forum + "thread&id=" + str(thread["id"]) + "&key="
                try:
                    thread_details = get_api_resp(str_url, key)["thread"]
                except:
                    continue
                thd_obj[thread["id"]] = forum_trans.thread_transformation(thread_details)
                counts["Inserts"] += 1
                #print("Insert: " + str(thread_details["id"]))
            
        if count_threads >= 1000:
            dump_results()
            count_threads = 0
        now = datetime.datetime.now()
        print(str(now.time()) + "  Threads: " + str(counts))
        
    dump_results()
    return counts

#Gets the specific posts under each forum thread
#Something is wrong with the counting logic, there are many duplicates in the responses when there should be none.
def get_forum_posts(key, thread_id, pst_cnt, new_posts, forum_id):
    global pst_obj
    counts = {}
    counts["Posts"] = 0
    counts["Updates"] = 0
    counts["Inserts"] = 0
    counts["Skips"] = 0

    offset_max = math.ceil(pst_cnt/20)
    offset_min = math.ceil((pst_cnt-new_posts)/20)-1
    if  offset_min == -1:
        offset_min = 0
    for offset in range(offset_min,offset_max):
        str_url = api_root_forum + "posts&offset=" + str(offset*20) + "&cat=plain&id=" + str(thread_id) + "&key="
        #print(str_url + key)
        try:
            response = get_api_resp(str_url, key)["posts"]
        except:
            continue
        for post in response:
            post["thread_id"] = thread_id
            post["forum_id"] = forum_id
            post["post_id"] = post["id"]
            post["id"] = str(forum_id) + "_" + str(thread_id) + "_" + str(post["id"])
            #Check for new entry
            if post["id"] in pst_obj.keys():
                if post["is_edited"] == "true":
                    pst_obj[post["id"]] = forum_trans.post_transformation(post)
                    counts["Updates"] += 1
                else:
                    counts["Skips"] += 1
                    #print("Post Exists: " + str(post["id"]))
            else:
                pst_obj[post["id"]] = forum_trans.post_transformation(post)
                counts["Inserts"] += 1
                #print("Post Insert: " + str(post["id"]))
    #print("Posts: " + str(counts))
    return counts          
                
def get_api_resp(str_url, key):
    global api_keys
    global api_index
    global gbl_time
    err_count = 0

    err = True
    while err == True:
        if api_index >= len(api_keys):
            api_index = 0
        req_url = str(str_url) + api_keys[api_index]
        api_index += 1
        err = True
        try:
            r = requests.get(req_url)
            run_time = time.time() - gbl_time
            if run_time < .8/len(api_keys):
                time.sleep((.8/len(api_keys))-run_time)
            gbl_time = time.time()
        except:
            err = True
            time.sleep(10)
        try:
            response = r.json()
            err = False
        except:
            print("Error in API call.")
            err = True
            time.sleep(10)
            
        try:
            print("Error:" + str(r.json()["error"]["error"]))
            err = True
            if str(r.json()["error"]["error"]) == "Incorrect ID":
                return False
            if str(r.json()["error"]["error"]) == "Backend error occurred, please try again":
                print(req_url)
                return False
            if str(r.json()["error"]["error"]) == "Incorrect key":
                print("Popping: " + str(api_keys[api_index-1]))
                del api_keys[api_index-1]
            if str(r.json()["error"]["error"]) == "Too many requests":
                continue
                
            time.sleep(10)
        except:
            pass
            
        if err == False:
            return response
        else:
            err_count += 1
            print("Error Count: " + str(err_count))
            #Disabled to continue overnight despite API errors
            # if err_count > 10:
            #     print("Error retrieving API. Exiting")
            #     return False
            
def dump_results():
    global thd_obj
    global pst_obj
    global usr_obj
    start = time.time()
    success = False
    try:        
        with open(str(config['main']['thread_file']) + ".json", 'w') as f:
            json.dump(thd_obj, f, indent=4)
        success = True
    finally:
        if not success:
            print("Thread file was not written.")
    success = False
    try:
        with open(str(config['main']['post_file']) + ".json", 'w') as f:
            json.dump(pst_obj, f, indent=4)
        success = True
    finally:
        if not success:
            print("Post file was not written.")
    success = False
    try:
        with open(str(config['main']['user_file']) + ".json", 'w') as f:
            json.dump(usr_obj, f, indent=4)
        success = True
    finally:
        if not success:
            print("User file was not written.")
    end = time.time()
    length = end - start
    print("Writing took " + str(length) + " seconds.")
        
def sentiment(content, user):
    global usr_obj
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(str(content))
    
    # Remove punctuation
    translator = str.maketrans('', '', string.punctuation)
    clean_content = content.translate(translator)
    
    words = clean_content.lower().split()
    scores["length"] = len(words)

    if user not in usr_obj:
            usr_obj[user] = {}

    for word in words:
        if any(char.isdigit() for char in str(word)):
            continue
        if word not in usr_obj[user]:
            usr_obj[user][word] = 0
        usr_obj[user][word] += 1
    
    #print(clean_content)
    #print(scores)
    return scores