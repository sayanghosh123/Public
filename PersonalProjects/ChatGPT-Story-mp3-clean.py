#Required for the Open AI text generation
import openai

#Required for the text to speech conversion using Azure Cognitive Services
import azure.cognitiveservices.speech as speechsdk
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

#Required for saving the file to Google Drive
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os.path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

#Parameters
openai_prompt = "Please make up a long format poem story based on the characters from lord of the rings. Including Frodo, Gandalf, lLegolas, Aragorn, Gimli, and Sam. Also include new hero - a 5 year boy called *, and his friends - *, *, *. Have a guest appearance from Ninjago heroes, and include a very special funny elephant named * in a red hat who will get multiple comic relief mentions."
file_name = "LOTR_2.mp3"
output_file_name = "C:/Users/*****/" + file_name

# configure the script to use your specific commands
# keyvault_url - this is the specific URL of your Azure Key Vault where you will store your Gmail username and app password 
keyvault_url = "https://***.vault.azure.net/"
azure_region = "australiaeast"

# account credentials and other configs
# replace with you Gmail username and password reading from Azure Key Vault
credential = DefaultAzureCredential(additionally_allowed_tenants=['*'])
secret_client = SecretClient(vault_url=keyvault_url, credential=credential)

#Secrets
openai_api_key = secret_client.get_secret("openaiapikey")
azure_speech_sub_key = secret_client.get_secret("azurespeechsubkey")

#Function to get response from OpenAI
def get_openai_response(input_text, openai_api_key):
  openai.api_key = openai_api_key.value
  response = openai.Completion.create(
    engine="text-davinci-002",
    prompt=input_text,
    temperature=0.5,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=1,
    presence_penalty=1
  )
  return response.choices[0].text

#Function to get response from Azure Speech
def convert_text_to_speech(input_text, azure_speech_sub_key, azure_region, output_file_name):
    speech_config = speechsdk.SpeechConfig(subscription=azure_speech_sub_key.value, region=azure_region)
    speech_config.speech_synthesis_language ='en-AU'
    speech_config.speech_synthesis_voice_name='en-AU-WilliamNeural'
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file_name)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
   
    speech_synthesis_result = synthesizer.speak_text_async(input_text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized successfully.")
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values correctly?")


#Function to store the file in Google Drive
def store_google_drive(output_file_name, file_name):
  # If modifying these scopes, delete the file token.json.
  SCOPES = ['https://www.googleapis.com/auth/drive']
  CREDENTIALS_FILE = 'credentials.json'
  # Set up the authorization credentials
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists('token.json'):
      creds = Credentials.from_authorized_user_file('token.json', SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
          creds.refresh(Request())
      else:
          flow = InstalledAppFlow.from_client_secrets_file(
              CREDENTIALS_FILE, SCOPES)
          creds = flow.run_local_server(port=0)
      # Save the credentials for the next run
      with open('token.json', 'w') as token:
          token.write(creds.to_json())
  try:
    # Build the Drive API client
    service = build('drive', 'v3', credentials=creds)

  # Find the folder named "Stories" which is the target folder
    query = "mimeType='application/vnd.google-apps.folder' and trashed = false and name='ChildName'"
    results = service.files().list(q=query, fields="nextPageToken, files(id, name)").execute()
    parent_folder_id = results.get("files", [])[0]["id"]

    # Find the folder named "Stories" inside the "ChildName" folder
    query = "mimeType='application/vnd.google-apps.folder' and trashed = false and '"+ parent_folder_id +"' in parents and name='Stories'"
    results = service.files().list(q=query, fields="nextPageToken, files(id, name)").execute()
    folder_id = results.get("files", [])[0]["id"]

    
    # Define the file metadata
    file_metadata = {
      'name': file_name,
      'mimeType': 'audio/mpeg',
      'parents': [folder_id]
    }

    # Read the file content
    media = MediaFileUpload(output_file_name, mimetype='audio/mpeg', resumable=True)

    # Create the file in the "Stories" folder
    file = service.files().create(body=file_metadata, media_body=media).execute()
    print(F'File with ID: "{file.get("id")}" has been added to the "Stories" folder.')

  except HttpError as error:
          # TODO(developer) - Handle errors from drive API.
          print(f'An error occurred: {error}')

#Tests
#Run the function to get the input from OpenAI
openai_response = get_openai_response(openai_prompt, openai_api_key)
#print the result as it is useful to validate the output before sharing it with children
print(openai_response)

#Run the function to get the results from Azure Speech
convert_text_to_speech(openai_response, azure_speech_sub_key, azure_region, output_file_name)

#Store the generated MP3 file in Google Drive
store_google_drive(output_file_name, file_name)