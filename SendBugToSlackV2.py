from flask import Flask
import json, boto3, requests,sched, time
 

app = Flask(__name__)
app.config["DEBUG"] = True

AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''

##RETRIEVE SECRETS FROM SECRET MANAGER##
client = boto3.client('secretsmanager', region_name = 'us-east-1', aws_access_key_id = AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

##SQS SECRETS##
responseSQS = client.get_secret_value( 
    SecretId = 'SQS_QueueURL'
)
jsonSQS = json.loads(responseSQS['SecretString'])
Queue_url = jsonSQS['SQS_Queue']

##TRELLO SECRETS##
responseTrello = client.get_secret_value(
    SecretId = 'TrelloCredentials'
)
jsonTrello = json.loads(responseTrello['SecretString'])

trello_url = jsonTrello['trello_url']
trello_token = jsonTrello['trello_token']
trello_key = jsonTrello['trello_key']
trello_idList = jsonTrello['trello_idList']

##SLACK SECRETS##
responseSlack = client.get_secret_value(
    SecretId = 'SlackWebHookURL'
)
jsonSlack = json.loads(responseSlack['SecretString'])
SlackWebHookURL = jsonSlack['slackWebHook']

##SQS Queue Connections##
sqs = boto3.client('sqs', region_name='us-east-1', aws_access_key_id = AWS_ACCESS_KEY , aws_secret_access_key=AWS_SECRET_KEY)
queue_url = Queue_url


s = sched.scheduler(time.time, time.sleep) #Scheduler 

@app.route('/', methods=['POST'])
def dequeue_message(): #recieve message from SQS Queue       
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

    messageAsDictionary = response #Convert message to dictionary
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
    sqs.delete_message( #Delete message from Queue
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

    

