from langchain.prompts import (PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate,
                               AIMessagePromptTemplate, HumanMessagePromptTemplate)
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import ResponseSchema
from langchain.output_parsers import StructuredOutputParser

from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationChain
import json
from datetime import datetime
import boto3
import os
import random

from parameter import aws_access_key, aws_secret_key, aws_bucket_name, OpenAI_API_KEY


polly_client = boto3.Session(
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name='us-west-2').client('polly')

session = boto3.Session(
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
)
s3_client = session.client('s3')


llm_quiz = ChatOpenAI(
    model="gpt-3.5-turbo", openai_api_key=OpenAI_API_KEY, temperature=0.2, max_tokens=2000)

conversation_with_summary = ConversationChain(
    llm=llm_quiz,
    # We set a very low max_token_limit for the purposes of testing.
    memory=ConversationSummaryBufferMemory(
        llm=llm_quiz, max_token_limit=2600),
    verbose=True,
)


def generate_audio_with_polly(aws_bucket_name, input_text, title, additional_info):
    # Generate current date and timestamp
    current_date = datetime.now().strftime('%Y-%m-%d')
    time_stamp = datetime.now().strftime('%H-%M-%S-%f')

    additional = additional_info

    input_text_to_AWS = f"<speak><prosody rate='84%'>" + \
        input_text + additional + "</prosody></speak>"

    response_mp3 = polly_client.synthesize_speech(VoiceId='Emma',
                                                  TextType='ssml',
                                                  OutputFormat='mp3',
                                                  Text=input_text_to_AWS,
                                                  Engine='neural',
                                                  )

    # Generate a unique local filename
    local_directory = f'{title}/fact/{current_date}'
    local_filename = f'{local_directory}/{time_stamp}.mp3'

    # Ensure the directory exists
    os.makedirs(local_directory, exist_ok=True)

    with open(local_filename, 'wb') as audio_file:
        audio_file.write(response_mp3['AudioStream'].read())

    # Generate a unique S3 object key
    s3_key = f'short_stories/AI_voice/{title}/{current_date}/{time_stamp}.mp3'

    # Upload to S3 and return the URL
    try:
        s3_client.upload_file(local_filename, aws_bucket_name, s3_key)
        s3_url = f'https://{aws_bucket_name}.s3.eu-west-1.amazonaws.com/{s3_key}'
    except Exception as e:
        print(f'Error uploading file to S3: {e}')
        return None

    # Clean up local file after upload
    os.remove(local_filename)

    return s3_url


def gen_short_stroies_fun_facts(stroy_details):
    fun_fact_schema = ResponseSchema(name='fun_fact', description='Fun Facts')
    follow_up_question_schema_1 = ResponseSchema(
        name="follow_up_question_1", description="Follow up question 1")
    follow_up_question_schema_2 = ResponseSchema(
        name="follow_up_question_2", description="Follow up question 2")

    response_schema = [fun_fact_schema, follow_up_question_schema_1,
                       follow_up_question_schema_2]

    output_parser = StructuredOutputParser.from_response_schemas(
        response_schema)

    format_instructions = output_parser.get_format_instructions()

    title = stroy_details['title']
    page_detail = stroy_details['page_detail']
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    general_instruction = f'You are an AI Teaching App helping kids under the age to six.\nCurrently they are reading a famous short story and\
        the title is {title}.\nThis is the page text that is currently being read: {page_detail}. The current date and time is {timestamp}.'

    additional_instruction = random.choice([
        "Make sure to provide a new fun fact that hasn't been mentioned before. First look at the page text and generate a fun fact based on that. If you can't find anything in the page text, then generate a fun fact based on the title of the story.",
        "Provide a fun fact that is unique and not repetitive. First look at the page text and generate a fun fact based on that. If you can't find anything in the page text, then generate a fun fact based on the title of the story.",
        "Generate a fun fact and ensure it's different from previous ones. First look at the page text and generate a fun fact based on that. If you can't find anything in the page text, then generate a fun fact based on the title of the story."
    ])

    template_string = f'{general_instruction} {additional_instruction} You need to generate one fun fact followed by which generate 2\
    follow up questions on topic related to page text or fun fact.\n \
    Start fun fact with phrase [Did you know ] If the story or page text mentions particular animal or place or nouns\
    then get fun facts and follow up questions about fun facts. \
    Donot discuss about the original version of story as they could be dark and not appropriate of kids.\
    IMPORTANT: Generate fun facts that would be appropriate for kids age and interesting to kids, is informational and builds there general knowlegde.\
    IMPORTANT: Please follow the schema instructions for generating the response. If not then downstream will error out.\
    \n{format_instructions}'

    output = conversation_with_summary.predict(input=template_string)

    print(output)

    cleaned_output_content = output.replace(
        "```json", "").replace("```", "").replace(',\n}', '}')

    print(cleaned_output_content)

    # Convert the list of dictionaries into a JSON object
    output_in_json = json.loads(cleaned_output_content)
    print("type of output_in_json", type(output_in_json))

    # Generate audio files
    fun_fact_text = output_in_json['fun_fact']
    follow_up_question_1_text = output_in_json['follow_up_question_1']
    follow_up_question_2_text = output_in_json['follow_up_question_2']

    fun_fact_additional = " Would you like to know more interesting facts then Click on the buttons to know more fun facts!"

    follow_up_q_additional_instruction = random.choice([
        "Hmm, Just a seccond. I would get that information for you.",
        "Let me find that out for you. I will be right back",
        "Interesting question! Let me find that out for you. I will be right back",
    ])

    # Add audio URLs to the JSON response
    output_in_json['fun_fact_audio_url'] = generate_audio_with_polly(
        aws_bucket_name, fun_fact_text, title, fun_fact_additional)
    output_in_json['follow_up_question_1_audio_url'] = generate_audio_with_polly(
        aws_bucket_name, follow_up_question_1_text, title, follow_up_q_additional_instruction)
    output_in_json['follow_up_question_2_audio_url'] = generate_audio_with_polly(
        aws_bucket_name, follow_up_question_2_text, title, follow_up_q_additional_instruction)
    print(output_in_json)

    return output_in_json


