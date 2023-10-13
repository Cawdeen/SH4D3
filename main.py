import asyncio
import openai
import discord
import random
import ingest
import functools
import typing
import os
import re
import io

from datetime import datetime, date, time, timedelta
from llama_index.llms import OpenAI
from dotenv import load_dotenv
load_dotenv()
#for embedded RAG query
OpenAI.api_key = os.getenv("OPENAI_API_KEY")
from llama_index import ServiceContext, set_global_service_context
from llama_index import StorageContext, load_index_from_storage

from pytz import timezone
from discord import app_commands

TOKEN = os.getenv("TOKEN")

########################## RAG stuff

# define LLM
llm = OpenAI(model="gpt-3.5-turbo", temperature=0.6, max_tokens=900)

# configure service context
service_context = ServiceContext.from_defaults(llm=llm, chunk_size=900, chunk_overlap=20)
set_global_service_context(service_context)


storage_context = StorageContext.from_defaults(persist_dir="index")#load index
index = load_index_from_storage(storage_context)
query_engine = index.as_query_engine(similarity_top_k=2)#build query engine
chat_engine = index.as_chat_engine(chat_mode='context', similarity_top_k=2)#build chat engine
chat_countdown = 0 #countdown timer to reset chat in minutes
chat_countdown_max = 15
############################# openai
#for openai API
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.Model.list()

#basic who are you prompt
startingprompt = "You are a droid named SH4D3 in a Star Wars video game. You're in Mos Pelgo, Tatooine. Be a little sarcastic, keep responses brief. Use emoji sparingly. Include some static and stuttering in your responses since you're a droid. "
eventsList = []
prompt = ''
postMorning = time(8,0,0)
reloadMorning = time(7,50,0)
reloadNight = time(16,0,0)
percent_alert_yes = 30 #percent (0-100) that will be yes for alert rolls
min_alert_seconds = 18000 #min seconds to wait until an alert roll (18000 is 5hrs)
max_alert_seconds = 54000 #max seconds to wait until an alert roll (54000 is 15hrs)
eventsToday = False
announcementsToday = False
intents = discord.Intents.all()

test_channelID = 1156939619225587733 #Moss droid test channel
tempest_main_channelID = 941946605479817218 #Tempest discord main channel
tempest_event_channelID = 955640862166110249 #Tempest discord events channel

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=1123270531790155916)) #Moss server
    taskMorningBrief = asyncio.create_task(post_timer())
    taskContextTimer = asyncio.create_task(context_timer())
    taskChatReset = asyncio.create_task(chat_reset_timer())
    taskRandomAlertTimer = asyncio.create_task(random_alert_scheduler())
    print('The bot is ready')
    await taskMorningBrief #posts a morning announcement
    await taskContextTimer #reloads context every 12 hours
    await taskChatReset #timer to reset chats
    await taskRandomAlertTimer #timer to post random alerts


async def load_context():
    global index, query_engine,chat_engine
    print('loading context')
    #clear the events file
    fp = open('data/events.txt', "w", encoding="utf-8")
    fp.close()
    #get text for announcements and events, and combine them with a title
    announcementsTxt = await ingest_announcements()
    eventsTxt = await ingest_events()
    announceEventsTxt = 'Morning Brief - Announcements and Events\n'+announcementsTxt+eventsTxt
    #write the updated events annoucements to the file
    file = io.open('data/events.txt', "w", encoding="utf-8")
    file.write(announceEventsTxt)
    file.close()
    
    #Create and save the index
    ingest.ingest()

    #load the index
    storage_context = StorageContext.from_defaults(persist_dir="index")
    index = load_index_from_storage(storage_context)
    query_engine = index.as_query_engine(similarity_top_k=2) #build the query engine
    chat_engine = index.as_chat_engine(chat_mode='context', similarity_top_k=2)#build chat engine
    print('finished loading context')

