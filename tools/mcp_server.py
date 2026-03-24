from fastmcp import FastMCP
import boto3
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Create FastMCP server
mcp = FastMCP("KORU Reports Server")


class S3Service:
    def __init__(self):
        self.bucket = os.getenv("S3_BUCKET_NAME")
        self.client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
    
    def list_files(self):
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket)
            if "Contents" not in response:
                return []
            return [obj["Key"] for obj in response["Contents"]]
        except Exception as e:
            print(f"Error listing S3 files: {e}")
            return []
    
    def download_file(self, key, local_path):
        try:
            self.client.download_file(self.bucket, key, local_path)
        except Exception as e:
            print(f"Error downloading file: {e}")
            raise


s3_service = S3Service()


@mcp.tool()
def list_reports() -> str:
    """List all available KORU reports from S3"""
    print("i got called")
    reports = s3_service.list_files()
    if not reports:
        return "No reports found"
    return "\n".join(reports)


@mcp.tool()
def analyze_report(report_name: str) -> str:
    """
    Analyze a KORU report and return metrics
    
    Args:
        report_name: Name of the report file (e.g., 'hyatt-koru-report.xlsx')
    """
    print("i can analyze i got called")
    try:
        # Ensure .xlsx extension
        if not report_name.endswith(".xlsx"):
            report_name += "-koru-report.xlsx"
        
        # Download report
        local_path = f"temp_{report_name}"
        s3_service.download_file(report_name, local_path)
        
        # Read Excel file
        sheets = pd.read_excel(
            local_path,
            sheet_name=None,
            engine="calamine",
            dtype=str
        )
        
        metrics = {
            "summary": {},
            "derived": {},
            "samples": {}
        }
        
        total_pages = 0
        total_clicks = 0
        total_tags = 0
        total_third_party = 0
        total_failed = 0
        vendors = {}
        
        for name, df in sheets.items():
            df = df.fillna("")
            lower = name.lower()
            
            # Sample data
            metrics["samples"][name] = df.head(10).to_dict(orient="records")
            
            # Extract metrics
            if "page" in lower:
                total_pages = max(total_pages, len(df))
            
            if "click" in lower:
                total_clicks = max(total_clicks, len(df))
            
            if "tag" in lower:
                total_tags = len(df)
                
                if "vendor" in df.columns:
                    vc = df["vendor"].value_counts().to_dict()
                    for k, v in vc.items():
                        vendors[k] = vendors.get(k, 0) + v
                
                if "status" in df.columns:
                    total_failed += len(df[df["status"] != "200"])
            
            if "3rd" in lower or "third" in lower:
                total_third_party = len(df)
        
        # Summary metrics
        metrics["summary"] = {
            "pages": total_pages,
            "clicks": total_clicks,
            "tag_requests": total_tags,
            "third_party_calls": total_third_party,
            "failed_requests": total_failed,
            "vendors": vendors
        }
        
        # Derived KPIs
        pages = total_pages or 1
        clicks = total_clicks or 1
        tags = total_tags or 1
        third = total_third_party or 1
        
        metrics["derived"] = {
            "tags_per_page": round(tags / pages, 2),
            "tags_per_click": round(tags / clicks, 2),
            "third_party_per_click": round(third / clicks, 2),
            "failure_rate_percent": round((total_failed / tags) * 100, 2) if tags > 0 else 0
        }
        
        # Clean up temp file
        if os.path.exists(local_path):
            os.remove(local_path)
        
        # Format response
        result = f"""
📊 KORU Report Analysis: {report_name}

📈 Summary:
• Pages Analyzed: {total_pages}
• Click Journeys: {total_clicks}
• Tag Requests: {total_tags}
• Third-Party Calls: {total_third_party}
• Failed Requests: {total_failed}

📊 Key Metrics:
• Tags per Page: {metrics['derived']['tags_per_page']}
• Tags per Click: {metrics['derived']['tags_per_click']}
• Third-Party per Click: {metrics['derived']['third_party_per_click']}
• Failure Rate: {metrics['derived']['failure_rate_percent']}%

🏢 Top Vendors:
"""
        # Add top 10 vendors
        sorted_vendors = sorted(vendors.items(), key=lambda x: x[1], reverse=True)[:10]
        for vendor, count in sorted_vendors:
            result += f"• {vendor}: {count} calls\n"
        
        return result
        
    except Exception as e:
        return f"Error analyzing report: {str(e)}"



if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001)