def followup_question_response(question_detail):
    title = question_detail['title']
    question = question_detail['question']
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    general_instruction = f'You are an AI Teaching App helping kids under the age to six.\nCurrently they are reading a famous short story and\
        the title is {title}.\nThe current date and time is {timestamp}.'

    question_response_schema = ResponseSchema(
        name='fun_fact', description='Fun Facts')
    follow_up_question_schema_1 = ResponseSchema(
        name="follow_up_question_1", description="Follow up question 1")
    follow_up_question_schema_2 = ResponseSchema(
        name="follow_up_question_2", description="Follow up question 2")

    response_schema = [question_response_schema, follow_up_question_schema_1,
                       follow_up_question_schema_2]

    output_parser = StructuredOutputParser.from_response_schemas(
        response_schema)

    format_instructions = output_parser.get_format_instructions()

    template_string = f'{general_instruction}. You are generated a follow up question and the kid is asking answer.\
    The question is {question}. First generate a response for this question.\
    After that generate 2 follow up questions on topic related to the question, and stroy being read. \
    Donot discuss about the original version of story as they could be dark and not appropriate of kids.\
    IMPORTANT: Generate response that would be appropriate for kids age and interesting to kids and builds there general knowlegde. \
    IMPORTANT: Please follow the schema instructions for generating the response. If not then downstream will error out.\
    \n{format_instructions}'

    output = conversation_with_summary.predict(input=template_string)

    print(output)

    cleaned_output_content = output.replace(
        "```json", "").replace("```", "").replace(',\n}', '}')

    print(cleaned_output_content)

    fun_fact_additional = " For more facts Click on the buttons below."

    follow_up_q_additional_instruction = random.choice([
        "Just a seccond. I would get that information for you.",
        "Let me find that out for you.",
        "Interesting question! I will be right back",
        "Just a second, I will find that out for you."
    ])

    # Convert the list of dictionaries into a JSON object
    output_in_json = json.loads(cleaned_output_content)

    # Generate audio files
    fun_fact_text = output_in_json['fun_fact']
    follow_up_question_1_text = output_in_json['follow_up_question_1']
    follow_up_question_2_text = output_in_json['follow_up_question_2']

    # Add audio URLs to the JSON response
    output_in_json['fun_fact_audio_url'] = generate_audio_with_polly(
        aws_bucket_name, fun_fact_text, title, fun_fact_additional)
    output_in_json['follow_up_question_1_audio_url'] = generate_audio_with_polly(
        aws_bucket_name, follow_up_question_1_text, title, follow_up_q_additional_instruction)
    output_in_json['follow_up_question_2_audio_url'] = generate_audio_with_polly(
        aws_bucket_name, follow_up_question_2_text, title, follow_up_q_additional_instruction)
    print(output_in_json)

    return output_in_json