#random safety reminder
async def pick_safety_reminder():
    myList = []
    file = open('rp/SafetyReminders.txt', "r", encoding="utf-8")
    str = file.read()
    myList = str.splitlines()
    choice = random.choice(myList)
    return choice

#for picking a random heads up story
async def pick_story():
    myList = []
    file = open('rp/HeadsUpStories.txt', "r", encoding="utf-8")
    str = file.read()
    myList = str.splitlines()
    choice = random.choice(myList)
    return choice

#pick weather
async def pick_weather():
    myList = []
    file = open('rp/Weather.txt', "r", encoding="utf-8")
    str = file.read()
    myList = str.splitlines()
    choice = random.choice(myList)
    return choice    

async def weather_report(channel):
    global startingprompt, eventsToday, announcementsToday
    day = ''
    date = datetime.now()
    date = date.astimezone(timezone('US/Eastern'))
    daynum = date.weekday()
    if daynum == 0:
        day = 'Monday'
    elif daynum == 1:
        day = 'Tuesday'
    elif daynum == 2:
        day = 'Wednesday'
    elif daynum == 3:
        day = 'Thursday'
    elif daynum == 4:
        day = 'Friday'
    elif daynum == 5:
        day = 'Saturday'
    else:
        day = 'Sunday'
    weatherPrompt = await pick_weather()
    if announcementsToday == True and eventsToday == True: #big brief because both announce and events. Give shortrt weather report.
        txt=startingprompt + 'SH4D3, Today is ' +day+ '. Greet the citizens of Mos Pelgo, give us a unique but short weather forecast based on this: \n' + weatherPrompt + '\n After the weather report dont say goodbye or anything yet.'
    elif announcementsToday == True and eventsToday == False:
        txt=startingprompt + 'SH4D3, Today is ' +day+ '. Greet the citizens of Mos Pelgo, give us a unique weather forecast based on this: \n' + weatherPrompt + '\n After the weather report dont say goodbye or anything yet.'
    elif announcementsToday == False and eventsToday == True:
        txt=startingprompt + 'SH4D3, Today is ' +day+ '. Greet the citizens of Mos Pelgo, give us a unique weather forecast based on this: \n' + weatherPrompt + '\n After the weather report dont say goodbye or anything yet.'
    else: #both are false give a nice long report
        txt=startingprompt + 'SH4D3, Today is ' +day+ '. Greet the citizens of Mos Pelgo, tell a funny story about your morning and give a unique weather forecast based on this: \n' + weatherPrompt + '\n After the weather report dont say goodbye or anything yet.'

    response = chat_engine.chat(txt)
    return response
    #await c_channel.send(response)

    # response = openai.Completion.create(
    #     model="gpt-3.5-turbo-instruct",
    #     prompt=startingprompt + 'SH4D3, Today is ' +day+ '. Greet the citizens of Mos Pelgo and give us a weather forecast for today. Dont say goodbye yet though.',
    #     max_tokens = 1000
    #     )
    # c_channel = client.get_channel(1156939619225587733) #Droid test channel
    # message = response['choices'][0]['text']
    # await c_channel.send(message)
