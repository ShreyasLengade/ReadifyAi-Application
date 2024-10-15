import boto3
from botocore.exceptions import NoCredentialsError


def upload_file_to_s3(access_key, secret_key, bucket_name, file_name, object_name=None):
    """
    Upload a file to an S3 bucket

    :param access_key: String. Your AWS Access Key ID
    :param secret_key: String. Your AWS Secret Access Key
    :param bucket_name: String. The name of the bucket to upload to
    :param file_name: String. File to upload
    :param object_name: String. S3 object name. If not specified, file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Initialize a session using AWS credentials
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    # Create an S3 client using the session
    s3_client = session.client('s3')

    # Try to upload the file
    try:
        response = s3_client.upload_file(file_name, bucket_name, object_name)
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except Exception as e:
        print(f"Failed to upload {object_name} to {bucket_name}: {e}")
        return False
    return True


def create_subfolder_in_s3(session, bucket_name, folder_prefix, subfolder_title):
    s3 = session.client('s3')

    # Ensure the folder prefix ends with a '/'
    if not folder_prefix.endswith('/'):
        folder_prefix += '/'

    # Construct the full path for the new subfolder
    subfolder_path = f"{folder_prefix}{subfolder_title}/"

    # Create the subfolder by uploading an empty object
    s3.put_object(Bucket=bucket_name, Key=subfolder_path, Body=b'')

    print(f"Subfolder '{subfolder_path}' created in bucket '{bucket_name}'.")

    return subfolder_path


def save_string_to_s3_file(session, bucket_name, subfolder_path, file_name, string_data):
    s3 = session.client('s3')

    # Ensure the subfolder path ends with a '/'
    if not subfolder_path.endswith('/'):
        subfolder_path += '/'

    # Full path where the text file will be saved
    full_file_path = f"{subfolder_path}{file_name}"

    # Uploading the string_data as a text file to S3
    s3.put_object(Bucket=bucket_name, Key=full_file_path, Body=string_data)

    print(f"File '{full_file_path}' saved in bucket '{bucket_name}'.")
