from flask import Flask, request, jsonify
app = Flask(__name__)

import os
import redis
import json



# use local settings for connecting to the database
# example from https://stackoverflow.com/questions/9383450/how-can-i-detect-herokus-environment
USE_LOCAL = not 'ON_HEROKU' in os.environ

redis_url = os.getenv('REDISTOGO_URL')

#database is set up so that every item is a key value is an item and the value is either inventory or grocery 
#depending on what list it is being a added to

# connect to the database and return the db handle
def connectToDatabase():
	db = None
	if USE_LOCAL:
		db = redis.Redis(host='localhost', port=6379, db=0)
	else:
		#decode to get string instead of bytes, reference: https://stackoverflow.com/questions/44026515/python-redis-keys-returns-list-of-bytes-objects-instead-of-strings/45484370
		db = redis.from_url(os.environ.get("REDIS_URL"), decode_responses=True)	
	
	return db


#have a key for grocery and a key for invenotry, each will keep track of a list of what is on their 
def initialize(db):
	db.set('grocery', '')
	db.set('inventory','')

#add an item to the database corresponding to list
def addItem(db, itemName, listName):
	if not db.exists(itemName):
		db.set(itemName,listName)
	else:
		db.set(itemName,listName)
	return itemName + " was added to " + listName

#check if an item is in the database corresponding to list 
def checkItem(db, itemName, listName):
	if db.get(itemName):
		if str(db.get(itemName))==listName:

			return itemName + " is on " + listName
		else:
			return itemName + " is not on " + listName

	else:
		print("else")
		return itemName + " is not on " + listName

#try to print all xof a database, used for debugging 
def getAll(db):
	print(db.dbsize())
	for key in db.scan_iter():
		print (key)

#delete all from database
def deleteAll(db):
	for key in db.scan_iter():
		db.delete(key)

#delete item from given list
def deleteItem(db, itemName, listName):
	if db.get(itemName) == listName:
		db.delete(itemName)
	if listName == 'inventory':
		otherList = 'grocery list?'
	else:
		otherList = 'inventory?'
	return itemName + " is deleted from "+ listName+". Would you like me to add it to your "+otherList

#delete the entirety of a list
def clearList(db, listName):
	for key in db.scan_iter():
		if db.get(key) == listName:
			db.delete(key)
	return listName + " is now empty"

#print the entirety of a list
def printList(db, listName):
	listItems = ''
	for key in db.scan_iter():
	 	if db.get(key) == listName:
	 		listItems += key
	 		listItems += '\n'
	if listItems == '':
	 	return listName + " is empty"
	else:
	 	return listName+ ": " + listItems + " "





@app.route("/")
def root():
	return """
	<h1>Commands:</h1>
	<ul>
		<li>/printAll - print the entire inventory and grocery list</li>
		<li>/deleteAll - clear inventory and grocery list
		<li>/add/{itemName}/{listName} - add item to list</li>
		<li>/clearList/{listName} - clear a specific list/li>
		<li>/deleteItem/{itemName}/{listName} - delete item from list</li>
		<li>/print/{listName} - print list</li>
		<li>/lastRequest - see JSON of the last webhook request (for debugging)</li>
	</ul>
	"""

@app.route("/get/<itemName>/<listName>")
def webCheckItem(itemName, listName):
	db = connectToDatabase()
	return checkItem(db, itemName, listName)

@app.route("/add/<itemName>/<listName>")
def webAddItem(itemName, listName):
	db = connectToDatabase()
	print('test')
	return addItem(db,itemName,listName)

@app.route("/printAll")
def webPrintAll():
	print('test')
	db = connectToDatabase()
	getAll(db)

@app.route("/deleteAll")
def webDeleteAll():
	db = connectToDatabase()
	deleteAll(db)

@app.route("/clearList/<listName>")
def webClearList(listName):
	db = connectToDatabase()
	return clearList(db, listName) 

@app.route("/deleteItem/<itemName>/<listName>")
def webDeleteItem(itemName, listName):
	db = connectToDatabase()
	return deleteItem(db, itemName, listName)