async def morning_brief(channel, events, annouce):
    global startingprompt
    day = ''
    date = datetime.now()
    date = date.astimezone(timezone('US/Eastern'))
    daynum = date.weekday()
    
    if daynum == 0:
        day = 'Monday'
    elif daynum == 1:
        day = 'Tuesday'
    elif daynum == 2:
        day = 'Wednesday'
    elif daynum == 3:
        day = 'Thursday'

    elif daynum == 4:
        day = 'Friday'
    elif daynum == 5:
        day = 'Saturday'
    else:
        day = 'Sunday'
    if events != '' and annouce != '': # there are both events and annoucements
        txt=startingprompt + 'Now summarize these announcements and list any scheduled events, give details, say the host exactly as written, what day etc. Then say something fun to end your morning briefing:\n'+annouce+events
    
    elif events != '' and annouce == '': #there are events, but no announcements
        txt = 'Now list any scheduled events, give details, say the host exactly as written, what day etc. Then say something fun to end your morning briefing:\n'+events
        #reminder = await pick_safety_reminder()
        #txt = txt + reminder
    
    elif events == '' and annouce != '': # there are no events, but there are annoucements
        txt = 'Now say something like "There are no guild scheduled events yet, but here are the latest annoucements" then tell us about the following and end your morning brief: \n' + annouce
        #story = await pick_story()
        #txt = txt + story
    
    else: #there are niether events nor annoucements
        txt = 'Now say something like "We have no scheduled guild events, but let me tell you whats happening around town... " then tell us about the following and end your morning brief: \n'
        story = await pick_story()
        txt = txt + story + '\n'
        #temporarily commenting out safety reminder as they are kinda corny
        #txt2 = 'Finally, tell us you also have a safety reminder for us about this, and then end your morning brief: \n'
        #reminder = await pick_safety_reminder()
        #txt = txt + txt2 + reminder
    flagged_messages = await ingest_flagged_messages() #check for flagged messages
    if flagged_messages != '': #if we have flagged messages
        print('there are flagged messages')
        txt = txt + 'Before you sign off, the following guild members wanted their messages mentioned in your morning brief: '+flagged_messages
    else:
        print('there are no flagged messages')
    response = chat_engine.chat(txt)
    return response
    #await c_channel.send(response)

async def random_alert_scheduler():
    global percent_alert_yes, min_alert_seconds, max_alert_seconds
    #choose random seconds between the min and max times
    seconds_until_alert = random.randint(min_alert_seconds, max_alert_seconds) #first time after starting bot shorter
    while True:
        print('seconds to sleep for alert: ' + str(seconds_until_alert))
        await asyncio.sleep(seconds_until_alert)  # Sleep until we hit the target time
        
        #roll a chance to have an alert
        alert_roll = random.randint(0,10) #0-10 then convert to 0-100
        alert_roll = alert_roll*10
        print("alert roll: " + str(alert_roll))
        if alert_roll <= percent_alert_yes: #if less than percent yes
            print('alert triggered')
            test_channelID = 1156939619225587733 #Droid test channel
            main_channelID = 941946605479817218 #tempest main channel
            response = await create_alert()
            c_channel = client.get_channel(main_channelID)
            await c_channel.send(response)
        else:
            print('alert not triggered')
        seconds_until_alert = random.randint(min_alert_seconds, max_alert_seconds) #generate new time


#timer for counting down to reset chat
async def chat_reset_timer():
    global chat_countdown
    while True:
        if chat_countdown > 1:
            chat_countdown -= 1
        elif chat_countdown == 1:
            chat_countdown = 0
            chat_engine.reset()
            print('chat is now reset')
        await asyncio.sleep(60)

#make the morning brief post
async def post_morningbrief(channelID):
    global chat_countdown, chat_countdown_max
    chat_countdown = chat_countdown_max #set the countdown timer to max
    c_channel = client.get_channel(channelID)
    events = await ingest_events()
    annouce = await ingest_announcements()
    weatherresponse = await weather_report(channelID)  # Call the function that makes the weather report
    briefresponse = await morning_brief(channelID, events, annouce)
    await c_channel.send(weatherresponse)
    await c_channel.send(briefresponse)

#make the morning brief post
async def post_just_brief(channelID):
    c_channel = client.get_channel(channelID)
    #weatherresponse = await weather_report(channelID)  # Call the function that makes the weather report
    #await c_channel.send(weatherresponse)
    briefresponse = await morning_brief(channelID)
    await c_channel.send(briefresponse)

