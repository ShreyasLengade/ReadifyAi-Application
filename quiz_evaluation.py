from langchain.prompts import (PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate,
                               AIMessagePromptTemplate, HumanMessagePromptTemplate)


from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import ResponseSchema
from langchain.output_parsers import StructuredOutputParser

from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationChain
import json
import boto3
import json
from datetime import datetime

import os
import random

from parameter import OpenAI_API_KEY, conn_params, aws_access_key, aws_secret_key, aws_bucket_name


polly_client = boto3.Session(
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name='us-west-2').client('polly')

session = boto3.Session(
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
)
s3_client = session.client('s3')
aws_bucket_name = aws_bucket_name


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
    s3_key = f'quiz/AI_voice/{title}/{current_date}/{time_stamp}.mp3'

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


def quiz_evaluation(submission):

    quiz_type = submission['Quiz_Type']
    question = submission['Question']
    user_age = submission['Quiz_AgeLevel']

    llm_quiz = ChatOpenAI(
        model="gpt-3.5-turbo", openai_api_key=OpenAI_API_KEY, temperature=0, max_tokens=1000)

    conversation_with_summary = ConversationChain(
        llm=llm_quiz,
        # We set a very low max_token_limit for the purposes of testing.
        memory=ConversationSummaryBufferMemory(
            llm=llm_quiz, max_token_limit=1600),
        verbose=True,
    )

    answer_schema = ResponseSchema(
        name="evaluation", description="Q & A Evaluation")
    follow_up_question_schema_1 = ResponseSchema(
        name="follow_up_question_1", description="Follow up question 1")
    follow_up_question_schema_2 = ResponseSchema(
        name="follow_up_question_2", description="Follow up question 2")
    follow_up_question_schema_3 = ResponseSchema(
        name="follow_up_question_3", description="Follow up question 3")

    response_schema = [answer_schema, follow_up_question_schema_1,
                       follow_up_question_schema_2, follow_up_question_schema_3]

    output_parser = StructuredOutputParser.from_response_schemas(
        response_schema)

    format_instructions = output_parser.get_format_instructions()

    general_instruction = f'You are an AI Teaching Assistant helping kids of age {user_age}.\n \
    You are evaluating quizes that they are working on.'

    if quiz_type == "multiple-choice":

        selected_choice = submission['selectedChoice']
        answer = submission['Answer']
        choice_1 = submission['Choice_1']
        choice_2 = submission['Choice_2']
        choice_3 = submission['Choice_3']
        choice_4 = submission['Choice_4']

        template_string = f'{general_instruction} quiz is of type {quiz_type}. \n The question is {question}. \n The answer choices for the question are \n \
        Choice 1: {choice_1} \n Choice 2: {choice_2} \n Choice 3: {choice_3} \n Choice 4: {choice_4}\n\
        The kids selected answer is: {selected_choice} \n \
        The Actual Answer is : {answer} \n \
        Evaluate this Q and A. The response should be encouraging and supportive. If the childs answer is correct\
        provide reason on why it is correct and why other choices are not. If appropriate provide example. If the childs answer is incorrect then gently say that the selected answer is incorrect in supportive manner explain why the answer is incorrect and explain correct answer.\
        After evaluation generate 3 follow up questions on topics related to the question, answer and answer choice. But follow up questions should not be repetitive \
        Also since the users are kids, at this moment they cannot type in the answer. \
        IMPORTANT: Consider kids age and your response should be appropriate for that age\
        and keep the follow up question short.\n{format_instructions}'

    if quiz_type == "true-false":

        selected_choice = submission['selectedChoice']
        answer = submission['Answer']
        choice_1 = submission['Choice_1']
        choice_2 = submission['Choice_2']

        template_string = f'{general_instruction} quiz is of type {quiz_type}. \n The question is {question}. \n \
        Choices given with question are Choice 1: {choice_1} and Choice 2: {choice_2} \
        The kids selected answer is: {selected_choice} \n \
        The Actual Answer is : {answer} \n \
        Evaluate this Q and A. The response should be encouraging and supportive. If the childs answer is correct\
        provide reason on why it is correct. If the childs answer is incorrect then gently say that the selected answer is incorrect\
        in supportive manner explain why the answer is incorrect and explain correct answer.\
        After evaluation generate 3 follow up questions on topics related to the question. But follow up questions should not be repetitive\
        Also since the users are kids, at this moment they cannot type in the answer. \
        IMPORTANT: Consider kids age and your response should be appropriate for that age\
        and keep the follow up question short.\n{format_instructions}'

    if quiz_type == "Follow-up":

        template_string = f'{general_instruction}. You generated follow up question for kids and they want know one answer to one of the question  you asked.  \n \
            {question}. Please responsd to their question and generate follow up question on topic being discussed\n{format_instructions}'

    print(template_string)

    output = conversation_with_summary.predict(input=template_string)

    cleaned_output_content = output.replace(
        "```json", "").replace("```", "")

    # Convert the list of dictionaries into a JSON object
    output_in_json = json.loads(cleaned_output_content)

    print(output_in_json)

    evaluation = output_in_json['evaluation']
    follow_up_question_1 = output_in_json['follow_up_question_1']
    follow_up_question_2 = output_in_json['follow_up_question_2']
    follow_up_question_3 = output_in_json['follow_up_question_3']

    title = 'Quiz'

    additional_info_evalutation = f" \nClick on the buttons below to know more about this topic."

    follow_up_q_additional_instruction = random.choice([
        " Hmm, Just a seccond. I would get that information for you.",
        " Let me find that out for you. I will be right back",
        " Interesting question! Let me find that out for you. I will be right back",
    ])

    output_in_json['evaluation_audio'] = generate_audio_with_polly(
        aws_bucket_name, evaluation, title, additional_info_evalutation)

    output_in_json['follow_up_question_1_audio'] = generate_audio_with_polly(
        aws_bucket_name, follow_up_question_1, title, follow_up_q_additional_instruction)

    output_in_json['follow_up_question_2_audio'] = generate_audio_with_polly(
        aws_bucket_name, follow_up_question_2, title, follow_up_q_additional_instruction)

    output_in_json['follow_up_question_3_audio'] = generate_audio_with_polly(
        aws_bucket_name, follow_up_question_3, title, follow_up_q_additional_instruction)

    return output_in_json
