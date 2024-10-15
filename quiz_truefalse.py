from langchain.prompts import (PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate,
                               AIMessagePromptTemplate, HumanMessagePromptTemplate)


from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import ResponseSchema
from langchain.output_parsers import StructuredOutputParser

from parameter import OpenAI_API_KEY, conn_params
from datetime import datetime

import json
import psycopg2


def quiz_truefalse(topic, additional_info, quiztype, agelevel, numquestions, userid):

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
    answer_schema = ResponseSchema(name="answer", description="Answer")

    response_schema = [question_number_schema,
                       question_schema,  answer_schema]

    output_parser = StructuredOutputParser.from_response_schemas(
        response_schema)

    format_instructions = output_parser.get_format_instructions()

    print(format_instructions)

    template_string = 'You are an AI Teaching Assistant Please generate a quiz for type {quiz_type} and the topic for quiz is {topic} and the additional info quiz are {additional_info}. The age of the student taking this quiz is {age_level}\'s old. The number of Question and Answer that needs to be generated is {number_of_question}. \nThe Answer should be either True or False.\n{format_instructions}'

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

    # Convert the list of dictionaries into a list of dictionaries
    output_in_json = json.loads(cleaned_output_content_in_list)

    print(json.dumps(output_in_json, indent=4))

    # Establishing the database connection
    conn = psycopg2.connect(**conn_params)

    # Create a cursor object
    cur = conn.cursor()

    # SQL query for inserting data
    insert_query = """
    INSERT INTO quiz_truefalse (quiz_topic, quiz_additional_info, quiz_agelevel, quiz_type, 
    question_number, question, choice_1, choice_2, answer, create_session_id,create_timestamp, user_id, approval_status)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    # Iterate over the JSON data and insert each entry into the database
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
                "True",
                "False",
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
