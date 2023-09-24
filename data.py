
from supabase import Client,create_client
import time
import pandas as pd
from datetime import datetime
import pytz
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVwenBzZXJxbmhid2ZwZnFhcW1xIiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTM5Mjg5MjUsImV4cCI6MjAwOTUwNDkyNX0.p9B-v6HNzS7yqClhKI1BNi5DByuIfDvpLPBpRS2O_MQ'
url = 'https://epzpserqnhbwfpfqaqmq.supabase.co'
client = create_client(url,key)
timezone = pytz.timezone("Asia/Ho_Chi_Minh")  # Replace with your desired timezone

def write(s):
    time = datetime.now( ).astimezone(tz = timezone).strftime('%Y-%m-%d %H:%M:%S %z')

    client.table('notes').insert({'content':s,'time':time}).execute()
def getwrite():
    return pd.DataFrame(client.table('notes').select("*").execute().data)
def blog(s):
    time = datetime.now( ).astimezone(tz = timezone).strftime('%Y-%m-%d %H:%M:%S %z')
    client.table('blog').insert({'content':s,'time':time}).execute()
def getblog():
    return pd.DataFrame(client.table('blog').select("*").execute().data)