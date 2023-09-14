import requests
import json
import re
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from jira import JIRA

"""This script looks through all major/concentration
json files to find if any requirements have changed
over the year. If so, it raises a JIRA ticket with 
requirement change information
"""

#Should this detect CORE changes and, if so, should I flag each major for core changes?

#Modify the tolernance to ignore fluff (grammar changes, footnote numbering, etc)
#Determine what the cause of the diff is:
    #Course number change [*]
    #Major/Concentration deleted [*]
    #Degree credit hour changes [ ]

load_dotenv()
jira_api_key = os.getenv('JIRA_API_KEY')
course_prefixes = ["ACCT","ACTS","AHST","AMS","ARAB","ARHM","ARTS","ATCM","BA","BBSU","BCOM","BIOL","BIS","BLAW","BMEN","BPS","CE","CGS",
                   "CHEM","CHIN","CLDP","COMM","CRIM","CRWT","CS","DANC","ECON","ECS","ECSC","ED","EE","ENGR","ENGY","ENTP","ENVR","EPCS",
                   "EPPS","FILM","FIN","FREN","GEOG","GEOS","GERM","GISC","GOVT","GST","HIST","HLTH","HMGT","HONS","HUMA","IMS","IPEC","ISAE",
                   "ISAH","ISEC","ISIS","ISNS","ITSS","JAPN","KORE","LANG","LATS","LIT","MATH","MECH","MECO","MKT","MSEN","MUSI","NATS","NSC",
                   "OBHR","OPRE","PA","PHIL","PHIN","PHYS","PPOL","PSCI","PSY","REAL","RELS","RHET","RMIS","SE","SOC","SPAN","SPAU","STAT","THEA",
                   "UNIV","VIET","VPAS"]
major_json_path = "/home/runner/work/planner/planner/validator/degree_data"
#Extracts html from url and sends it to course extractor
def get_req_content(url: str) -> set[str]:
    response = requests.get(url)
    if(response.status_code == 200):
        return extract_courses(response.text)
    else:
        return set()

#Extracts the courses from each major and sends them to a set
def extract_courses(webData: str) -> set[str]:
    bs = BeautifulSoup(webData, features="html.parser")
    courses = set()
    course_elements = bs.find_all('a', href=True)

    for course_element in course_elements:
        course_name = course_element.text.strip()
        for prefix in course_prefixes:
            if prefix in course_name:
                courses.add(course_name)
    return courses

#Creates a ticket based on issue type, including URI and impacted courses in ticket
# C issue type = Course renamed/added/removed
# R issue type = Major/concentration removed
def createTicket(issueType: str, jira_connection: JIRA, URI: str, coursesImpacted: set[str]) -> None:
    description = ""
    if issueType == 'R':
        description += "The following major/concentration has been removed:\n"
    elif issueType == 'C':
        description += "The following course(s) have been renamed/added/removed:\n"
        description += str(coursesImpacted) + "\n"
    description += "URI: " + URI + "\n"
    description += "Major: " + URI.split("/")[-1] + "\n"
    # jira_connection.create_issue(
    #     project='NP',
    #     summary='Course requirement version changes',
    #     description=description,
    #     issuetype={'name': 'Task'}
    # )

#Establishes JIRA connection and ierates through each major for versioning issues
if __name__ == "__main__":
    jira_connection = JIRA(
        basic_auth=('planner@utdnebula.com', jira_api_key),
        server="https://nebula-labs.atlassian.net"
    )
    for majorReqJson in os.scandir(major_json_path):
        data = json.loads(open(f"validator/degree_data/" + majorReqJson.name, "r").read())
        catalog_uri=data["catalog_uri"]
        yearRegex = r'/(\d{4})/'
        result = re.search(yearRegex, catalog_uri)
        if result:
            match = str(int(result.group(1))+1)
            print(match)
            old=get_req_content(data["catalog_uri"])
            new=get_req_content(re.sub(yearRegex, f'/{ str(match) }/', data["catalog_uri"]))
            if len(new) == 0:
                createTicket('R', jira_connection, re.sub(yearRegex, f'/{ match }/', data["catalog_uri"]), set())
            else:
                createTicket('C', jira_connection, re.sub(yearRegex, f'/{ match }/', data["catalog_uri"]), (new-old).union(old-new))
            