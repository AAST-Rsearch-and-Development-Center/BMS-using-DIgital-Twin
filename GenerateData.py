import requests
import urllib.parse
import json
import polyline
import csv

#Open Weather Map API KEY - https://home.openweathermap.org/api_keys
weather_api_key = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
#Google API KEY
KEY="XXXXXXXXXXXXXXXXXXXXXXXXXX"
#Constants
UPHILL_TOLERANCE = 0.1

#Documentation: https://openweathermap.org/api/one-call-3
def weather(grocode):
    #return 10
    # checks the weather condtions in the city
    # base_url variable to store url
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = base_url + "appid=" + weather_api_key + "&lat="+str(grocode[0])+ "&lon=" + str(grocode[1]) + "&units=metric"
    response = requests.get(complete_url)
    # json method of response object
    # convert json format data into
    # python format data
    x = response.json()

    # Now x contains list of nested dictionaries
    # Check the value of "cod" key is equal to
    # "404", means city is found otherwise,
    # city is not found
    if x["cod"] == "404":
        return 0
    else:
        # store the value of "main"
        # key in variable y
        y = x["main"]

        # store the value corresponding
        # to the "temp" key of y
        return (y["temp"],y["pressure"], x["wind"]["deg"], x["wind"]["speed"])

def getTotalDistance(distance):
	tokinized = distance.split()
	#print(tokinized)
	if tokinized[1]=="km":
		#print(float(tokinized[0])*1000)
		return float(tokinized[0])*1000
	else:
		#print(float(tokinized[0]))
		return float(tokinized[0])

def getTotalTime(distance):
	tokinized = distance.split()
	#print(tokinized)
	if len(tokinized)==4:
		#print(float(tokinized[0])*60 + float(tokinized[2]))
		return float(tokinized[0])*60 + float(tokinized[2])
	else:
		if tokinized[1]== "mins" or tokinized[1]== "min":
			#print(float(tokinized[0]))
			return float(tokinized[0])
		else:
			#print(float(tokinized[0])*60)
			return float(tokinized[0])*60
"""
direction method is responsible for handling the directions
the drivingBehiviour could have one of three values (bestguess, pessimistic, optimistic) #https://developers.google.com/maps/documentation/javascript/directions#UnitSystems
"""
def direction(origin = "Alexandria", destination = "Cairo", behaviour = 1):
	url="https://maps.googleapis.com/maps/api/directions/json"

	raw_params = {
		"origin": origin, #"El Ibrahemeya, Alexandria",
		"destination": destination, #"Semouha, Alexandria",
		"unitSystem": "Metric",
		"key": KEY
	}
	params = urllib.parse.urlencode(raw_params)
	response = requests.request("GET", f'{url}?{params}', headers={}, data={})

	raw_data = response.text
	#print(raw_data)

	data = json.loads(raw_data)
	#print(data)
	if json.loads(response.text)["status"] != "OK":
		print("Getting Directions Not Working, code[1234]")
		return
	routeName = data["routes"][0]["summary"]
	routeTDistance = data["routes"][0]["legs"][0]["distance"]["text"]
	routeTTime = data["routes"][0]["legs"][0]["duration"]["text"]
	#print(json.dumps(data["routes"], sort_keys=True, indent=6, separators=(",", ": ")))
	routeData = [None] * len(data["routes"][0]["legs"][0]["steps"])
	totalD = 0
	totalT = 0
	#RouteData list have each step in an element, in each: total step distance, then time, then polyline points
	for i in range(0, len(data["routes"][0]["legs"][0]["steps"])):
		routeData[i] = (getTotalDistance(data["routes"][0]["legs"][0]["steps"][i]["distance"]["text"]),
		  getTotalTime(data["routes"][0]["legs"][0]["steps"][i]["duration"]["text"]),
		  polyline.decode(data["routes"][0]["legs"][0]["steps"][i]["polyline"]["points"])
		  )
		totalD += routeData[i][0]
		totalT += routeData[i][1]
		#print(i, " --> ", routeData[i])
	#print("D> ",totalD, ", T> ",totalT)
	createStream(routeData, totalD, totalT, behaviour)