#timer for morning brief
async def post_timer():
    global postMorning
    now = datetime.now()
    if now.time() > postMorning:  # Make sure loop doesn't start after {postMorning} as then it will send immediately the first time as negative seconds will make the sleep yield instantly
        tomorrow = datetime.combine(now.date() + timedelta(days=1), time(0))
        seconds = (tomorrow - now).total_seconds()  # Seconds until tomorrow (midnight)
        await asyncio.sleep(seconds)   # Sleep until tomorrow and then the loop will start 
    
    while True:
        now = datetime.now() # You can do now() or a specific timezone if that matters
        midnight = time(0,0,0)
        if now.time() < postMorning:
          target = postMorning
        else:
          target = midnight

        if target != midnight:
          
          target_time = datetime.combine(now.date(), target) 
          seconds_until_target = (target_time - now).total_seconds()
          print('seconds to wait')
          print(seconds_until_target)
          await asyncio.sleep(seconds_until_target)  # Sleep until we hit the target time
          event_channelID = 955640862166110249 #event channel in SHADE
          await post_morningbrief(event_channelID) #post the whole morning brief to the event channel in SHADE
        else:
          tomorrow = datetime.combine(now.date() + timedelta(days=1), time(0))
          seconds = (tomorrow - now).total_seconds()  # Seconds until tomorrow (midnight)
          await asyncio.sleep(seconds)   # Sleep until tomorrow and then the loop will start

#timer for morning brief
async def context_timer():
    global postMorning, reloadNight, reloadMorning
    while True:
        now = datetime.now()
        midnight = time(0,0,0)
        if now.time() < reloadMorning:
            target = reloadMorning
            print('target is reload morning')
        elif now.time() >= reloadMorning and now.time() < reloadNight:
            target = reloadNight # 4 in the afternoon, load it again
            print('target is reload night')
        else:
            target = midnight
            print('target is midnight')


        if target != midnight:
            target_time = datetime.combine(now.date(), target) 
            seconds_until_target = (target_time - now).total_seconds()
            print('seconds to wait until context load')
            print(seconds_until_target)
            await asyncio.sleep(seconds_until_target)  # Sleep until we hit the target time
            #do the thing
            await load_context()  # Call the function that updates context
        else:  # wait till midnight
            print('wating til midnight - context timer')
            tomorrow = datetime.combine(now.date() + timedelta(days=1), time(0))
            seconds = (tomorrow - now).total_seconds()  # Seconds until tomorrow (midnight)
            await asyncio.sleep(seconds)   # Sleep until tomorrow and then the loop will start 

#function to create a random alert
async def create_alert():
    global startingprompt, chat_countdown, chat_countdown_max
    prompt = " Please give Mos Pelgo a short alert (1-3 sentence) message using this prompt: "
    myList = [] #array of strings
    fileR = open('rp/RandomAlert.txt', "r", encoding="utf-8")
    str = fileR.read()
    myList = str.splitlines(keepends=True)
    alert = random.choice(myList)
    response = chat_engine.chat(startingprompt + prompt + alert)
    chat_countdown = chat_countdown_max #set the countdown

    return response


#may not be needed, was for ingesting a few messages from guild info channel
async def ingest_intro():
    global prompt
    channelID = 1060780901581193216
    messageIDs = [1132115316189700128, 1132115237269672106, 1090124608646164581, 1060783286814785536]
    
    prompt = prompt + " Here is some background info: "
    channel = client.get_channel(channelID)
    for i in messageIDs:
        message = await channel.fetch_message(i)
        msg= message.content
        prompt = prompt + "Next background info : " + msg

