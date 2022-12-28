from pathlib import Path
from bs4 import BeautifulSoup

from time import sleep
from traceback import print_exception
from sys import exc_info

import requests
import urllib.request

import csv
import logging

FORMAT = '[%(asctime)s] %(levelname)s - %(message)s'

logging.basicConfig(
        format=FORMAT,
        datefmt='%H:%M:%S',
        )

logging.getLogger().setLevel(logging.INFO)

__version__ = '0.0.5'

header = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.167 YaBrowser/22.7.3.822 Yowser/2.5 Safari/537.36',}
header_urllib = [('user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.167 YaBrowser/22.7.3.822 Yowser/2.5 Safari/537.36'),]


def main(username):
    
    logging.info('Script started')
    curdir = Path.cwd()
    user_projects = []
    filepath = None
    is_last_page_reached = False
    
    # Creating folders and file path
    try:
        user_folder = curdir / str(username) 
        user_folder.mkdir(parents=True, exist_ok=True)
    
        datapath = curdir / 'downloaded_projects.csv'
        
    except:
        logging.error("Can't create folder or get current path")
        
        return None
        
        
    # Loading data file 
    try:
        user_projects = read_db_file(datapath)
        logging.info("User projects info successfully downloaded")
         
    except:
        logging.error(f"Can't load saved user projects. Create new file by path {datapath}")
        with open(datapath, mode='w') as csvfile:
            csvfile.write('username, project_id\n')
    
    # Trying parse author projects   
    current_page = 1
    try:
        while not is_last_page_reached:
            logging.info(f"Fetching page {current_page} of {username}")

            session = get_session(header) 
            r = session.get(f'https://{username}.artstation.com/rss?page={current_page}')
            channel = BeautifulSoup(r.text, "lxml-xml").rss.channel
            tag_titles = channel.select("item > title")
            links = channel.select("item > link")
            
            all_titles =  [t.text for t in tag_titles]
            
            titles = []
            projects = []
            
            for title, link in zip(all_titles, links):
                if not 'blog' in link.text:
                    titles.append(title)
                    projects.append(link.text.split('/')[-1])
                
            page_num_projects = len(projects)
            

            is_last_page_reached = page_num_projects < 49 # Each full page contains 50 projects. If it has less than 50, it is the last page

            for index in range(len(projects)):

                    project_name    = titles[index]
                    project_hash_id = projects[index]

                    logging.info(f"Found project - '{project_name}' with hash_id {project_hash_id}")

                    # Have we already downloaded this post?
                    if not is_post_already_saved(username, project_hash_id, user_projects):

                        # Fetch information about the project
                        project_info = requests.get(f"https://www.artstation.com/projects/{project_hash_id}.json", headers=header)
                        assets = project_info.json()["assets"]

                        # For each asset in the project
                        for asset in assets:
                            asset_type = asset["asset_type"]
                            asset_position = asset["position"]

                            # If the asset is an image
                            if asset_type == "image":
                                asset_image_url = asset["image_url"]

                                # Generate a download filename
                                filename = project_name[:60].lower().replace(' ', '_').replace(':', '') + "_" + project_hash_id + "_" + str(asset_position) + "." + extension_from_url(asset_image_url)
                                filepath = user_folder / filename

                                logging.info(f"Found image in project - '{project_name}' [hash_id {project_hash_id}] at position {asset_position}.")
                                logging.info(f'Downloading to {filepath}')

                                # Download it
                                download_media(asset_image_url, filename=filepath)
                                sleep(1)
                                    
                                    

                        # After downloading all assets, mark the project as downloaded.
                        write_post_in_db(username, project_hash_id, user_projects)

            if not is_last_page_reached:
                current_page = current_page + 1

                        
    except:
        logging.error(f"Can't fetching page {current_page} of {username}")
        exception_info = exc_info()
        with open('bug_report.log', mode='w') as report_file:
            print_exception(*exception_info, file=report_file)
        
        return False
   
    return True
                
                        
def extension_from_url(url):
    rurl = url[::-1]
    rext = ""
    for c in rurl:
        if c != '.':
            rext = rext + c
        else:
            break

    ext = rext[::-1]

    # Now remove the get parameters
    foundQuestionmark = False
    actualExt = ""
    for c in ext:
        if c == '?':
            foundQuestionmark = True

        if not foundQuestionmark:
            actualExt = actualExt + c

    return actualExt

def download_media(url, filename):
    
    # Prepare and execute query to download images
    try:
        opener = urllib.request.build_opener()
        opener.addheaders = header_urllib
        urllib.request.install_opener(opener)
        source = urllib.request.urlretrieve(url, filename=filename)
        logging.info('Download successfully!')
        print('', end='\n\n')
        
    except:
        logging.error('Download finished with error.\nMore information you can see in .log file')
        with open(f'downloading_errors_{username}.log', mode='a') as logfile:
            logfile.write(f'Failed to download file by url - {url}\n')
        
        
def is_post_already_saved(username, project_hash_id, user_projects):
    return [username, project_hash_id] in user_projects


def write_post_in_db(username, project_hash_id, user_projects):
    try:
        with open('downloaded_projects.csv', 'a', newline='\n') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow([username, project_hash_id])
        
    except:
        logging.error("Can't write new data in file")

        
def get_session(headers):
    session = requests.Session()
    session.headers = headers
    
    return session

def read_db_file(filename):
    user_projects = []
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            user_projects.append(row)
            
    return user_projects

if __name__ == "__main__":
    first_input = input('Enter username or url:\n')
    username = None
    
    if 'artstation' in first_input:
        username = first_input.split('/')[-1]
    else:
        username = first_input
        
    
    print('\n')
    complete_status = main(username)
    
    if complete_status:
        logging.info("Downloading finished")
    else:
        logging.info(f"Downloading with error. More info in bug_report_{username}.log")
    input('Tap Enter to close program....')
                        