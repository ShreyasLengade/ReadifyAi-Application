from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import openai
from pydantic import BaseModel
import uvicorn
import boto3
from io import BytesIO
import json
import tempfile
from google.cloud import texttospeech_v1
from google.cloud import speech, texttospeech_v1
import os
from datetime import datetime, timezone
import psycopg2
from typing import Dict

from split_content_into_pages import insert_newlines
from split_content_into_pages import split_into_pages

from AWS import create_subfolder_in_s3
from AWS import save_string_to_s3_file

from parameter import OpenAI_API_KEY, conn_params, aws_access_key, aws_secret_key, aws_bucket_name

from quiz_mcq_creation import quiz_mcq_creation
from quiz_truefalse import quiz_truefalse
from conversation_history import insert_conversation_history
from quiz_evaluation import quiz_evaluation
from short_stories_fun_facts import gen_short_stroies_fun_facts, followup_question_response


class ChatRequest(BaseModel):  # Pydantic model for request body this is string in this case
    prompt: str


# Pydantic model for request body this is string in this case
class QuizGenerationRequest(BaseModel):
    topic: str
    additional_info: str
    quiztype: str
    agelevel: str
    numquestions: int
    userid: str


# Pydantic model for request body here it is JSON object interpreted as a dictionary.

class ClassMaterialRequest(BaseModel):
    newTitle: str
    newContent: str

# Define a Pydantic model for the data to be returned by the API endpoint


class Short_Story(BaseModel):
    short_stories_title: str
    story_page_num: str
    page_text_url: str
    image_url: str
    audio_url: str
    word_level_timing: str


class Short_Story_fun_facts(BaseModel):
    title: str
    page_detail: str


class Short_Story_fun_facts(BaseModel):
    title: str
    page_detail: str


# For Google Text-to-Speech
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gen-ai-tutor-0db5498380ef.json"


app = FastAPI()
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Initialize OpenAI
openai.api_key = OpenAI_API_KEY

# AWS credentials and the S3 bucket name.
access_key = aws_access_key
secret_key = aws_secret_key
bucket_name = aws_bucket_name

conn_params = conn_params

# Initialize a session using AWS credentials
session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
)

# Define the Client Session
s3_client = session.client('s3')

# AWS Polly client
polly_client = boto3.Session(
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name='us-west-2').client('polly')

speech_client = speech.SpeechClient()
client = texttospeech_v1.TextToSpeechClient()

# Define voice parameters
voice_params = texttospeech_v1.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Studio-Q",
    ssml_gender=texttospeech_v1.SsmlVoiceGender.MALE
)

# Define audio configuration
audio_config = texttospeech_v1.AudioConfig(
    audio_encoding=texttospeech_v1.AudioEncoding.MP3,
    speaking_rate=0.86,
    sample_rate_hertz=22050
)


@app.get("/")  # Root URL
def read_root():
    return {"message": "FastAPI backend server is running!"}


@app.post("/api/quiz-generation")
async def handle_teacher_request(quiz_generation_request: QuizGenerationRequest):

    topic = quiz_generation_request.topic
    additional_info = quiz_generation_request.additional_info
    quiztype = quiz_generation_request.quiztype
    agelevel = quiz_generation_request.agelevel
    numquestions = int(quiz_generation_request.numquestions)
    userid = quiz_generation_request.userid

    if quiztype == 'multiple-choice':

        return {'message': quiz_mcq_creation(topic, additional_info, quiztype, agelevel, numquestions, userid)}

    if quiztype == 'true-false':
        return {'message': quiz_truefalse(topic, additional_info, quiztype, agelevel, numquestions, userid)}

    # return {'message': 'Invalid quiz type'}

# Route to evaluate the quiz and respond to follow-up questions:


@app.post("/api/quiz-evaluation")
async def quiz_response(submission: Dict):

    print("Received quiz submission:", submission)

    ai_response = quiz_evaluation(submission)

    print("AI Response:", ai_response)

    return {"message": ai_response}


# Route to generate short stories fun facts:

@app.post("/api/short-stories-fun-facts")
async def handle_short_stories_fun_facts(story_details: Dict):
    print("Received story details:", story_details)

    ai_response = gen_short_stroies_fun_facts(story_details)

    print("AI Response:", ai_response)

    return {"message": ai_response}


@app.post("/api/short-stories-followup-question")
async def handle_short_stories_followup_question(question_details: Dict):

    print("Received story details:", question_details)

    ai_response = followup_question_response(question_details)

    print("AI Response:", ai_response)

    return {"message": ai_response}