#ingest flagged messages, and clear any older ones
async def ingest_flagged_messages():
    #load txt
    #read in all messages and save to list
    #remove messages that are old
    #save messages back to txt
    
    myList = [] #array of strings
    today = datetime.now() #for date comparison, deleting old messages
    fileR = open('rp/flaggedMessages.txt', "r", encoding="utf-8")
    str = fileR.read()
    myList = str.splitlines(keepends=True)
    # this was from another function, we want all, not just random
    #choice = random.choice(myList)
    
    # initializing substrings
    sub1 = "Message date:"
    sub2 = ";"
    for i in myList:
        # getting index of substrings
        idx1 = i.index(sub1)
        idx2 = i.index(sub2)
        datestr = ''
        # getting elements in between
        for idx in range(idx1 + len(sub1) + 1, idx2):
            datestr = datestr + i[idx]
        print(datestr)
        datetime_object = datetime.strptime(datestr, '%Y-%m-%d %H-%M-%S')#create datetime object from string
        backdate = today - timedelta(days=2) # only accept 2 day old messages
        if datetime_object < backdate: # message is old
            myList.remove(i) # delete it
            print('removed old message from flagged messages')
    fileR.close()
    #clear the file
    fileW = open('rp/flaggedMessages.txt', "w", encoding="utf-8")
    fileW.close()
    #open file for writing again
    fileW = open('rp/flaggedMessages.txt', "w", encoding="utf-8")
    #save the messages back to txt and concat all messages into one str
    all_messages = ''
    for i in myList:
        all_messages = all_messages + i
    fileW.write(all_messages)
    fileW.close()

    return all_messages

async def remove_flagged_message(message):
    myList = [] #array of strings
    today = datetime.now() #for date comparison, deleting old messages
    fileR = open('rp/flaggedMessages.txt', "r", encoding="utf-8")
    str = fileR.read()
    myList = str.splitlines(keepends=True)
    fileR.close()
    fileW = open('rp/flaggedMessages.txt', "w", encoding="utf-8")
    fileW.close()  
    #iterate through messages, check if being removed
    for i in myList:
        if message == i:
            myList.remove(i)
    #open file for writing again
    fileW = open('rp/flaggedMessages.txt', "w", encoding="utf-8")
    #save the messages back to txt and concat all messages into one str
    all_messages = ''
    for i in myList:
        all_messages = all_messages + i
    fileW.write(all_messages)
    fileW.close()

async def add_flagged_message(message):
    myList = [] #array of strings
    today = datetime.now() #for date comparison, deleting old messages
    fileR = open('rp/flaggedMessages.txt', "r", encoding="utf-8")
    str = fileR.read()
    myList = str.splitlines(keepends=True)
    fileR.close()
    fileW = open('rp/flaggedMessages.txt', "w", encoding="utf-8")
    fileW.close()  
    #iterate through messages, check if being removed
    for i in myList:
        if message == i:
            return #end without adding anything. Message already added.
    #add the new message
    myList.append(message)
    #open file for writing again
    fileW = open('rp/flaggedMessages.txt', "w", encoding="utf-8")
    #save the messages back to txt and concat all messages into one str
    all_messages = ''
    for i in myList:
        all_messages = all_messages + i
    fileW.write(all_messages)
    fileW.close()

#ingest the announcements channel
async def ingest_announcements():
    global announcementsToday
    announcementsToday = False #false by default
    channelID = 1009349616371769397
    channel = client.get_channel(channelID)
    backdate = datetime.utcnow() - timedelta(days = 2)
    messages = [message async for message in channel.history(limit=1, after=backdate, oldest_first=False)]
    combined_text = ''
    for i in messages:
        print(i)
        print(i.content)
        combined_text = combined_text + 'Announcement-\n'
        user = i.author
        nickname = user.display_name
        combined_text = combined_text + nickname + ' says: \n'
        txt = i.content
        combined_text = combined_text + txt + '. '
    if combined_text != '':
        announcementsToday = True
        combined_text = '\nHere are the announcements from the announcements channel:\n' + combined_text
    else:
        announcementsToday = False
    return combined_text

async def get_weekday(num):
    day = ''
    if num == 0:
        day = 'Monday'
    elif num == 1:
        day = 'Tuesday'
    elif num == 2:
        day = 'Wednesday'
    elif num == 3:
        day = 'Thursday'
    elif num == 4:
        day = 'Friday'
    elif num == 5:
        day = 'Saturday'
    else:
        day = 'Sunday'
    return day

