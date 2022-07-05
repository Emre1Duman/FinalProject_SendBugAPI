from flask import Flask
import json, botocore, botocore.session, boto3, requests,sched, time
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig 


app = Flask(__name__)
app.config["DEBUG"] = True


##RETRIEVE SECRETS FROM SECRET MANAGER##
client = botocore.session.get_session().create_client('secretsmanager')
cache_config = SecretCacheConfig()
cache = SecretCache( config = cache_config, client = client)

##AWS SECRETS##
AWSKeySecret = cache.get_secret_string('AWS_Keys') #Retrieve AWS secret
jsonAWS = json.loads(AWSKeySecret) #jsonify secrets

AWS_ACCESS_KEY = jsonAWS['AWS_Access_Key']
AWS_SECRET_KEY = jsonAWS['AWS_Secret_Key']

##SQS SECRETS##
SQSSecret = cache.get_secret_string('SQS_QueueURL') 
jsonSQS = json.loads(SQSSecret)

SQS_Queue = jsonSQS['SQS_Queue']

##TRELLO SECRETS##
trelloSecret = cache.get_secret_string('TrelloCredentials') 
jsonTrello = json.loads(trelloSecret) 

trello_url = jsonTrello['trello_url']
trello_token = jsonTrello['trello_token']
trello_key = jsonTrello['trello_key']
trello_idList = jsonTrello['trello_idList']

##SLACK SECRETS##
slackSecret = cache.get_secret_string('SlackWebHookURL') 
jsonSlack = json.loads(slackSecret) 

SlackWebHookURL = jsonSlack['slackWebHook'] 

##Queue Connections##
sqs = boto3.client('sqs', region_name='us-east-1', aws_access_key_id = AWS_ACCESS_KEY , aws_secret_access_key=AWS_SECRET_KEY)
queue_url = SQS_Queue


s = sched.scheduler(time.time, time.sleep) #Scheduler 

@app.route('/', methods=['POST'])
#recieve message from SQS Queue
def dequeue_message():       
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp',
              
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'name',
            'priority'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )

    messageAsDictionary = response
    if 'Messages' in messageAsDictionary:
        message = messageFormatter(response)    
        
    

def messageFormatter(response): #Formating message so it only sends the bug name and priority
    message = response['Messages'][0]
    print(message)
    messageAtrributes = message['MessageAttributes']
    
    if messageAtrributes['priority']['StringValue'] == "high":
        Send_slack_message("Warning! New Bug! Priority: " + messageAtrributes['priority']['StringValue'] + ", Bug Message: " + messageAtrributes['name']['StringValue'])
    else: #messageAtrributes['priority']['StringValue'] == "low" or messageAtrributes['priority']['StringValue'] == "medium":
        create_trello_card("New Bug! Priority: " + messageAtrributes['priority']['StringValue'], messageAtrributes['name']['StringValue'])
    
        
    receipt_handle = message['ReceiptHandle']
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )
    

##Function to send messages to Slack##
def Send_slack_message(Slack_message):
    payload = '{"text":"%s"}' % Slack_message
    response = requests.post(SlackWebHookURL, data=payload)
    print(response.text)

##Fucntion to send messages to Trello##
def create_trello_card(card_name, card_desc):
    trello_Obj = {"key":trello_key,"token":trello_token,"idList":trello_idList, "name":card_name,"desc":card_desc} #jsonObj
    new_card = requests.post(trello_url,json=trello_Obj)
 
##Main function calling all the others##
def main(sc):
    dequeue_message()
    s.enter(1, 1, main, (sc,)) #Scheduler
s.enter(1, 1, main, (s,)) #Scheduler
s.run()


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)

    