@app.route("/print/<listName>")
def webPrintList(listName):
	db = connectToDatabase()
	return printList(db, listName)	


# this is for debugging the webhook code
# it just prints out the json of the last webhook request
@app.route("/lastRequest")
def lastRequest():
	db = connectToDatabase()
	req = db.get("lastRequest")
	return req

# webhook code goes here
# this is set to receive a webhook request from DialogFlow
# see https://dialogflow.com/docs/fulfillment/how-it-works for details
# 
# basically, the url /dialog will expect a JSON object as described above
# and will parse the attached JSON object, then do stuff

@app.route("/dialog", methods=["POST"])
def handleDialog():
	data = request.get_json()
	
	# save this request for debugging
	db = connectToDatabase()
	db.set("lastRequest", json.dumps(data))
	
	# debug
	# print data
	
	# now, do stuff based on the JSON data
	# in particular we want to look at the queryResult.intent.displayName to
	# see which intent is triggered, and queryResult.parameters to see params
	

	if data['queryResult']['intent']['displayName'] == "AddItemGeneric":
		itemName = data['queryResult']['parameters']['Item']
		listName = data['queryResult']['parameters']['list']
		response = webAddItem(itemName,listName)
		print (response)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "AddItemShopping":
		itemName = data['queryResult']['parameters']['Item']
		listName = 'grocery'
		response = webAddItem(itemName,listName)
		print (response)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "AddtoInventory":
		itemName = data['queryResult']['parameters']['Item']
		listName = 'inventory'
		response = webAddItem(itemName,listName)
		print (response)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "checkItem":
		itemName = data['queryResult']['parameters']['Item']
		listName = data['queryResult']['parameters']['list']
		response = webCheckItem(itemName, listName)
		print (response)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "GetAllInventory":
		response = webPrintList('inventory')
		print (response)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "GetAllGrocery":
		response = webPrintList('grocery')
		print (response)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "GetAllList":
		listName = data['queryResult']['parameters']['list']
		response = webPrintList(listName)
		print (response)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "ClearList":
		listName = data['queryResult']['parameters']['list']
		response = webClearList(listName)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "deleteAll":
		webDeleteAll()
		return jsonify({'fulfillmentText': 'cleared inventory and grocery list'})
	elif data['queryResult']['intent']['displayName'] == "deleteItemGeneric":
		itemName = data['queryResult']['parameters']['Item']
		listName = data['queryResult']['parameters']['list']
		response = webDeleteItem(itemName, listName)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "deleteFromInventory":
		itemName = data['queryResult']['parameters']['Item']
		listName = 'inventory'
		response = webDeleteItem(itemName, listName)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "deleteItemFromGroceryList":
		itemName = data['queryResult']['parameters']['Item']
		listName = 'grocery'
		response = webDeleteItem(itemName, listName)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "deleteItemGeneric - yes":
		itemName = data['queryResult']['parameters']['Item']
		listName = data['queryResult']['parameters']['list']
		if listName == 'inventory':
			listName = 'grocery'
		else:
			listName = 'inventory'
		response = webAddItem(itemName, listName)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "deleteItemFromShoppingList - yes":
		itemName = data['queryResult']['parameters']['Item']
		listName = 'inventory'
		response = webAddItem(itemName, listName)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "deleteFromInventory - yes":
		itemName = data['queryResult']['parameters']['Item']
		listName = 'grocery'
		response = webAddItem(itemName, listName)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "justItem-add":
		itemName = data['queryResult']['parameters']['Item']
		listName = data['queryResult']['parameters']['list']
		response = webAddItem(itemName,listName)
		print (response)
		return jsonify({'fulfillmentText': response})
	elif data['queryResult']['intent']['displayName'] == "justItem-check":
		itemName = data['queryResult']['parameters']['Item']
		listName = data['queryResult']['parameters']['list']
		response = webCheckItem(itemName, listName)
		print (response)
		return jsonify({'fulfillmentText': response})


if __name__ == "__main__":
	db = connectToDatabase()
	initialize(db)
	app.run()
