import os
import csv
import json
import requests
from requests.auth import HTTPBasicAuth
from time import sleep
from datetime import datetime, date, timedelta

intro_text = """
################################## Update tags ##################################
This script will update the tags on given shift ID:s provided in your CSV file.


"""

config_file = "config.json"

GET = 0
POST = 1
PUT = 2

shift_error_action = {
    "error.schedule.addShift.chooseAbsenceAction": ["overrideOnOverlappingShiftsAction", "OVERLAP"]
}

current_directory = os.getcwd()
log_path = f"{current_directory}\\Logs"
log_path_exists = os.path.exists(f"{current_directory}\\Logs")

script_start_time = datetime.now()

def log_shift_to_file(status, shift):
    if not log_path_exists:
        os.makedirs(log_path)

    with open(f"{log_path}\\Logfile_{script_start_time}", 'a') as log_file:
        log_file.write(f"Shift ID {shift['id']} was not updated. Status: {status}. Body: {shift} \n")
    return

def validate_config_data(data) -> bool:

    if data["username"] == "" or data["password"] == "":
        print("Username or password is missing from the config file.")
        return False
    


    return True
    # Add validation to each field below here...

def apply_new_tag_to_shift(shift, tag):
    
    return shift

def http_with_retry(action, url, auth, body=None):
    response = None
    for _ in range(5):
        if action == GET:
            response = requests.get(url=url, auth=auth)
        elif action == POST:
            response = requests.post(url=url, json=body, auth=auth)
        elif action == PUT:
            response = requests.put(url=url, json=body, auth=auth)
        else:
            return None

        if response.status_code < 500:
            return response

        sleep(0.5)
    
    return response

# NOT IN USE YET.
def get_group_ids(group_tree: list, only_these_groups: set, get_all: bool):
    group_ids = []
    
    if len(group_tree) == 0:
        return []

    for group in group_tree:
        include_all_sub_groups = get_all
        if (group["id"] in only_these_groups) or get_all:
            if group["typeId"] == 5 or group["typeId"] == 7:
                group_ids.append(group["id"])
            include_all_sub_groups = True

        if len(group["hasAccess"]) > 0:
            group_ids.extend(get_group_ids(group["hasAccess"], only_these_groups, include_all_sub_groups))
        
    return group_ids