@app.post("/api/interact")
async def handle_interact(chat_request: ChatRequest):
    prompt = chat_request.prompt
    # Thse values should come from the frontend
    userid = "Mary"
    app_section = ''
    book_or_material = ''
    chapter_or_page = ''
    conversation_content = prompt

    # Insert the conversation history into the database
    insert_conversation_history(userid=userid, speaker=userid, app_section=app_section,
                                book_or_material=book_or_material, chapter_or_page=chapter_or_page, conversation_content=conversation_content)

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a supportive AI tutor who is helping a student with reading book and helping build their comprehension skills, curiosity, and love for reading. Currently the app is getting built, so you might get the same questions over and over again. The target user group is 6-12 year olds. If user ask for meaning of a word, then provide meaning as well as synonyms where ever applicable. Provide examples of the word in a sentence. If the word has different meaning in different context, then provide example."},
                {"role": "user", "content": prompt},
            ],
        )

        gen_ai_response = response.choices[0].message.content.strip()

        # Write the AI's response to PostgreSQL
        ai_speaker = "AI Tutor"
        insert_conversation_history(userid=userid, speaker=ai_speaker, app_section=app_section,
                                    book_or_material=book_or_material, chapter_or_page=chapter_or_page, conversation_content=gen_ai_response)

        print(gen_ai_response)

        return {"message": gen_ai_response}
    except Exception as e:
        print(f"Error calling OpenAI: {e}")  # Log the detailed error
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/class-material-request")
async def handle_class_material(request: ClassMaterialRequest):
    ''' Text from the input will be sent to GCP Text-to-Speech API to generate audio files. and Audio files will be saved in S3 bucket. Also Word level timing information will be saved in JSON format in S3 bucket.'''

    # print(request.newTitle)
    # print(request.newContent)
    title = request.newTitle
    content = request.newContent

    existing_folder_prefix = 'class_material'
    full_file_name = title + '.txt'

    sub_folder_path = create_subfolder_in_s3(
        session, bucket_name, existing_folder_prefix, title)

    print("************")
    print(sub_folder_path)
    print("************")

    material_to_transcribe = title + '\n\n\t' + content

    # print(material_to_transcribe)

    save_string_to_s3_file(
        session, bucket_name, sub_folder_path, full_file_name, material_to_transcribe)

    pages = insert_newlines(
        material_to_transcribe, max_words=10)

    # print(pages)

    page_list = split_into_pages(
        pages, lines_per_page=30)

    for i, page_content in enumerate(page_list, start=1):
        # Format the subfolder name as 'Page XX'
        # Results in "Page 01/", "Page 02/", etc.
        page_folder_name = f"Page {i:02}"
        page_folder_path = sub_folder_path

        print(page_folder_path)
        print(page_folder_name)

        page_folder_created = create_subfolder_in_s3(
            session, bucket_name, page_folder_path, page_folder_name)
        print('####Page folder Created')
        print(page_folder_created)

        save_string_to_s3_file(session, bucket_name,
                               page_folder_created, page_folder_name+'.txt', page_content)

        # Prepare synthesis input
        synthesis_input = texttospeech_v1.SynthesisInput(text=page_content)

        # Create the SynthesizeSpeechRequest
        request = texttospeech_v1.SynthesizeSpeechRequest(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )

        # Synthesize speech
        response = client.synthesize_speech(request=request)

        audio_file_key = page_folder_created+page_folder_name+'.mp3'
        word_level_timings_file_key = page_folder_created+page_folder_name+'.json'

        # Convert the response's audio content to a BytesIO object
        audio_content = BytesIO(response.audio_content)

        # Prepare audio for transcription
        audio = speech.RecognitionAudio(content=response.audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MP3,
            sample_rate_hertz=22050,  # Ensure this matches the output of Text-to-Speech
            language_code="en-US",
            enable_word_time_offsets=True
        )

        # Transcribe the audio file
        operation = speech_client.long_running_recognize(
            config=config, audio=audio)
        print("Waiting for operation to complete...")
        response = operation.result(timeout=300)

        # Process word-level timing info.
        # Get the start and end times of each word in the transcription and store in a list
        word_timings = []
        for result in response.results:
            alternative = result.alternatives[0]
            for word_info in alternative.words:
                word_timings.append({
                    "word": word_info.word,
                    "start_time": word_info.start_time.total_seconds(),
                    "end_time": word_info.end_time.total_seconds()
                })

        # Upload the BytesIO object to S3
        s3_client.upload_fileobj(audio_content, bucket_name, audio_file_key)

        print(f"File uploaded to {bucket_name}/{audio_file_key}")

        # Convert word timings to JSON and upload to S3
        word_timings_json = json.dumps(word_timings)
        word_timings_io = BytesIO(word_timings_json.encode('utf-8'))

        s3_client.upload_fileobj(
            word_timings_io, bucket_name, word_level_timings_file_key)

        print(f"Transcription JSON uploaded to S3: \
              {bucket_name}{word_level_timings_file_key}")

        if i == len(page_list):
            return {"message": "Class material saved successfully!"}


