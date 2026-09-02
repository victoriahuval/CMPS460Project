
# Sims 4 Catalog Database Project 

## Purpose
I made this demo web app in my database management class to be able to demonstrate how to implement different queries by selection. insertion and deletion. 
This demo consists of admin permissions for users to add, edit or delete skin packs, creators, categories, and users. 
It also includes security measures using Werkzeug password hashing to protect users from cross-site attacks, CSRF tokens, and SQL injection protection. 

## Tech Stack
    Jinja2 HTML
    Python 3 Flask
    SQlite 

## How to run
To run the server (assuming project is cloned), run this in your terminal:

`cd [FILE PATH TO PROJECT ON DESKTOP]`

`source venv/bin/activate`

`python3 app.py`

the server URL is `http://127.0.0.1:5000/`