def main():
    print(intro_text)
    config_data = None
    with open(config_file, 'r') as f:
        config_data = json.load(f)

    if not validate_config_data(config_data):
        exit(0)

    while True:
        input_command = input("Please write 'continue' to proceed with the update, or 'quit' to exit the program: ")
        if input_command.lower().strip() == "continue":
            break
        elif input_command.lower().strip() == "quit":
            exit(0)
        else:
            print("Could not understand the input.")


    environment = config_data["environment"]
    username, password = config_data["username"], config_data["password"]
    from_date_raw = config_data["fromDate"]
    to_date_raw = config_data["toDate"]
    domain_group_id = config_data["domainGroupId"]
    apply_to_schedule = config_data["applyTo"]["schedule"]
    apply_to_base_schedule = config_data["applyTo"]["baseSchedule"]
    apply_to_shift_types = config_data["applyTo"]["shiftTypes"]
    csv_path = config_data["csvPath"]

    dates_are_valid_format = False

    if from_date_raw != "" and to_date_raw != "":
        from_date = date.fromisoformat(from_date_raw)
        to_date = date.fromisoformat(to_date_raw)
        dates_are_valid_format = True

    url_groups = f"https://{environment}.quinyx.com/extapi/v1/organisation/groups?groupId={domain_group_id}"
    url_schedules = f"https://{environment}.quinyx.com/extapi/v1/schedule/shifts/by-group/"
    url_put_schedules = f"https://{environment}.quinyx.com/extapi/v1/schedule/shifts/"
    url_get_tags = f"https://{environment}.quinyx.com/extapi/v1/tags/groups/{domain_group_id}/tags"
    url_tag_categories = f"https://{environment}.quinyx.com/extapi/v1/tags/accounts/{domain_group_id}/categories"
    url_all_base_schedules = f"https://{environment}.quinyx.com/extapi/v1/baseschedule/templates/by-group/"
    url_single_base_schedule = f"https://{environment}.quinyx.com/extapi/v1/baseschedule/templates/"
    url_shift_types = f"https://{environment}.quinyx.com/extapi/v1/shifttypes/types/group/"

    shifttype_tag_table = {}
    with open(csv_path, newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='|')

        for row in csvreader:
            shifttype_tag_table[row[0]] = row[1]
        
    # Get necessary data and parse it.
    # Tags
    print("Retrieveing tag info...")
    all_tag_categories = json.loads(http_with_retry(action=GET, url=url_tag_categories, auth=HTTPBasicAuth(username, password)).text)
    all_tags = json.loads(http_with_retry(action=GET, url=url_get_tags, auth=HTTPBasicAuth(username, password)).text)

    if "status" in all_tags or "status" in all_tag_categories: # The calls weren't sucessful.
        print(all_tag_categories, all_tags)
        exit(0)

    tag_pages = all_tags["pagination"]["totalPages"]
    all_tags_table = {}
    all_tag_cat_table = {}

    for tag_cat in all_tag_categories:
        all_tag_cat_table[tag_cat["id"]] = tag_cat

    for page in range(1, tag_pages + 1):
        all_tags = json.loads(http_with_retry(action=GET, url=(url_get_tags + f"?page={page}"), auth=HTTPBasicAuth(username, password)).text)
        for tag in all_tags["result"]:
            
            all_tags_table[tag["externalId"]] = {
                "name": tag["name"],
                "id": tag["id"],
                "categoryId": all_tag_cat_table[tag["tagCategoryId"]]["id"],
                "categoryName": all_tag_cat_table[tag["tagCategoryId"]]["name"],
                "categoryColor": all_tag_cat_table[tag["tagCategoryId"]]["color"]
            }

    # Groups
    print("Retrieving group info...")
    group_ids = []
    group_data_response = http_with_retry(action=GET, url=url_groups, auth=HTTPBasicAuth(username, password))
    
    if group_data_response.status_code == 401:
        print("401 - Could not retrieve group information: Your credentials lack sufficient access, or the credentials are incorrect.")
        exit(0)
    elif group_data_response.status_code == 403:
        print("403 - Could not retrieve group information: Your credentials lack sufficielt access.")
        exit(0)
    elif group_data_response.status_code == 404:
        print(f"404 - Could not retrieve group information: Provided group ID {domain_group_id} does not exist.")
        exit(0)

    group_data = json.loads(group_data_response.text)
    
    group_info_for_shift_types = []
    include_all_sub_groups = False

    for domain in group_data:
        for region in domain["hasAccess"]:
            for unit in region["hasAccess"]:
                if unit["typeId"] == 5:
                    group_ids.append(unit["id"])

                    if apply_to_shift_types:
                        group_info_for_shift_types.append(unit["id"])
                        for section in unit["hasAccess"]:
                            if section["typeId"] == 7:
                                group_info_for_shift_types.append(section["id"])
    
    # Begin update.    
    if apply_to_base_schedule:
        print("################## Updating base schedule ##################")
        for group in group_ids:
            base_schedules_in_group = json.loads(http_with_retry(action=GET, url=f"{url_all_base_schedules}{group}", auth=HTTPBasicAuth(username, password)).text)           
            
            for base_schedule in base_schedules_in_group:
                if "id" in base_schedule:
                    base_schedule_id = base_schedule["id"]
                    base_schedule_shifts = json.loads(http_with_retry(action=GET, url=f"{url_single_base_schedule}{base_schedule_id}", auth=HTTPBasicAuth(username, password)).text)

                    shifts_to_update = []
                    
                    for shift in base_schedule_shifts["shifts"]:
                        if str(shift["shiftTypeId"]) in shifttype_tag_table:
                            new_tag_ext_id = shifttype_tag_table[str(shift["shiftTypeId"])]

                            if new_tag_ext_id not in all_tags_table:
                                print(f"Tag with ext code {new_tag_ext_id} for shift type {shift['shiftTypeId']} in CSV file, was not found among the customer's existing tags.")
                                continue
                            
                            if "tags" in shift:
                                for tag in shift["tags"]:
                                    tag["id"] = all_tags_table[new_tag_ext_id]["id"]
                                    tag["name"] = all_tags_table[new_tag_ext_id]["name"]
                                    tag["tagCategory"]["id"] = all_tags_table[new_tag_ext_id]["categoryId"]
                                    tag["tagCategory"]["name"] = all_tags_table[new_tag_ext_id]["categoryName"]
                                    tag["tagCategory"]["color"] = all_tags_table[new_tag_ext_id]["categoryColor"]
                            else:
                                shift["tags"] = []
                                shift["tags"].append({
                                    "id": all_tags_table[new_tag_ext_id]["id"],
                                    "name": all_tags_table[new_tag_ext_id]["name"],
                                    "tagCategory": {
                                        "id": all_tags_table[new_tag_ext_id]["categoryId"],
                                        "name": all_tags_table[new_tag_ext_id]["categoryName"],
                                        "color": all_tags_table[new_tag_ext_id]["categoryColor"]
                                    }
                                })
                            shifts_to_update.append(shift)
                    
                    if len(shifts_to_update) > 0:
                        upload_response = http_with_retry(action=PUT, url=f"{url_single_base_schedule}{base_schedule_id}/shifts/batch", auth=HTTPBasicAuth(username, password), body=shifts_to_update)
                        
                        if upload_response.status_code == 500:
                            print(f"500 - Base schedule ID {base_schedule_id} was not updated due to repeating Internal Server Errors.")
                        elif upload_response.status_code == 401:
                            print()
                        elif upload_response.status_code == 403:
                            print()
                        elif upload_response.status_code == 404:
                            print()
                        elif upload_response.status_code == 200:
                            # Check for rejected shifts.
                            response = json.loads(upload_response.text)
                            if len(response["rejectedShifts"]) == 0:
                                print(f"200 - Base schedule ID {base_schedule_id} successfully updated.")
                                continue
                            
                            shifts_to_approve = []
                            for rejected_shift in response["rejectedShifts"]:
                                if "validationErrors" not in rejected_shift:
                                    continue
                                
                                rejected_shift["acceptedValidationErrors"] = []
                                for val_error in rejected_shift["validationErrors"]:
                                    rejected_shift["acceptedValidationErrors"].append({
                                        "message": val_error["message"],
                                        "severity": val_error["severity"],
                                        "additionalErrorParameters": val_error["additionalErrorParameters"]    
                                    })
                                
                                shifts_to_approve.append(rejected_shift)
                                
                            upload_response = http_with_retry(action=PUT, url=f"{url_single_base_schedule}{base_schedule_id}/shifts/batch", auth=HTTPBasicAuth(username, password), body=shifts_to_approve)
                            if upload_response.status_code > 201:
                                print(f"{upload_response.status_code} - Base schedule ID {base_schedule_id} could not update shifts with validation errors due to: {upload_response.reason}.")
                                continue

                            print(f"200 - Base schedule ID {base_schedule_id} successfully updated.")

                        else:
                            print(f"{upload_response.status_code} - Base schedule ID {base_schedule_id} failed up update due to: {upload_response.reason}.")
                            

    if apply_to_shift_types:
        print("################## Updating shift types ##################")
        already_updated_shift_types = []

        # These are all units and sections that shift types can exist on (shift types belonging to the domain will also be returned)
        for group in group_info_for_shift_types:
            
            shift_types_json = json.loads(http_with_retry(action=GET, url=f"{url_shift_types}{group}", auth=HTTPBasicAuth(username, password)).text)
            if "result" not in shift_types_json:
                continue
            
            for shift_type_partial in shift_types_json["result"]:
                shift_type_id = str(shift_type_partial["id"])

                if shift_type_id in already_updated_shift_types:
                    continue

                if shift_type_id not in shifttype_tag_table:
                    continue

                shift_type = json.loads(http_with_retry(action=GET, url=f"{url_shift_types}{group}/type/{shift_type_id}", auth=HTTPBasicAuth(username, password)).text)

                new_tag_ext_id = shifttype_tag_table[str(shift_type_id)]
                if new_tag_ext_id not in all_tags_table:
                    continue
                
                if "tags" not in shift_type:
                    shift_type["tags"] = []
                    
                if len(shift_type["tags"]) > 0:
                    for tag in shift_type["tags"]:
                        tag["id"] = all_tags_table[new_tag_ext_id]["id"]
                        tag["name"] = all_tags_table[new_tag_ext_id]["name"]
                        tag["tagCategory"]["id"] = all_tags_table[new_tag_ext_id]["categoryId"]
                        tag["tagCategory"]["name"] = all_tags_table[new_tag_ext_id]["categoryName"]
                        tag["tagCategory"]["color"] = all_tags_table[new_tag_ext_id]["categoryColor"]
                else:
                    shift_type["tags"].append({
                        "id": all_tags_table[new_tag_ext_id]["id"],
                        "name": all_tags_table[new_tag_ext_id]["name"],
                        "tagCategory": {
                            "id": all_tags_table[new_tag_ext_id]["categoryId"],
                            "name": all_tags_table[new_tag_ext_id]["categoryName"],
                            "color": all_tags_table[new_tag_ext_id]["categoryColor"]
                        }
                    })
                
                already_updated_shift_types.append(shift_type_id)

                put_back_result = http_with_retry(action=PUT, url=f"{url_shift_types}{group}/type/{shift_type_id}", auth=HTTPBasicAuth(username, password), body=shift_type)          

                if put_back_result.status_code == 200:
                    print(f"200 - Shift type ID {shift_type_id} was successfully updated.")
                elif put_back_result.status_code == 500:
                    print(f"500 - Shift type ID {shift_type_id} was not updated due to an Internal Server Error occurring several times in a row.")
                elif put_back_result.status_code == 401:
                    print(f"401 - Shift type ID {shift_type_id} was not updated as the request returned 'Unauthorized'.")
                elif put_back_result.status_code == 403:
                    print(f"403 - Shift type ID {shift_type_id} was not updated as the request returned 'Forbidden'.")
                elif put_back_result.status_code == 404:
                    print(f"404 - Shift type ID {shift_type_id} was not updated as the shift ID was not found in Quinyx.")
                else:
                    print(f"{put_back_result.status_code} - Shift type ID {shift_type_id} was not updated due to status: - {put_back_result.reason}\n{shift_type}.")

    if apply_to_schedule:
        if not dates_are_valid_format:
            print("One or both of 'fromDate' and 'toDate' are an invalid format. Schedule cannot be updated.")
            exit(0)
        
        print("################## Updating schedule ##################")
        updating_from_date = from_date
        
        while updating_from_date < to_date:
            updating_to_date = updating_from_date + timedelta(days=30)
            if updating_to_date > to_date:
                updating_to_date = to_date
            print(f"Updating {updating_from_date} - {updating_to_date}")
            
            for group in group_ids: 
                schedule_data = json.loads(http_with_retry(action=GET, url=f"{url_schedules}{group}?endDate={updating_to_date}T00:00:00Z&startDate={updating_from_date}T00:00:00Z", auth=HTTPBasicAuth(username, password)).text)
                for shift in schedule_data:
                    
                    if str(shift["shiftTypeId"]) not in shifttype_tag_table:
                        continue
                    
                    new_tag_ext_id = shifttype_tag_table[str(shift["shiftTypeId"])]
                    if new_tag_ext_id not in all_tags_table:
                        continue
                    
                    if "tags" in shift:
                        for tag in shift["tags"]:
                            tag["id"] = all_tags_table[new_tag_ext_id]["id"]
                            tag["name"] = all_tags_table[new_tag_ext_id]["name"]
                            tag["tagCategory"]["id"] = all_tags_table[new_tag_ext_id]["categoryId"]
                            tag["tagCategory"]["name"] = all_tags_table[new_tag_ext_id]["categoryName"]
                            tag["tagCategory"]["color"] = all_tags_table[new_tag_ext_id]["categoryColor"]
                    else:
                        shift["tags"] = []
                        shift["tags"].append({
                            "id": all_tags_table[new_tag_ext_id]["id"],
                            "name": all_tags_table[new_tag_ext_id]["name"],
                            "tagCategory": {
                                "id": all_tags_table[new_tag_ext_id]["categoryId"],
                                "name": all_tags_table[new_tag_ext_id]["categoryName"],
                                "color": all_tags_table[new_tag_ext_id]["categoryColor"]
                            }
                        })

                    put_back_result = http_with_retry(action=PUT, url=f"{url_put_schedules}{shift['id']}?ignoreValidationRules=true", auth=HTTPBasicAuth(username, password), body=shift)

                    if put_back_result.status_code == 200:
                        print(f"200 - Shift ID {shift['id']} was successfully updated.")
                    elif put_back_result.status_code == 500:
                        print(f"500 - Shift ID {shift['id']} was not updated due to an Internal Server Error occurring several times in a row.")
                    elif put_back_result.status_code == 401:
                        print(f"401 - Shift ID {shift['id']} was not updated as the request returned 'Unauthorized'.")
                    elif put_back_result.status_code == 403:
                        print(f"403 - Shift ID {shift['id']} was not updated as the request returned 'Forbidden'.")
                    elif put_back_result.status_code == 404:
                        print(f"404 - Shift ID {shift['id']} was not updated as the shift ID was not found in Quinyx.")
                    
                    elif put_back_result.status_code == 400:
                        errormessage = json.loads(put_back_result.text)
                        for error in errormessage:
                            if "message" in error:
                                if error["message"] in shift_error_action:
                                    action = shift_error_action[error["message"]]
                                    shift[action[0]] = action[1]
                                    put_back_result = http_with_retry(action=PUT, url=f"{url_put_schedules}{shift['id']}?ignoreValidationRules=true", auth=HTTPBasicAuth(username, password), body=shift)
                                elif error["message"] == "error.schedule.timepunch.approved":
                                    print(f"400 - Shift ID {shift['id']} was not updated. Its timepunch is approved.")
                                else:
                                    print(f"400 - Shift ID {shift['id']} was not updated due to an error message: {error['message']}")
                                    break
                    else:
                        print(f"{put_back_result.status_code} - Shift ID {shift['id']} was not updated due to status: {put_back_result.reason}.")

            updating_from_date = updating_to_date + timedelta(days=1)

    print("Script completed.")

if __name__ == "__main__":
    main()