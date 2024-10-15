from langchain.prompts import (PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate,
                               AIMessagePromptTemplate, HumanMessagePromptTemplate)


from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import ResponseSchema
from langchain.output_parsers import StructuredOutputParser

from parameter import OpenAI_API_KEY, conn_params
from datetime import datetime

import json
import psycopg2


def quiz_mcq_creation(topic, additional_info, quiztype, agelevel, numquestions, userid):

    topic = topic
    additional_info = additional_info
    if len(additional_info) == 0:
        additional_info = "None"
    quiz_type = quiztype
    age_level = agelevel
    number_of_question = numquestions
    userid = userid

    now = datetime.now()
    current_time = now.strftime("%d_%m_%y_%H_%M_%S_")

    create_session_id = current_time + userid

    chat = ChatOpenAI(openai_api_key=OpenAI_API_KEY, temperature=0)

    # Define the response schema
    question_number_schema = ResponseSchema(
        name="question number", description="Question number in the quiz set")
    question_schema = ResponseSchema(name="question", description="Question")
    choice_1_schema = ResponseSchema(name="choice 1", description="Option one")
    choice_2_schema = ResponseSchema(name="choice 2", description="Option two")
    choice_3_schema = ResponseSchema(
        name="choice 3", description="Option three")
    choice_4_schema = ResponseSchema(
        name="choice 4", description="Option four")
    answer_schema = ResponseSchema(name="answer", description="Answer")

    response_schema = [question_number_schema, question_schema, choice_1_schema,
                       choice_2_schema, choice_3_schema, choice_4_schema, answer_schema]

    output_parser = StructuredOutputParser.from_response_schemas(
        response_schema)

    format_instructions = output_parser.get_format_instructions()

    print(format_instructions)

    template_string = 'You are an AI Teaching Assistant Please generate a quiz for type {quiz_type} and the topic for quiz is {topic} and the additional info quiz are {additional_info}. The age of the student taking this quiz is {age_level}\'s old. The number of Question and Answer that needs to be generated is {number_of_question}. \nThe Answer should be the choice number and should be either 1 ,2, 3 or 4.\n{format_instructions}'

    prompt = ChatPromptTemplate.from_template(template=template_string)

    messages = prompt.format_messages(quiz_type=quiz_type, topic=topic, additional_info=additional_info, age_level=age_level,
                                      number_of_question=number_of_question, format_instructions=format_instructions)

    response = chat(messages)

    output_content = response.content

    print(output_content)
    # Remove the ```json``` and ``` from the output
    cleaned_output_content = output_content.replace(
        "```json", "").replace("```", "")

    # Remove the newline characters from the output
    cleaned_output_content = cleaned_output_content.replace("\n", "")

    print(cleaned_output_content)

    # Split the output content into a list of dictionaries
    cleaned_output_content_in_list = "[" + \
        cleaned_output_content.replace("}{", "},{") + "]"

    print(cleaned_output_content_in_list)

    # Convert the list of dictionaries into a JSON object
    output_in_json = json.loads(cleaned_output_content_in_list)

    print(json.dumps(output_in_json, indent=4))

    # Establishing the database connection
    conn = psycopg2.connect(**conn_params)

    # # Create a cursor object
    cur = conn.cursor()

    insert_query = """
INSERT INTO quiz_mcq (quiz_topic, quiz_additional_info, quiz_agelevel, quiz_type, 
question_number, question, choice_1, choice_2, choice_3, choice_4, answer, create_session_id,
create_timestamp, user_id, approval_status)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

# Iterate over the JSON data and insert each entry into the database
    try:
        for item in output_in_json:
            cur.execute(insert_query, (
                topic,
                additional_info,
                age_level,
                quiz_type,
                # Make sure this key exists in your items
                item["question number"],
                item["question"],
                item["choice 1"],  # And these keys too
                item["choice 2"],
                item["choice 3"],
                item["choice 4"],
                item["answer"],
                create_session_id,
                now,  # Ensure 'now' is defined and formatted correctly
                userid,
                "Pending"
            ))
        conn.commit()  # Commit the transaction to save the inserts
    except Exception as e:
        print("An error occurred:", e)
        conn.rollback()  # Rollback in case of error

    # Commit the transaction
    conn.commit()

    # Close the cursor and connection
    cur.close()
    conn.close()

    print("Data inserted successfully.")
    print(output_in_json)

    return output_in_json
