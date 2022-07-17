# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np


movies = pd.read_csv('MY Directory/movies.csv')
ratings = pd.read_csv('MY Directory/ratings.csv')
tags = pd.read_csv('MY Directory/tags.csv')

rating=ratings.drop(['userId','timestamp'],axis=1)
tag=tags.drop(['userId','timestamp'],axis=1)


rate=pd.DataFrame(rating.groupby('movieId')['rating'].mean())
rate['number_of_ratings']=rating.groupby('movieId')['rating'].count()

tag=pd.DataFrame(tag.groupby('movieId')['tag'].apply(list))


metadata=movies.merge(rate,on='movieId')
metadata=metadata.merge(tag,on='movieId',how='left')


def clean_data(x):
    if isinstance(x, str):
        return str.lower(x.replace('|',',')) #cleaning up | in the data

metadata['genres']=metadata['genres'].apply(clean_data)

for i in range(len(metadata)):
  metadata['genres'][i]=metadata['genres'][i].split()

metadata['corpus']='' #generate corpus for ML models
for i in range(len(metadata)):
  if isinstance(metadata['tag'][i],list):
    metadata['corpus'][i]=' '.join(metadata['genres'][i]).replace(',',' ') + ' ' + ' '.join(metadata['tag'][i]).replace(',',' ')
  else:
    metadata['corpus'][i]=' '.join(metadata['genres'][i]).replace(',',' ')
     
#local prediction testing functions
def get_genres():
  genre=input("What Genre of Movies are you interested in?(Seperate by comma if you interested in more than one)[Type 'skip' to skip this question]")
  genre = " ".join(["".join(n.split()) for n in genre.lower().split(',')])
  return genre

def get_tags():
  keywords=input("What are some Keywords that describe the movie you want to watch?(Seperate by comma if you interested in more than one)[Type 'skip' to skip this question]")
  keywords = " ".join(["".join(n.split()) for n in keywords.lower().split(',')])
  return keywords

def get_rating():
  num_rate=input("How many ratings do you want for the recommended movies?(In range from 1 to 300 Default value is 1)[Type 'skip' to skip this question]")
  return num_rate

def get_searchterms():
  searchTerm=[]
  genres=get_genres()
  if genres != 'skip':
    searchTerm.append(genres)
  
  keywords=get_tags()
  if keywords != 'skip':
    searchTerm.append(keywords)  
  
  return searchTerm

train_set=metadata['corpus'].values
train_label=metadata['title'].values

#BOW model
from sklearn.feature_extraction.text import CountVectorizer
count_vect = CountVectorizer()
X_train_counts = count_vect.fit_transform(train_set)
X_train_counts.shape

#TFIDF model
from sklearn.feature_extraction.text import TfidfTransformer
tfidf_transformer = TfidfTransformer()
X_train_tfidf = tfidf_transformer.fit_transform(X_train_counts)
X_train_tfidf.shape



#local prediction test
from sklearn.neighbors import KNeighborsClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
def make_recommendation(metadata=metadata):
  searchTerms=get_searchterms()
  num_rate=get_rating()
  if num_rate != 'skip':
    lim_data=metadata[metadata['number_of_ratings']>=int(num_rate)]
    train_set=lim_data['corpus'].values
    train_label=lim_data['title'].values
  else:
    train_set=metadata['corpus'].values
    train_label=metadata['title'].values

  count_vect = CountVectorizer()
  X_train_counts = count_vect.fit_transform(train_set)
  tfidf_transformer = TfidfTransformer()
  X_train_tfidf = tfidf_transformer.fit_transform(X_train_counts)
  clf = KNeighborsClassifier().fit(X_train_tfidf,train_label)
  predict= count_vect.transform(searchTerms)
  predict= tfidf_transformer.transform(predict)
  result=clf.predict(predict)
  print(result)
  
#make_recommendation()

#Dialogflow prediction function 
def make_recommendation(searchTerms, data):
  if len(searchTerms) !=0:
    train_set=data['corpus'].values
    train_label=data['title'].values
    count_vect = CountVectorizer()
    X_train_counts = count_vect.fit_transform(train_set)
    tfidf_transformer = TfidfTransformer()
    X_train_tfidf = tfidf_transformer.fit_transform(X_train_counts)
    clf = KNeighborsClassifier().fit(X_train_tfidf,train_label)
    predict= count_vect.transform(searchTerms)
    predict= tfidf_transformer.transform(predict)
    result=clf.predict(predict)
  else:
    result=data.sort_values(by=['rating'],ascending=False).head(3)['title'].values
  return result


#Flask used to capture Raw API json sent by dialogflow
from flask import Flask, request, send_from_directory

import os
import json

#store user input into a list
searchTerm=[]
#create a copy of original database
dupdata=metadata

app = Flask(__name__)

# @app.route('/',methods=["POST","GET"])
# def webhook():
#   if request.method == 'GET':
#     return "SUP"
#   elif request.method == 'POST':
#     payload= request.json
#     user_response=(payload['queryResult']['queryText'])
#     bot_response=(payload['queryResult']['fulfillmentText'])
#     if user_response or bot_response != '':
#       print("User: "+ user_response)
#       print("Bot: "+ bot_response)
#     return "Message Received"
#   else:
#     print(request.data)
#     return "200"



@app.route('/')
@app.route('/home')
def home():
    return "Hello World"

#interactions with dialogflow chatbot agent, collect user input and make recomendations
@app.route('/webhook', methods=['POST','GET'])
def webhook():
    global searchTerm
    global dupdata
    req = request.get_json(force=True)
    user_response=(req['queryResult']['queryText'])
    if user_response.find("genre:") != -1 or user_response.find("Genre:") != -1:
      genre = " ".join(["".join(n.split()) for n in user_response.lower().split(',')])
      genre = genre.replace('genre:','')
      searchTerm.append(genre)
    elif user_response.find("tag:") != -1 or user_response.find("Tag:") != -1:
      tag = " ".join(["".join(n.split()) for n in user_response.lower().split(',')])
      tag = tag.replace('tag:','')
      searchTerm.append(tag)
    elif user_response.find("number of ratings:") != -1 or user_response.find("Number of Ratings:") != -1:
      numrate = " ".join(["".join(n.split()) for n in user_response.lower().split(',')])
      numrate=numrate.replace('numberofratings:','')
      numrate=int(numrate)
      dupdata=dupdata[dupdata['number_of_ratings']>=int(numrate)]
    elif user_response.find("ratings:") != -1 or user_response.find("Ratings") != -1:
      rate = " ".join(["".join(n.split()) for n in user_response.lower().split(',')])
      rate=rate.replace('ratings:','')
      rate=float(rate)
      dupdata=dupdata[dupdata['rating']>=float(rate)]
    elif user_response.find("That is all") != -1:
      prediction=make_recommendation(searchTerm,dupdata)
      #reset user inputs for potential another recommendation
      searchTerm.clear()
      dupdata=metadata
      prediction=" ".join([" ".join(n.split()) for n in prediction])
      return {
        'fulfillmentText': 'Your Recommendations: '+prediction+' Would you like hear another recommendation?'
      }
    return "Message Received"

if __name__ == "__main__":
    app.secret_key = 'ItIsASecret'
    app.debug = True
    app.run()
