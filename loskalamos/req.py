#author: sspsk, 2020
#function and HTMLParser object to send sms using web2sms/cosmote

import requests
from html.parser import HTMLParser

#function to send message to phone number
#arguments: HTMLParser object,username,password,phone,message
def send(parser,username,password,phone,msg):
    #open session to keep tokens
    s = requests.Session()
    login_token = None
    send_token = None

    #get token to login
    r = s.get('https://corpmail.otenet.gr/')

    print("parsing...")
    parser.feed(r.text)
    login_token = TokenParser.token
    print("login token: ",login_token)

    #post token and user, pass
    payload = {'_token':login_token,'_task':'login','_action':'login','_timezone':'_default_','_user':username,'_pass':password}
    r = s.post('https://corpmail.otenet.gr/',data=payload)

    #get token to send sms
    payload = {'_task':'websms','_action':'plugin.websms_compose_send'}
    r = s.get('https://corpmail.otenet.gr',params=payload)

    print("parsing...")
    parser.feed(r.text)
    send_token = TokenParser.token
    print("send token: ",send_token)

    #post token and send the sms
    payload = {'_token':send_token,'_to':phone,'_message':msg}
    r = s.post('https://corpmail.otenet.gr/?_task=websms&_action=plugin.websms_compose_send',data=payload)

    #logout
    print("logging out...")
    payload = {'_task':'logout'}
    r = s.get('https://corpmail.otenet.gr',params=payload)


#override methods of parser
class TokenParser(HTMLParser):
    token = None
    def handle_starttag(self,tag,attrs):
        if tag == "input":
            for i in range(len(attrs)):
                if attrs[i][1] == '_token':
                    TokenParser.token = attrs[i+1][1]

#example usage
# myparser = TokenParser()
# send(myparser,<username>,<password>,'+3069xxxxxxxx','test message')
