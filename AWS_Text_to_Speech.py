import boto3
from parameter import aws_access_key, aws_secret_key, aws_bucket_name


polly_client = boto3.Session(
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name='us-west-2').client('polly')


input_file = 'Little_Red_Riding_Hood.txt'
audio_output_file = 'Little_Red_Riding_Hood.mp3'
word_timing_output_file = 'Little_Red_Riding_Hood.json'

with open('Little_Red_Riding_Hood.txt', 'r', encoding='utf-8') as file:
    text = file.readlines()

input_text = ' '.join(text)

input_text_to_AWS = "<speak><prosody rate='82%'>" + \
    input_text + "</prosody></speak>"


response_mp3 = polly_client.synthesize_speech(VoiceId='Emma',
                                              TextType='ssml',
                                              OutputFormat='mp3',
                                              Text=input_text_to_AWS,
                                              Engine='neural',
                                              )

response_json = polly_client.synthesize_speech(VoiceId='Emma',
                                               OutputFormat='json',
                                               TextType='ssml',
                                               Text=input_text,
                                               Engine='neural',
                                               SpeechMarkTypes=['word']
                                               )

file = open(audio_output_file, 'wb')
file.write(response_mp3['AudioStream'].read())
file.close()

print("MP3 file created")


file = open(word_timing_output_file, 'wb')
file.write(response_json['AudioStream'].read())
file.close()

print("Json file created")
