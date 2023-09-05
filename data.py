
from supabase import Client,create_client
import time
from datetime import datetime

key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVwenBzZXJxbmhid2ZwZnFhcW1xIiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTM5Mjg5MjUsImV4cCI6MjAwOTUwNDkyNX0.p9B-v6HNzS7yqClhKI1BNi5DByuIfDvpLPBpRS2O_MQ'
url = 'https://epzpserqnhbwfpfqaqmq.supabase.co'
client = create_client(url,key)

def write(s):
    client.table('notes').insert({'content':s,'time':datetime.now().strftime('%Y-%m-%d %H:%M:%S')}).execute()