#for pulling scheduled events and listing them for the bot
async def ingest_events():
    global eventsToday, tempest_event_channelID
    eventsToday = False #set to false by default
 
    channel = client.get_channel(tempest_event_channelID)
    server = channel.guild
    events = await server.fetch_scheduled_events()
    print('Number of events loaded: ')
    print(len(events))
    eventListStr = ''
    eventsList = []
    for i in events:
        eventStr = ''
        name = i.name
        hostID = i.creator.id
        host = await server.fetch_member(hostID)
        if host.nick is not None:
            hostname = host.nick
        elif host.global_name is not None:
            hostname = host.global_name
        eventDesc = i.description
        location = i.location
        date = i.start_time
        date = date.astimezone(timezone('US/Eastern'))
        daynum = date.weekday()
        fullDate = date.strftime("%A, %b %d, %I:%M %p")
        
        #get weekday of event and todays weekday
        event_weekday = await get_weekday(daynum)
        today_weekday = await get_weekday(datetime.now().weekday())
        cutoff_date = datetime.now().astimezone(timezone('US/Eastern'))
        cutoff_date = cutoff_date + timedelta(hours=18) #any events in the next 24hrs
        #are there events in the next day
        if date <= cutoff_date:
            eventsToday = True
            eventStr = 'Scheduled event:\nName of event: '+name + '\n'
            if eventDesc is not None:
                eventStr = eventStr + 'Event Description: ' + eventDesc + '\n'
            if location is not None:
                eventStr = eventStr + 'Event Location: '+ location + '\n'
            if hostname is not None:
                eventStr = eventStr + 'Event Host: '+ hostname + '\n'
            if event_weekday is not None:
                eventStr = eventStr +'Date of Event: ' +fullDate+ '\n'
            eventsList.append(eventStr) #add to todays events (strings)
    if len(eventsList) > 0: #if we have events today
        todaydate = datetime.utcnow()
        eventListStr = 'Todays Date: '+ todaydate.strftime("%A, %b %d") + '\nWhat are the scheduled events? These are the upcoming scheduled events for the guild:\n'
        for i in eventsList:
            eventListStr = eventListStr + i + '\n'
    else:
        eventListStr = '' #no events today, return empty string
    return eventListStr

async def is_reply_to_droid(m):
    channel = m.channel
    if m.reference is not None:
         refid = m.reference.message_id
         ref =  await channel.fetch_message(refid)#the message it was replied to
         auth = ref.author # the sender of the first message
         if auth.id == 1156937634384465960: # if its the droid
            return True
    return False

#bot responds to 'SH4D3' emoji reactions and adds the message to flagged messages
@client.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name == 'SH4D3': #correct reaction emoji
        #get channel and message content
        channelID = payload.channel_id
        messageID = payload.message_id
        channel = client.get_channel(channelID)
        guild = channel.guild
        message = await channel.fetch_message(messageID)
        user = message.author
        user_id = user.id
        guildMember = await guild.fetch_member(user_id)
        if guildMember.nick != None:
            name = guildMember.nick
        else:
            name = guildMember.global_name
        msgDate = message.created_at.strftime("%Y-%m-%d %H-%M-%S")
        
        # with open("scr.txt", mode='a') as file:
        #     file.write('Printed string %s recorded at %s.\n' % 
        #        (scr, datetime.datetime.now()))


        msg= message.content
        msg = msg.replace("\n", "")
        combinedText = "Message date: " + msgDate + ";" + name + ' said: ' + '"' + msg + '"' + '\n'
        await add_flagged_message(combinedText)