"""
createStream function task is to modify the obtained data from API to fit the digital twin inputs
the finalData list contains: 
[trip total distance, trip total estimated time, 
city temprature, pressure, wind degree, Wind Speed, 
traveled distance so far as meters (step distance divided over each step inside the polyline),
traveled time so far as minutes (step time divided over each step inside the polyline),
speed (km/h), climbing, geocode]
"""
def createStream(routeData,totalD, totaleT, behaviour):
	finalData = list()#['Total Distance', 'Total Time', 'Temprature', 'Wind Speed',
	      #"Traveled Distance (m)", "Traveled Time (min)", "Speed (km/h)", 
		  #"Climbing?", "Latitude", "Longitude"]
	#print(len(routeData[0][2]))
	accomulatedDistance = 0
	accomulatedTime = 0
	previousPoint = routeData[0][2][0]

	for i in range(0, len(routeData)):
		if i > 0:
			accomulatedDistance += routeData[i-1][0] 
			accomulatedTime += routeData[i-1][1] 
		print("D and T == ", routeData[i][0], routeData[i][1])
		for j in range(0, len(routeData[i][2])):
			weath = weather(routeData[i][2][j])
			finalData.append([round(totalD,1), round(totaleT*behaviour,1), weath[0], weath[1],weath[2],weath[3],
				round(accomulatedDistance+(routeData[i][0]/len(routeData[i][2]))*(j+1),1),
				round(accomulatedTime+(routeData[i][1]/len(routeData[i][2]))*(j+1)*behaviour,1),
				120 if (round((routeData[i][0]/1000)/(routeData[i][1]*behaviour/60)))> 120 else round((routeData[i][0]/1000)/(routeData[i][1]*behaviour/60)),
				climbing(previousPoint[0],previousPoint[1], routeData[i][2][j][0], routeData[i][2][j][1]),
				routeData[i][2][j][0], routeData[i][2][j][1]])
			previousPoint = routeData[i][2][j]
			print("i=", i, " j=", j, " Index= ", len(finalData)-1, finalData[len(finalData)-1])
	storeInCSVFile("Traviling_Data.csv", finalData)
	#print(routeData[1])
	#print(len(routeData[1][2]))

#OS getElevation method takes a location latitude and longitude, uses Google Elevation API to return the location's Elevation
def getElevation(lat, lng):
	url = "https://maps.googleapis.com/maps/api/elevation/json?locations="+str(lat)+"%2C"+str(lng)+"&key="+KEY
	payload={}
	headers = {}
	response = requests.request("GET", url, headers=headers, data=payload)
	if json.loads(response.text)["status"] == "OK":
		return json.loads(response.text)["results"][0]["elevation"]
	else:
		return 0

#OS climbing method calculates if the traveling object is climbing or steady or descending while traveling by getting two elevations (of two consequent locations) and get the difference
def climbing(lat1, lng1, lat2, lng2):
	#return 0.1
	diff = getElevation(lat2, lng2)-getElevation(lat1, lng1)
	#print("El2 = ", getElevation(lat2, lng2), "El1 = ", getElevation(lat1, lng1),"Diff>", diff)
	if diff > UPHILL_TOLERANCE:
		return "climbing"
	elif diff >= UPHILL_TOLERANCE*-1 and diff <= UPHILL_TOLERANCE:
		return "steady"
	elif diff < UPHILL_TOLERANCE*-1:
		return "descending"

def storeInCSVFile(csvFileName, rows):
	with open(csvFileName, 'w', newline='') as file:
		writer = csv.writer(file)
		writer.writerows(rows)

#print(climbing(31.2173762259494, 29.942175724788083, 31.21654423912898, 29.942060302611218))
direction("Sidi Bishr, Alexandria, Egypt", "Semouha, Alexandria, Egypt", 0.8)
