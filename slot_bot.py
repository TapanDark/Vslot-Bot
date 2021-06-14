# INSTRUCTIONS:
# Fill in your telegram bot API key and group ID below.
# Fill in the password for your accounts. Assumption: All accounts use the same password.
# Create a file named "accounts.json" in the same folder as this script with the schema:
#{
#    "<consulate>" : [ <list of email account strings> ]
#}
# USAGE:
#  python slot_bot.py <consulate_name>

############### FILL THIS #####################
TELEGRAM_API_KEY="" # Docs: https://core.telegram.org/bots
SEND_ID = 0 # refer https://stackoverflow.com/questions/32423837/telegram-bot-how-to-get-a-group-chat-id
PASSWORD = "" # keep a common password for all accounts, or adjust code as needed.
CHROME_DRIVER_PATH = "" # download from https://chromedriver.chromium.org/downloads
###############################################

from selenium import webdriver
import re
import requests
import time
import pdb
import json
import sys


baseUrl = "https://api.telegram.org/bot{key}/{api}"
messageApi="sendMessage"

failCount = 0

# Fill in group id where the bot should send messages.

drivers = []

statusDict = {
    "last": None,
    "failure": False,
    "failCount": 0
}

# Used to tile windows neatly in a grid.
Y_POS ={
    "Mumbai" : 100,
    "Delhi": 400,
    "Chennai": 700,
    "Kolkata": 1000
}

def sendDebugMessage(consulate):
    if not statusDict["failure"]:
        sendTelegramMessage("%s Exception" % consulate, SEND_ID)
        statusDict["failure"] = True

def sendTelegramMessage(text, number):
    messageData = {'chat_id': number}
    url = baseUrl.format(key=TELEGRAM_API_KEY, api=messageApi)
    messageData["text"] = text
    resp = requests.post(url, data = messageData)
    print(resp.text)


def updateIfChanged(consulate, date):
    if not statusDict["last"] or statusDict["last"]  != date:
        statusDict["last"]  = date
        message =  "%s : %s" % (consulate, date)
        sendTelegramMessage(message, SEND_ID)

def sendUpdates(driver, consulate):
    driver.refresh()
    try:
        try:
            usernameelement = driver.find_element_by_class_name("username-display")
            if not usernameelement:
                if not statusDict["failure"]:
                    updateIfChanged(consulate, "Concurrency Error(possibly).")
                    statusDict["failure"] = True
                return True
        except Exception as e:
            statusDict["failCount"] += 1
            if not statusDict["failure"]:
                updateIfChanged(consulate, "Concurrency Error(possibly).")
            statusDict["failure"] = True
            return True
        element = None
        try:
            element = driver.find_element_by_class_name("leftPanelText")
        except Exception as e:
            updateIfChanged(consulate, "No Blue Box.")
        if element:
            data = element.text
            match = re.search("First Available Appointment Is (.*)", data)
            if match:
                updateIfChanged(consulate, match.group(1))
    except Exception as e:
        sendTelegramMessage("%s session %s logged out/frozen! Bot dead. X[" % (consulate, statusDict["failCount"]), SEND_ID)
        return False
    return True

if __name__ == "__main__":

    usernameBox = '//*[@id="loginPage:SiteTemplate:siteLogin:loginComponent:loginForm:username"]'
    passwordBox = '//*[@id="loginPage:SiteTemplate:siteLogin:loginComponent:loginForm:password"]'
    checkBox = '//*[@id="loginPage:SiteTemplate:siteLogin:loginComponent:loginForm:j_id131"]/table/tbody/tr[3]/td/label/input'

    CONSULATE = sys.argv[1]

    with open("accounts.json", "r") as fp:
        unameList = json.loads(fp.read())[CONSULATE]

    # BELOW Loop helps log in to the account while the site is under load.
    # Sorry for the messy code, this was hacked in at run-time when logins started failing.
    # Fill the captcha when the script pauses and type "c" to continue from pdb.
    # The script will validate the login and keep retrying.
    print("Enter captcha in browser window type \"c\" until done with all accounts.")
    for i in range(len(unameList)):
        driver = webdriver.Chrome(CHROME_DRIVER_PATH)
        driver.get('https://cgifederal.secure.force.com/?language=English&country=India')
        logged_in = False
        while not logged_in:
            while True:
                time.sleep(0.5)
                try:
                    usernameelement = driver.find_element_by_class_name("username-display")
                except Exception:
                    pass
                else:
                    logged_in = True
                    break
                try:
                    driver.find_element_by_xpath(usernameBox).send_keys(unameList.pop())
                except Exception:
                    driver.refresh()
                    time.sleep(2)
                else:
                    break
            try:
                usernameelement = driver.find_element_by_class_name("username-display")
            except Exception:
                pass
            else:
                logged_in = True
                break
            driver.find_element_by_xpath(passwordBox).send_keys(PASSWORD)
            driver.find_element_by_xpath(checkBox).click()
            import pdb;pdb.set_trace()
            driver.refresh()
        drivers.append(driver)
        time.sleep(2)

    for index, driver in enumerate(drivers):
        driver.set_window_size(300,400)
        driver.set_window_position(150*index,Y_POS[CONSULATE])

    print("Type c to start the bot.")
    import pdb
    pdb.set_trace()

    counter = 0
    while drivers:
        driver = drivers.pop(0)
        if sendUpdates(driver, CONSULATE):
            drivers.append(driver)
        time.sleep(30)
        counter+=1
        if counter == 60:
            counter = 0
            statusDict["failure"] = False
