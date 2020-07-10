import logging
import datetime
import re
import json

import jinja2
import requests
import pendulum
import panflute as pf

from redmineapitools.single_instance import RedmineAPIWrapper, get_custom_field_value_by_name
from pycryptpad_tools.padapi import PadAPI
logging.getLogger("requests").setLevel(logging.DEBUG)


# In[6]:


def find_first_by_name(name, seq):
    return next(filter(lambda t: t.name == name, seq))

def to_iso_datestr(dt):
    return dt.strftime("%Y-%m-%d")

def to_redmine_datestr(dt):
    return to_iso_datestr(dt)

def to_localized_datestr(dt):
    return dt.strftime("%d.%m.%Y")

def get_open_issues(tracker_id, project_id):
    return list(redmine.api.issue.filter(project_id=project_id, tracker_id=tracker_id))

def make_todo_entry(issue):
    return f"[] #{issue.id}: {issue.subject}"


# In[7]:


pad_api = PadAPI(cryptpad_url, headless=False)
redmine = RedmineAPIWrapper(redmine_url, key=redmine_key, admin_key=redmine_admin_key, version="4.1.1")
redmine_status_offen = find_first_by_name("Offen", redmine.issue_status).id
redmine_status_zg = find_first_by_name("Zu genehmigen", redmine.issue_status).id
redmine_status_erledigt = find_first_by_name("Erledigt", redmine.issue_status).id
redmine_tracker_todo = find_first_by_name("To-Do", redmine.trackers).id
redmine_tracker_protokoll = find_first_by_name("Protokoll", redmine.trackers).id


# ## Termin

# In[8]:


event_dt = pendulum.datetime(year=2020, month=5, day=8, hour=21, minute=0, tz="Europe/Berlin")
topics = [
    "Streichungsanträge BPT 20.1",
    "Stand BEO-Software/Antragsportal"
]
timedelta = dict(hours=1)
event_title = "AG Antragsprozess"
number = 30
tags = ["ag-antragsprozess"]
datestr=to_localized_datestr(event_dt)
subject = f"{event_title} - {number}. Treffen {datestr}"
(subject, event_dt.to_iso8601_string())


# ### Protokoll-Pad anlegen

# In[9]:


api = pad_api
api.start_chrome_driver()
api.open_pad(pad_template_key)
pad_template = api.get_pad_content()


# In[10]:


tasks = [make_todo_entry(issue) for issue in get_open_issues(redmine_tracker_todo, redmine_project)]
start_time = event_dt.strftime("%H:%M")
end_time = event_dt.add(**timedelta).strftime("%H:%M")
template = jinja2.Template(pad_template)
pad_content = template.render(start_time=start_time,
                              end_time=end_time,
                              date=to_localized_datestr(event_dt),
                              number=number,
                              topics=topics,
                              tasks=tasks)
Markdown(pad_content)


# In[11]:


with pad_api as api:
    padinfo = api.create_pad(pad_content)


# In[12]:


pad_url = padinfo["url"]
pad_url


# ### Protokoll-Ticket anlegen

# In[13]:


last_protocol_issue = get_open_issues(redmine_tracker_protokoll, redmine_project)[0]


# In[14]:


protocol_ticket_description_tmpl = "Pad: {pad_url}\n\n"
issue = redmine.api.issue.new()
issue.project_id = redmine_project
issue.tracker_id = redmine_tracker_protokoll
issue.start_date = to_redmine_datestr(event_dt)
issue.subject = subject
issue.description = protocol_ticket_description_tmpl.format(pad_url=pad_url)
redmine.set_custom_fields_by_name(issue, {"Padlink (schreiben)": pad_url})


# In[15]:


issue.save()


# In[16]:


redmine.api.issue_relation.create(issue_id=issue.id, issue_to_id=last_protocol_issue.id, relation_type="relates")


# ### Discourse-Termin anlegen

# In[17]:


event = {}
location = {}

event["all_day"] = False
event["start"] = event_dt.to_iso8601_string()
event["end"] = event_dt.add(**timedelta).to_iso8601_string()
location["countrycode"] = "de"
location["geo_location"] = {}
location["name"] = "Mumble NRW, Raum Bund -> Zweig der innerparteilichen Arbeit -> AG Antragsprozess"

topics_text = "\n".join(f"* {to}" for to in topics)

discourse_post_content = f"""
Die AG Antragsprozess trifft sich im Mumble ab 20:30 Uhr. Wir fangen pünktlich um 21 Uhr mit dem offiziellen Teil an und hören um 22 Uhr auf.
Wir freuen uns auf Zuhörer und Leute, die gerne mitarbeiten wollen.

## Themen

{topics_text}

## Protokoll

{pad_url}

## Alle Protokolle

Die Protokolle werden nach der Sitzung im Bundesredmine archiviert. Die Protokolle für kommende Sitzungen sind dort auch zu finden:

[Liste aller Protokolle der AG Antragsprozess](https://redmine.piratenpartei.de/projects/ag-antragsprozess/issues?query_id=188)

[Alle Protokolle der AG Antragsprozess im Volltext](https://redmine.piratenpartei.de/projects/ag-antragsprozess/issues?query_id=189)
"""