@client.event
async def on_raw_reaction_remove(payload):
    if payload.emoji.name == 'SH4D3': #correct reaction emoji removed
        print(payload)
        emoji_user = payload.user_id
        #get channel and message content
        channelID = payload.channel_id
        messageID = payload.message_id
        channel = client.get_channel(channelID)
        guild = channel.guild
        message = await channel.fetch_message(messageID)
        user = message.author
        user_id = user.id
        guildMember = await guild.fetch_member(user_id)
        remove = False
        if user_id == emoji_user or len(message.reactions) == 0: #the person who removed the emoji was the message author or theres just none left
            remove = True
        else: #there are still reactions and the author didnt remove it
            for reaction in message.reactions: # check all the reactions for droids
                if reaction.emoji.name == 'SH4D3': #there are still droid reactions (added by other users)
                    remove == False #dont remove
                    break #break the reactions for loop
        if remove == True:
            if guildMember.nick != None:
                name = guildMember.nick
            else:
                name = guildMember.global_name
            msgDate = message.created_at.strftime("%Y-%m-%d %H-%M-%S")
            msg= message.content
            msg = msg.replace("\n", "")
            combinedText = "Message date: " + msgDate + ";" + name + ' said: ' + '"' + msg + '"' + '\n'
            await remove_flagged_message(combinedText)
        else:
            return


@client.event
async def on_message(message):
    global prompt, eventsList, startingprompt, chat_countdown
    prompt = ''
    msg = message.content
    
    day = ''
    date = datetime.now()
    date = date.astimezone(timezone('US/Eastern'))
    daynum = date.weekday()
    if daynum == 0:
        day = 'Monday'
    elif daynum == 1:
        day = 'Tuesday'
    elif daynum == 2:
        day = 'Wednesday'
    elif daynum == 3:
        day = 'Thursday'
    elif daynum == 4:
        day = 'Friday'
    elif daynum == 5:
        day = 'Saturday'
    else:
        day = 'Sunday'

    #text_file = open("data/prompt.txt", "w")
    #text_file.write(prompt.encode("utf-8"))
    #text_file.close()
    isreply = await is_reply_to_droid(message)
    if '<@1156937634384465960>' in msg or isreply == True:
        # c_channel = message.channel
        # await ingest_intro()
        # await ingest_announcements()
        # await ingest_events()
        # msg = re.sub('<@1156937634384465960>', '', msg)
        
        # response = openai.Completion.create(
        #     model="gpt-3.5-turbo-instruct",
        #     prompt=prompt + 'SH4D3, Today is ' +day+ '. Respond to: '+msg,
        #     max_tokens = 1000
        #     )
        # #c_channel = client.get_channel(1156939619225587733) #Droid test channel
        # message = response['choices'][0]['text']
        # await c_channel.send(message)
        
        c_channel = message.channel
        if chat_countdown <= 0: #brand new chat, give it starting prompt
            msg = re.sub('<@1156937634384465960>', '', startingprompt + 'Keep your responses very short. ' + msg)
            print('new chat started')
        else: # not a new chat, no starting prompt needed
            msg = re.sub('<@1156937634384465960>', '', msg)
        response = chat_engine.chat(msg)
        await c_channel.send(response)
        chat_countdown = chat_countdown_max #set chat countdown to 15 min each time someone talks
    elif 'testbrief' in msg:
        test_channel = 1156939619225587733 #Droid test channel
        await post_morningbrief(test_channel) #do the morning bried posts in the test channel
    elif 'testalert' in msg:
        test_channelID = 1156939619225587733 #Droid test channel
        response = await create_alert()
        c_channel = client.get_channel(test_channelID)
        await c_channel.send(response)
    elif 'tempest main testpost' in msg: #for sending to Tempest main without them seeing my prompt
        event_channelID = 955640862166110249
        main_channelID = 941946605479817218
        await post_morningbrief(event_channelID)
    elif 'tempest main justbrief' in msg: #for sending to Tempest main without them seeing my prompt
        event_channelID = 955640862166110249
        main_channelID = 941946605479817218
        await post_just_brief(event_channelID)
    elif 'testchannel justbrief' in msg: #for sending to testchannel
        test_channel = 1156939619225587733 #Droid test channel 
        await post_just_brief(test_channel)
    elif 'testevents' in msg:
        test_channel = 1156939619225587733 #Droid test channel  
        briefresponse = await morning_brief(test_channel)
        await c_channel.send(briefresponse)
    elif 'loadcontext now' in msg:
        await load_context()


client.run(TOKEN)