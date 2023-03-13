# Update-Tags

## Script
[Update Tags] is a Python script that allows updating tags on shift types in/on:
    
    * Schedule
    * Shift types
    * Base schedule

To run the script, place it in a folder together with a 'config.json' file (see below) and your .csv file.


## config.json
The config.json file is formatted as:

{
    "username": "",
    "password": "",
    "domainGroupId": 0,
    "onlyUpdateTheseGroups": [],
    "environment": "",
    "applyTo": {
        "schedule": true/false,
        "baseSchedule": true/false,
        "shiftTypes": true/false
    },
    "fromDate": "YYYY-MM-DD",
    "toDate": "YYYY-MM-DD",
    "csvPath": "yourfile.csv"
}

***Username, Password***
This is your Quinyx username + password.

***domainGroupId***
The group ID of the customer's domain, used to fetch group data necessary to perform all updates.

***onlyUpdateTheseGroups***
**CURRENTLY IN TESTING, NOT FUNCTIONAL!**

You can add one or more group ID:s that you specifically want to update. Note that a group ID for i.e. a unit will also include its sections, a group ID for a district will include its units and sections, etc.

***environment***
This is the environment you want to run the script towards. Accepted formats are:

* web           (_ _Production_ _)
* web-rc        (_ _RC_ _)
* web-qdaily    (_ _Qdaily_ _)

***applyTo***
Here you can specify what you want to update. Write **true** if you want to update, or **false** if the script should ignore it.

***fromDate, toDate***
**Only applicable for _applyTo -> schedule_.**

Specify between which dates you want to update the tags for.

***csvPath***
The .csv-file path. This file must not be present in the same folder as the script or the config.json-file, but you must then specify the exact path to your .csv-file. If the .csv-file is present in the same folder as the script, you can write only the name of the .csv-file.


## .csv-file
The .csv-file must include the following:

* NO headers
* Column A = shift type ID (the Quinyx internal ID, not an external integration key)
* Column B = tag external ID (not the internal tag ID)