Markdown(discourse_post_content)


# In[18]:


headers = {
    'accept': 'application/json',
    'api-key': discourse_api_key,
    'api-username': discourse_username
}
req = dict(raw=discourse_post_content,
           category=discourse_category_id,
           title=subject,
           event=event,
           location=location,
           tags=tags)

requests.post(f"{discourse_url}/posts.json", json=req, headers=headers)


# ### Pad nach Redmine übertragen

# In[17]:


open_protocol_issues = get_open_issues(redmine_tracker_protokoll, redmine_project)
for iss in open_protocol_issues:
    print(f"{redmine_url}/issues/{iss.id}", iss.subject, get_custom_field_value_by_name(iss, "Padlink (schreiben)"))


# In[18]:


protocol_issue = open_protocol_issues[0]
protocol_issue


# In[43]:


pad_url = get_custom_field_value_by_name(protocol_issue, "Padlink (schreiben)")
pad_key = pad_url.split("/")[-2]


# In[44]:


with pad_api as api:
    api.open_pad(pad_key)
    pad_content = api.get_pad_content()


# In[45]:


def pf_remove_mumble_link(elem, doc):
    if isinstance(elem, pf.Link) and elem.url.startswith("mumble://"):
        return []

def pf_toc(elem, doc):
    if isinstance(elem, pf.Para) and len(elem.content) == 1:
        ff = elem.content[0]
        if isinstance(ff, pf.Str) and ff.text == "[TOC]":
            ff.text = "{{toc}}"

def issue_subject_from_todo_line(item_content):
    return "".join(pf.stringify(e) for e in item_content[3:]).strip()

def try_issue_id(text):
    try:
        return int(text.strip("# :"))
    except:
        pass

def find_todo_items(elem, doc):
    to_create = doc.issues["create"]
    to_update = doc.issues["update"]
    to_close = doc.issues["close"]

    if isinstance(elem, pf.ListItem):
        item_content = elem.content[0].content
        if isinstance(item_content[0], pf.Str) and len(item_content) > 2:
            checkbox = item_content[0].text
            issue = item_content[2].text
            if checkbox == "[]" and issue == "todo:":
                subject = issue_subject_from_todo_line(item_content)
                if subject:
                    to_create[subject] = "To-Do"
            elif checkbox == "[]" and issue.startswith("#"):
                issue_id = try_issue_id(issue)
                if issue_id:
                    to_update[issue_id] = issue_subject_from_todo_line(item_content)
            elif checkbox == "☒" and issue.startswith("#"):
                issue_id = try_issue_id(issue)
                if issue_id:
                    to_close[issue_id] = issue_subject_from_todo_line(item_content)

def convert_pad_content(pad_content):
    doc = pf.convert_text(pad_content, standalone=True)
    doc.walk(pf_remove_mumble_link)
    doc.walk(pf_toc)
    doc.issues = {
        "create": {},
        "update": {},
        "close": {}
    }
    doc.walk(find_todo_items)
    content = pf.convert_text(doc, input_format="panflute", output_format="markdown", extra_args=["--wrap=preserve"])
    return content, doc.issues


# In[46]:


content, issues = convert_pad_content(pad_content)
Markdown(content)


# In[47]:


issues


# In[48]:


protocol_issue.description = content
protocol_issue.status_id = redmine_status_zg
protocol_issue.save()


# In[49]:


for subject, tracker in issues["create"].items():
    issue = redmine.api.issue.new()
    issue.project_id=redmine_project
    issue.tracker_id=redmine_tracker_todo
    issue.subject=subject
    issue.save()
    try:
        redmine.api.issue_relation.create(issue_id=issue.id, issue_to_id=protocol_issue.id, relation_type="relates")
    except:
        pass


# In[50]:


for issue_id, subject in issues["update"].items():
    issue = redmine.api.issue.get(issue_id)
    if issue.project.id != protocol_issue.project.id:
        print("do not touch ;)")
        continue
    issue.subject = subject
    issue.save()
    try:
        redmine.api.issue_relation.create(issue_id=issue.id, issue_to_id=protocol_issue.id, relation_type="relates")
    except:
        pass


# In[51]:


for issue_id, subject in issues["close"].items():
    issue = redmine.api.issue.get(issue_id)
    if issue.project.id != protocol_issue.project.id:
        print("do not touch ;)")
        continue
    issue.subject = subject
    issue.status_id = redmine_status_erledigt
    issue.save()
    try:
        redmine.api.issue_relation.create(issue_id=issue.id, issue_to_id=protocol_issue.id, relation_type="relates")
    except:
        pass


# In[52]:


with pad_api as api:
    api.open_pad(pad_key)
    api.set_pad_content(f"Protokoll abgeschlossen, siehe: {redmine_url}/issues/{protocol_issue.id}")
