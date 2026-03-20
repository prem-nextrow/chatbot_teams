from fastmcp import FastMCP
import boto3
import os
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()
mcp = FastMCP(name="Teams Mcp")

try:
    s3 = boto3.client(
        service_name='s3',
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
except Exception as e:
    print(f"Unable to connect to S3: {str(e)}")


@mcp.tool()
def list_files() -> list[str]:
    """
    Lists all available files in the S3 bucket.
    Call this when the user asks what files are available, 
    or before fetching content to find the correct filename.
    """
    bucket = os.getenv("S3_BUCKET_NAME")
    obj = s3.list_objects_v2(Bucket=bucket)
    contents = obj.get("Contents", [])
    return [file["Key"] for file in contents]


@mcp.tool()
def get_content(filename: str) -> list[dict]:

    """
    Retrieves and parses an Excel file from S3 by its filename.
    Returns the file content as a list of row records.
    Call list_files first if you are unsure of the exact filename.
    
    Args:
        filename: The exact S3 key/filename e.g. 'chevy-report.xlsx'
    """

    bucket = os.getenv("S3_BUCKET_NAME")

    try:
        res = s3.get_object(Bucket=bucket, Key=filename)
        file_bytes = res["Body"].read()
        df = pd.read_excel(BytesIO(file_bytes), engine="calamine")
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}
    



if __name__ == "__main__":
    mcp.run()