@app.get("/api/conversations")
async def get_unique_userids():

    conn = psycopg2.connect(**conn_params)

    # Create a cursor object
    cur = conn.cursor()

    cur.execute(
        "SELECT DISTINCT userid FROM chat_conversation_history ORDER BY userid;")
    userids = cur.fetchall()

    print(userids)  # list of tuples
    print(type(userids))

    userids = [userid[0] for userid in userids]

    return userids


@app.get("/api/conversations/{userid}")
async def get_conversations(userid: str):

    conn = psycopg2.connect(**conn_params)

    # Create a cursor object
    cur = conn.cursor()

    cur.execute(
        "SELECT speaker ,conversation_content, conversation_timestamp  FROM chat_conversation_history WHERE userid = %s ORDER BY conversation_timestamp desc;", (userid,))
    rows = cur.fetchall()

    conversation = [
        # list of dictionaries. strftime() converts datetime object to string
        {'Speaker': row[0], 'Conversation': row[1], 'Time': row[2]} for row in rows]

    print(conversation)
    cur.close()
    conn.close()

    return conversation


@app.get("/api/quiz-topics")
async def get_unique_quiz_topic():

    conn = psycopg2.connect(**conn_params)

    # Create a cursor object
    cur = conn.cursor()

    # SQL query to select unique quiz topics from both tables
    query = """
        (SELECT quiz_topic FROM quiz_mcq)
        UNION  -- UNION removes duplicates
        (SELECT quiz_topic FROM quiz_truefalse);
        """
    cur.execute(query)
    results = cur.fetchall()

    print(results)  # list of tuples

    topics = [topic[0] for topic in results]

    return topics


@app.get("/api/quiz-topics/{topic}")
async def get_quiz(topic: str):

    conn = psycopg2.connect(**conn_params)

    # Create a cursor object
    cur = conn.cursor()

    # Query for quiz_mcq
    mcq_query = """
    SELECT question_number, quiz_topic, quiz_agelevel, quiz_type, question, choice_1, choice_2, choice_3, choice_4, answer,image_url, audio_url
    FROM quiz_mcq
    WHERE quiz_topic = %s;
    """
    # Execute the mcq_query
    cur.execute(mcq_query, (topic,))
    mcq_results = cur.fetchall()

    # Query for quiz_truefalse
    tf_query = """
    SELECT question_number, quiz_topic, quiz_agelevel, quiz_type, question, choice_1, choice_2, answer, image_url, audio_url
    FROM quiz_truefalse
    WHERE quiz_topic = %s;
    """
    # Execute the tf_query
    cur.execute(tf_query, (topic,))
    tf_results = cur.fetchall()

    # Close the cursor and connection
    cur.close()
    conn.close()

    mcq_list = [{'Question_ID': mcq[0],
                'Quiz_Topic': mcq[1],
                 'Quiz_AgeLevel': mcq[2],
                 'Quiz_Type': mcq[3],
                 'Question': mcq[4],
                 'Choice_1': mcq[5],
                 'Choice_2': mcq[6],
                 'Choice_3': mcq[7],
                 'Choice_4': mcq[8],
                 'Answer': mcq[9],
                 'Image_URL': mcq[10],
                 'Audio_URL': mcq[11]} for mcq in mcq_results]

    tf_list = [{'Question_ID': tf[0],
               'Quiz_Topic': tf[1],
                'Quiz_AgeLevel': tf[2],
                'Quiz_Type': tf[3],
                'Question': tf[4],
                'Choice_1': tf[5],
                'Choice_2': tf[6],
                'Answer': tf[7],
                'Image_URL': tf[8],
                'Audio_URL': tf[9]} for tf in tf_results]

    quiz_list = mcq_list + tf_list

    return quiz_list


@app.get("/api/short-stories/{story_title}", response_model=list[Short_Story])
async def get_short_story(story_title: str):

    print(story_title)

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    try:
        # Query to get short stories by title
        short_story_query = """
            SELECT 
                short_stories_title, 
                story_page_num, 
                page_text_url, 
                image_url, 
                audio_url, 
                word_level_timing 
            FROM 
                short_stories 
            WHERE 
                short_stories_title = %s
            ORDER BY 
                CAST(story_page_num AS INTEGER) ASC;
        """

        # Execute the query
        cur.execute(short_story_query, (story_title,))
        short_story_result = cur.fetchall()

        print(short_story_result)
        print(type(short_story_result))

        # Convert tuples to a list of dictionaries
        short_story_dicts = [
            {
                "short_stories_title": story[0],
                "story_page_num": story[1],
                "page_text_url": story[2],
                "image_url": story[3],
                "audio_url": story[4],
                "word_level_timing": story[5]
            }
            for story in short_story_result
        ]

        # Return list of dictionaries

        # Handle empty results
        if not short_story_result:
            raise HTTPException(status_code=404, detail="Story not found")

        # Close the connection before returning the data
        cur.close()
        conn.close()

        return short_story_dicts

    finally:
        # Ensure the connection is always closed
        conn.close()


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=3000)  # for Local Testing
