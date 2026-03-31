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
    Analyze a KORU report and return comprehensive metrics for executive summary
    
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
            "analytics": {},
            "media": {},
            "governance": {},
            "maturity": {},
            "samples": {}
        }
        
        total_pages = 0
        total_clicks = 0
        total_requests = 0
        total_marketing_tags = 0
        total_third_party = 0
        total_failed = 0
        vendors = {}
        analytics_vendors = {}
        media_vendors = {}
        pages_with_analytics = set()
        pages_with_media = set()
        all_pages = set()
        
        # Marketing tag patterns (real marketing technologies)
        marketing_patterns = {
            # Analytics
            "analytics": ["analytics", "omniture", "smetrics", "/va6/", "google-analytics", "ga.js", "gtag", "adobe", "collect?", "analytics.js"],
            # Media/Advertising
            "media": ["facebook.com", "fbcdn.net", "twitter.com", "linkedin.com", "snapchat.com", 
                     "tiktok.com", "pinterest.com", "doubleclick.net", "fls.doubleclick.net", 
                     "adsrvr.org", "bat.bing.com", "reddit.com", "taboola.com", "outbrain.com"],
            # Tag Management
            "tag_manager": ["tagmanager", "tealium", "ensighten", "signal"],
            # Survey/Feedback
            "survey": ["surveymonkey", "qualtrics", "medallia", "foresee"],
            # Session Recording
            "session": ["hotjar", "fullstory", "mouseflow", "clicktale", "sessioncam"]
        }
        
        # Non-marketing patterns (to exclude)
        non_marketing_patterns = [
            ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",  # Images
            ".woff", ".woff2", ".ttf", ".eot", ".otf",  # Fonts
            ".css", ".scss", ".less",  # Stylesheets (unless from CDN)
            ".mp4", ".webm", ".ogg", ".mp3",  # Media files
            "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com",  # CDN libraries
            "jquery", "bootstrap", "react", "vue", "angular",  # JS libraries (unless analytics)
        ]
        
        def is_marketing_tag(url, vendor=""):
            """Determine if a request is a real marketing tag"""
            url_lower = url.lower()
            vendor_lower = vendor.lower()
            
            # Exclude non-marketing patterns
            for pattern in non_marketing_patterns:
                if pattern in url_lower:
                    return False
            
            # Check for marketing patterns
            for category, patterns in marketing_patterns.items():
                for pattern in patterns:
                    if pattern in url_lower or pattern in vendor_lower:
                        return True
            
            return False
        
        for name, df in sheets.items():
            df = df.fillna("")
            lower = name.lower()
            
            # Sample data (first 5 rows for context)
            metrics["samples"][name] = df.head(5).to_dict(orient="records")
            
            # Track all unique pages
            if "page" in df.columns:
                all_pages.update(df["page"].unique())
            elif "Page" in df.columns:
                all_pages.update(df["Page"].unique())
            
            # Extract metrics
            if "page" in lower and "tag" not in lower:
                total_pages = max(total_pages, len(df))
            
            if "click" in lower:
                total_clicks = max(total_clicks, len(df))
            
            if "tag" in lower:
                total_requests += len(df)  # Count all requests
                
                # Vendor analysis
                vendor_col = None
                for col in df.columns:
                    if "vendor" in col.lower():
                        vendor_col = col
                        break
                
                tag_url_col = None
                for col in df.columns:
                    if "tag" in col.lower() and "url" in col.lower():
                        tag_url_col = col
                        break
                
                # Count only real marketing tags
                for idx, row in df.iterrows():
                    tag_url = str(row.get(tag_url_col, "")) if tag_url_col else ""
                    vendor = str(row.get(vendor_col, "")) if vendor_col else ""
                    
                    if is_marketing_tag(tag_url, vendor):
                        total_marketing_tags += 1
                        
                        if vendor and vendor.strip():
                            vendors[vendor] = vendors.get(vendor, 0) + 1
                            
                            # Classify analytics vs media tags
                            vendor_lower = vendor.lower()
                            tag_url_lower = tag_url.lower()
                            
                            # Check if analytics
                            if any(x in vendor_lower or x in tag_url_lower for x in marketing_patterns["analytics"]):
                                analytics_vendors[vendor] = analytics_vendors.get(vendor, 0) + 1
                            # Check if media
                            elif any(x in vendor_lower or x in tag_url_lower for x in marketing_patterns["media"]):
                                media_vendors[vendor] = media_vendors.get(vendor, 0) + 1
                
                # Track pages with analytics tags
                if "page" in df.columns or "Page" in df.columns:
                    page_col = "page" if "page" in df.columns else "Page"
                    
                    if tag_url_col:
                        for idx, row in df.iterrows():
                            tag_url = str(row.get(tag_url_col, "")).lower()
                            page = row.get(page_col, "")
                            vendor = str(row.get(vendor_col, "")) if vendor_col else ""
                            
                            # Check for analytics patterns
                            if any(x in tag_url for x in marketing_patterns["analytics"]):
                                pages_with_analytics.add(page)
                            
                            # Check for media patterns
                            if any(x in tag_url for x in marketing_patterns["media"]):
                                pages_with_media.add(page)
                
                # Failed requests
                status_col = None
                for col in df.columns:
                    if "status" in col.lower():
                        status_col = col
                        break
                
                if status_col:
                    total_failed += len(df[df[status_col] != "200"])
            
            if "3rd" in lower or "third" in lower:
                total_third_party = len(df)
        
        # Calculate analytics coverage
        total_pages = len(all_pages) if all_pages else total_pages
        pages_missing_analytics = all_pages - pages_with_analytics
        analytics_coverage = (len(pages_with_analytics) / total_pages * 100) if total_pages > 0 else 0
        
        # Calculate maturity scores
        tag_coverage_score = 5 if analytics_coverage >= 95 else (4 if analytics_coverage >= 85 else (3 if analytics_coverage >= 70 else 2))
        
        marketing_tags_per_page = total_marketing_tags / total_pages if total_pages > 0 else 0
        tag_governance_score = 5 if marketing_tags_per_page <= 20 else (4 if marketing_tags_per_page <= 30 else (3 if marketing_tags_per_page <= 40 else 2))
        
        vendor_visibility_score = 5 if len(vendors) <= 15 else (4 if len(vendors) <= 25 else (3 if len(vendors) <= 35 else 2))
        
        failure_rate = (total_failed / total_marketing_tags * 100) if total_marketing_tags > 0 else 0
        measurement_reliability_score = 5 if failure_rate < 1 else (4 if failure_rate < 3 else (3 if failure_rate < 5 else 2))
        
        privacy_score = 3  # Default - need actual privacy data
        
        overall_maturity = round((tag_coverage_score + tag_governance_score + vendor_visibility_score + measurement_reliability_score + privacy_score) / 5, 1)
        
        # Summary metrics
        metrics["summary"] = {
            "pages": total_pages,
            "clicks": total_clicks,
            "total_requests": total_requests,
            "marketing_tags": total_marketing_tags,
            "third_party_calls": total_third_party,
            "failed_requests": total_failed,
            "vendors": vendors
        }
        
        # Analytics insights
        metrics["analytics"] = {
            "pages_with_analytics": len(pages_with_analytics),
            "pages_missing_analytics": len(pages_missing_analytics),
            "missing_pages_list": list(pages_missing_analytics)[:10],
            "coverage_percent": round(analytics_coverage, 1),
            "analytics_vendors": analytics_vendors
        }
        
        # Media insights
        metrics["media"] = {
            "pages_with_media": len(pages_with_media),
            "media_coverage_percent": round((len(pages_with_media) / total_pages * 100), 1) if total_pages > 0 else 0,
            "media_vendors": media_vendors,
            "total_media_tags": sum(media_vendors.values())
        }
        
        # Governance insights
        metrics["governance"] = {
            "failed_requests": total_failed,
            "total_vendors": len(vendors),
            "unclassified_vendors": len([v for v in vendors.keys() if "other" in str(v).lower() or "unknown" in str(v).lower()])
        }
        
        # Maturity scores
        metrics["maturity"] = {
            "tag_coverage": tag_coverage_score,
            "tag_governance": tag_governance_score,
            "vendor_visibility": vendor_visibility_score,
            "measurement_reliability": measurement_reliability_score,
            "privacy_compliance": privacy_score,
            "overall": overall_maturity
        }
        
        # Derived KPIs
        pages = total_pages or 1
        clicks = total_clicks or 1
        marketing_tags = total_marketing_tags or 1
        third = total_third_party or 1
        
        metrics["derived"] = {
            "marketing_tags_per_page": round(marketing_tags / pages, 1),
            "total_requests_per_page": round(total_requests / pages, 1),
            "marketing_tags_per_click": round(marketing_tags / clicks, 2),
            "third_party_per_click": round(third / clicks, 2),
            "failure_rate_percent": round((total_failed / marketing_tags) * 100, 2) if marketing_tags > 0 else 0
        }
        
        # Clean up temp file
        if os.path.exists(local_path):
            os.remove(local_path)
        
        # Format response for executive summary
        result = f"""
📊 KORU Report Analysis: {report_name}

═══════════════════════════════════════════════════════════════

📈 MARKETING MEASUREMENT MATURITY SCORE: {overall_maturity}/5

┌─────────────────────────────────────────────────────────────┐
│ Dimension                    │ Score │ Assessment           │
├─────────────────────────────────────────────────────────────┤
│ Tag Coverage                 │ {tag_coverage_score}/5   │ {analytics_coverage:.1f}% pages tagged      │
│ Tag Governance               │ {tag_governance_score}/5   │ {marketing_tags_per_page:.1f} tags/page (target: <30) │
│ Vendor Visibility            │ {vendor_visibility_score}/5   │ {len(vendors)} vendors active       │
│ Measurement Reliability      │ {measurement_reliability_score}/5   │ {failure_rate:.1f}% failure rate        │
│ Privacy Compliance           │ {privacy_score}/5   │ Needs assessment        │
└─────────────────────────────────────────────────────────────┘

Overall Maturity: {"Excellent" if overall_maturity >= 4.5 else "Good" if overall_maturity >= 3.5 else "Needs Improvement"}

Top Priority: {"Maintain current standards" if overall_maturity >= 4.5 else f"Address {len(pages_missing_analytics)} pages missing analytics" if pages_missing_analytics else "Optimize tag governance"}

═══════════════════════════════════════════════════════════════

📊 AUDIT SCOPE:
• Pages Analyzed: {total_pages}
• Click Journeys: {total_clicks}
• Total Requests: {total_requests} (includes images, fonts, JS files)
• Marketing Tags: {total_marketing_tags} (real marketing technologies only)
• Third-Party Calls: {total_third_party}
• Failed Requests: {total_failed}

═══════════════════════════════════════════════════════════════

🎯 KEY METRICS:
• Marketing Tags per Page: {metrics['derived']['marketing_tags_per_page']} (Recommended: <30)
• Total Requests per Page: {metrics['derived']['total_requests_per_page']} (includes all assets)
• Marketing Tags per Click: {metrics['derived']['marketing_tags_per_click']}
• Third-Party per Click: {metrics['derived']['third_party_per_click']}
• Failure Rate: {metrics['derived']['failure_rate_percent']}%

═══════════════════════════════════════════════════════════════

1️⃣ ANALYTICS TAG COVERAGE:
• Pages with Analytics: {metrics['analytics']['pages_with_analytics']}/{total_pages} ({metrics['analytics']['coverage_percent']}%)
• Pages Missing Analytics: {metrics['analytics']['pages_missing_analytics']} ({round(100 - metrics['analytics']['coverage_percent'], 1)}%)
"""
        
        if metrics['analytics']['missing_pages_list']:
            result += f"• Missing on: {', '.join(metrics['analytics']['missing_pages_list'][:5])}"
            if len(metrics['analytics']['missing_pages_list']) > 5:
                result += f" ... and {len(metrics['analytics']['missing_pages_list']) - 5} more"
            result += "\n"
        
        if analytics_vendors:
            result += f"• Analytics Vendors: {', '.join(analytics_vendors.keys())}\n"
        
        result += f"""
Impact: {round(100 - metrics['analytics']['coverage_percent'], 1)}% of user sessions not tracked
Action: Tag the {metrics['analytics']['pages_missing_analytics']} missing pages immediately

💡 Type "analyze missing analytics" for detailed page-by-page breakdown

═══════════════════════════════════════════════════════════════

2️⃣ MEDIA TAG PERFORMANCE:
• Pages with Media Tags: {metrics['media']['pages_with_media']}/{total_pages} ({metrics['media']['media_coverage_percent']}%)
• Total Media Tag Fires: {metrics['media']['total_media_tags']}
"""
        
        if media_vendors:
            result += "• Media Vendors:\n"
            sorted_media = sorted(media_vendors.items(), key=lambda x: x[1], reverse=True)[:5]
            for vendor, count in sorted_media:
                result += f"  - {vendor}: {count} fires\n"
        
        result += f"""
Impact: {"Strong" if metrics['media']['media_coverage_percent'] >= 90 else "Partial"} media measurement coverage
Action: {"Maintain current coverage" if metrics['media']['media_coverage_percent'] >= 90 else "Review pages without media tags"}

💡 Type "analyze media tags" for complete media vendor analysis

═══════════════════════════════════════════════════════════════

3️⃣ TAG GOVERNANCE & RELIABILITY:
• Failed Tag Requests: {total_failed} ({metrics['derived']['failure_rate_percent']}% failure rate)
• Marketing Tags per Page: {metrics['derived']['marketing_tags_per_page']} (target: <30)
• Total Unique Vendors: {metrics['governance']['total_vendors']}
• Unclassified Vendors: {metrics['governance']['unclassified_vendors']}

Impact: {"Minimal" if failure_rate < 2 else "Moderate" if failure_rate < 5 else "Significant"} data quality issues
Action: {"Monitor for changes" if failure_rate < 2 else "Investigate failed tags"}

═══════════════════════════════════════════════════════════════

4️⃣ THIRD-PARTY VENDOR EXPOSURE:
• Total Third-Party Vendors: {metrics['governance']['total_vendors']}
• Third-Party Calls: {total_third_party}
• Vendor Categories: Analytics, Advertising, Tag Management

Impact: Privacy compliance review needed
Action: Conduct vendor audit and implement consent management

═══════════════════════════════════════════════════════════════

🏢 TOP VENDORS (Marketing Tags Only):
"""
        
        # Add top 10 vendors
        sorted_vendors = sorted(vendors.items(), key=lambda x: x[1], reverse=True)[:10]
        for vendor, count in sorted_vendors:
            result += f"• {vendor}: {count} fires\n"
        
        result += """
═══════════════════════════════════════════════════════════════

💡 Type "detailed analysis" for full 10-section audit report
"""
        
        return result
        
    except Exception as e:
        return f"Error analyzing report: {str(e)}"



@mcp.tool()
def analyze_missing_analytics_tags(report_name: str) -> str:
    """
    Deep dive analysis of pages missing analytics tags
    
    Args:
        report_name: Name of the report file (e.g., 'hyatt-koru-report.xlsx')
    """
    try:
        if not report_name.endswith(".xlsx"):
            report_name += "-koru-report.xlsx"
        
        local_path = f"temp_{report_name}"
        s3_service.download_file(report_name, local_path)
        
        sheets = pd.read_excel(local_path, sheet_name=None, engine="calamine", dtype=str)
        
        # Track pages and their analytics status
        all_pages = set()
        pages_with_analytics = {}  # page -> list of analytics tags
        page_tag_counts = {}  # page -> total tag count
        page_links = {}  # page -> link count
        
        for name, df in sheets.items():
            df = df.fillna("")
            lower = name.lower()
            
            # Get all unique pages
            page_col = None
            for col in df.columns:
                if col.lower() in ["page", "page url", "page_url"]:
                    page_col = col
                    break
            
            if page_col:
                all_pages.update(df[page_col].unique())
            
            # Analyze tags sheet
            if "tag" in lower:
                tag_url_col = None
                vendor_col = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if "tag" in col_lower and "url" in col_lower:
                        tag_url_col = col
                    if "vendor" in col_lower:
                        vendor_col = col
                
                if page_col and tag_url_col:
                    for idx, row in df.iterrows():
                        page = row.get(page_col, "")
                        tag_url = str(row.get(tag_url_col, "")).lower()
                        vendor = row.get(vendor_col, "") if vendor_col else ""
                        
                        if not page:
                            continue
                        
                        # Count total tags per page
                        page_tag_counts[page] = page_tag_counts.get(page, 0) + 1
                        
                        # Check for analytics patterns
                        analytics_patterns = [
                            "analytics", "omniture", "smetrics", "/va6/", 
                            "google-analytics", "ga.js", "gtag", "adobe",
                            "collect?", "analytics.js"
                        ]
                        
                        if any(pattern in tag_url for pattern in analytics_patterns):
                            if page not in pages_with_analytics:
                                pages_with_analytics[page] = []
                            pages_with_analytics[page].append({
                                "vendor": vendor,
                                "tag_url": row.get(tag_url_col, "")[:100]  # Truncate long URLs
                            })
            
            # Count links per page
            if "click" in lower or "link" in lower:
                if page_col:
                    link_counts = df[page_col].value_counts().to_dict()
                    for page, count in link_counts.items():
                        page_links[page] = page_links.get(page, 0) + count
        
        # Identify missing pages
        pages_missing_analytics = all_pages - set(pages_with_analytics.keys())
        
        # Clean up
        if os.path.exists(local_path):
            os.remove(local_path)
        
        # Format detailed response
        result = f"""
🔍 DEEP DIVE: Missing Analytics Tags Analysis
Report: {report_name}

═══════════════════════════════════════════════════════════════

📊 OVERVIEW:
• Total Pages Scanned: {len(all_pages)}
• Pages WITH Analytics: {len(pages_with_analytics)} ({round(len(pages_with_analytics)/len(all_pages)*100, 1)}%)
• Pages MISSING Analytics: {len(pages_missing_analytics)} ({round(len(pages_missing_analytics)/len(all_pages)*100, 1)}%)

═══════════════════════════════════════════════════════════════

❌ PAGES MISSING ANALYTICS TAGS:

"""
        
        if pages_missing_analytics:
            for i, page in enumerate(sorted(pages_missing_analytics), 1):
                total_tags = page_tag_counts.get(page, 0)
                links = page_links.get(page, 0)
                
                result += f"{i}. {page}\n"
                result += f"   • Total Tags on Page: {total_tags}\n"
                result += f"   • Links on Page: {links}\n"
                result += f"   • Issue: Analytics tag not firing on page load\n"
                result += f"   • Impact: User sessions on this page are not tracked\n\n"
        else:
            result += "✅ All pages have analytics tags!\n\n"
        
        result += f"""
═══════════════════════════════════════════════════════════════

✅ PAGES WITH ANALYTICS (Sample):

"""
        
        # Show first 5 pages with analytics
        sample_pages = list(pages_with_analytics.items())[:5]
        for page, tags in sample_pages:
            result += f"• {page}\n"
            result += f"  Analytics Tags: {len(tags)}\n"
            for tag in tags[:2]:  # Show first 2 tags
                result += f"    - {tag['vendor']}: {tag['tag_url'][:80]}...\n"
            result += "\n"
        
        if len(pages_with_analytics) > 5:
            result += f"... and {len(pages_with_analytics) - 5} more pages with analytics\n\n"
        
        result += f"""
═══════════════════════════════════════════════════════════════

📈 ANALYTICS TAG DISTRIBUTION:

"""
        
        # Count analytics tags by vendor
        vendor_counts = {}
        for page, tags in pages_with_analytics.items():
            for tag in tags:
                vendor = tag['vendor'] or 'Unknown'
                vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
        
        sorted_vendors = sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)
        for vendor, count in sorted_vendors:
            result += f"• {vendor}: {count} page loads\n"
        
        result += f"""

═══════════════════════════════════════════════════════════════

💡 RECOMMENDATIONS:

"""
        
        if pages_missing_analytics:
            result += f"""
1. IMMEDIATE ACTION: Tag {len(pages_missing_analytics)} missing pages
   - Priority: High-traffic pages (checkout, product, landing pages)
   - Implementation: Add analytics tag to page template or tag manager
   
2. VALIDATION: Test analytics firing on all pages
   - Use browser dev tools to verify tag execution
   - Check for JavaScript errors blocking tag execution
   
3. MONITORING: Set up alerts for missing analytics
   - Monitor tag coverage weekly
   - Alert when new pages are added without analytics

4. BUSINESS IMPACT:
   - {round(len(pages_missing_analytics)/len(all_pages)*100, 1)}% of pages have no visibility
   - Conversion funnels may be incomplete
   - Attribution models will be inaccurate
"""
        else:
            result += """
✅ Analytics coverage is complete!

NEXT STEPS:
1. Verify analytics data quality (correct values, no duplicates)
2. Check for consistent implementation across all pages
3. Monitor for new pages added without analytics
"""
        
        return result
        
    except Exception as e:
        return f"Error analyzing missing analytics tags: {str(e)}"


@mcp.tool()
def analyze_media_tags(report_name: str) -> str:
    """
    Deep dive analysis of media tag performance and coverage
    
    Args:
        report_name: Name of the report file (e.g., 'hyatt-koru-report.xlsx')
    """
    try:
        if not report_name.endswith(".xlsx"):
            report_name += "-koru-report.xlsx"
        
        local_path = f"temp_{report_name}"
        s3_service.download_file(report_name, local_path)
        
        sheets = pd.read_excel(local_path, sheet_name=None, engine="calamine", dtype=str)
        
        # Track media tags
        media_vendors = {}  # vendor -> {pages: set, links: set, total_fires: int}
        pages_with_media = set()
        links_with_media = set()
        all_pages = set()
        all_links = set()
        media_tag_details = []  # List of all media tag fires
        
        # Media patterns
        media_patterns = {
            "Facebook": ["facebook.com", "fbcdn.net", "fb.com", "facebook pixel"],
            "Google Ads": ["googleadservices.com", "google.com/ads", "doubleclick.net/pagead"],
            "LinkedIn": ["linkedin.com", "licdn.com", "linkedin insight"],
            "Twitter": ["twitter.com", "t.co", "twimg.com", "twitter pixel"],
            "Snapchat": ["snapchat.com", "sc-static.net"],
            "TikTok": ["tiktok.com", "ttwstatic.com"],
            "Pinterest": ["pinterest.com", "pinimg.com"],
            "Floodlight": ["fls.doubleclick.net", "floodlight"],
            "Trade Desk": ["adsrvr.org", "tradedesk"],
            "Bing Ads": ["bat.bing.com", "bing.com/ads"],
            "Reddit": ["reddit.com", "redditmedia.com"],
            "Taboola": ["taboola.com", "trc.taboola.com"],
            "Outbrain": ["outbrain.com", "amplify.outbrain.com"]
        }
        
        for name, df in sheets.items():
            df = df.fillna("")
            lower = name.lower()
            
            # Find relevant columns
            page_col = None
            tag_url_col = None
            vendor_col = None
            link_col = None
            event_type_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ["page", "page url", "page_url"]:
                    page_col = col
                if "tag" in col_lower and "url" in col_lower:
                    tag_url_col = col
                if "vendor" in col_lower:
                    vendor_col = col
                if "link" in col_lower and "text" in col_lower:
                    link_col = col
                if "event" in col_lower and "type" in col_lower:
                    event_type_col = col
            
            # Track all pages
            if page_col:
                all_pages.update(df[page_col].unique())
            
            # Analyze tags
            if "tag" in lower and tag_url_col:
                for idx, row in df.iterrows():
                    page = row.get(page_col, "") if page_col else ""
                    tag_url = str(row.get(tag_url_col, "")).lower()
                    vendor = row.get(vendor_col, "") if vendor_col else ""
                    link_text = row.get(link_col, "") if link_col else ""
                    event_type = row.get(event_type_col, "") if event_type_col else ""
                    
                    # Check if it's a media tag
                    matched_vendor = None
                    for media_vendor, patterns in media_patterns.items():
                        if any(pattern in tag_url for pattern in patterns):
                            matched_vendor = media_vendor
                            break
                    
                    if matched_vendor:
                        if matched_vendor not in media_vendors:
                            media_vendors[matched_vendor] = {
                                "pages": set(),
                                "links": set(),
                                "total_fires": 0,
                                "page_load": 0,
                                "click": 0
                            }
                        
                        media_vendors[matched_vendor]["total_fires"] += 1
                        
                        if page:
                            media_vendors[matched_vendor]["pages"].add(page)
                            pages_with_media.add(page)
                        
                        if link_text:
                            media_vendors[matched_vendor]["links"].add(link_text)
                            links_with_media.add(link_text)
                            all_links.add(link_text)
                        
                        # Track event type
                        event_lower = event_type.lower()
                        if "page" in event_lower or "load" in event_lower:
                            media_vendors[matched_vendor]["page_load"] += 1
                        elif "click" in event_lower:
                            media_vendors[matched_vendor]["click"] += 1
                        
                        media_tag_details.append({
                            "vendor": matched_vendor,
                            "page": page,
                            "link": link_text,
                            "event_type": event_type,
                            "tag_url": tag_url[:100]
                        })
            
            # Track all links
            if "click" in lower and link_col:
                all_links.update(df[link_col].unique())
        
        # Clean up
        if os.path.exists(local_path):
            os.remove(local_path)
        
        # Format response
        result = f"""
📢 DEEP DIVE: Media Tag Analysis
Report: {report_name}

═══════════════════════════════════════════════════════════════

📊 OVERVIEW:
• Total Pages: {len(all_pages)}
• Pages with Media Tags: {len(pages_with_media)} ({round(len(pages_with_media)/len(all_pages)*100, 1) if all_pages else 0}%)
• Total Links: {len(all_links)}
• Links with Media Tags: {len(links_with_media)} ({round(len(links_with_media)/len(all_links)*100, 1) if all_links else 0}%)
• Total Media Tag Fires: {len(media_tag_details)}
• Active Media Vendors: {len(media_vendors)}

═══════════════════════════════════════════════════════════════

🏢 MEDIA VENDOR BREAKDOWN:

"""
        
        # Sort vendors by total fires
        sorted_vendors = sorted(media_vendors.items(), key=lambda x: x[1]["total_fires"], reverse=True)
        
        for vendor, data in sorted_vendors:
            page_coverage = round(len(data["pages"]) / len(all_pages) * 100, 1) if all_pages else 0
            
            result += f"""
{vendor}
├─ Total Fires: {data["total_fires"]}
├─ Page Coverage: {len(data["pages"])}/{len(all_pages)} pages ({page_coverage}%)
├─ Link Coverage: {len(data["links"])} unique links
├─ Page Load Events: {data["page_load"]}
└─ Click Events: {data["click"]}

"""
        
        result += f"""
═══════════════════════════════════════════════════════════════

📈 MEDIA TAG PERFORMANCE:

"""
        
        # Calculate metrics
        total_fires = sum(v["total_fires"] for v in media_vendors.values())
        total_page_loads = sum(v["page_load"] for v in media_vendors.values())
        total_clicks = sum(v["click"] for v in media_vendors.values())
        
        result += f"""
• Total Media Tag Fires: {total_fires}
• Page Load Tags: {total_page_loads} ({round(total_page_loads/total_fires*100, 1) if total_fires else 0}%)
• Click Tags: {total_clicks} ({round(total_clicks/total_fires*100, 1) if total_fires else 0}%)
• Average Tags per Page: {round(total_fires/len(all_pages), 1) if all_pages else 0}
• Average Tags per Link: {round(total_clicks/len(all_links), 1) if all_links else 0}

═══════════════════════════════════════════════════════════════

🎯 COVERAGE ANALYSIS:

"""
        
        pages_missing_media = all_pages - pages_with_media
        
        if pages_missing_media:
            result += f"""
⚠️ Pages WITHOUT Media Tags: {len(pages_missing_media)}

"""
            for i, page in enumerate(sorted(pages_missing_media)[:10], 1):
                result += f"{i}. {page}\n"
            
            if len(pages_missing_media) > 10:
                result += f"... and {len(pages_missing_media) - 10} more\n"
        else:
            result += "✅ All pages have media tag coverage!\n"
        
        result += f"""

═══════════════════════════════════════════════════════════════

💰 MEDIA SPEND IMPLICATIONS:

"""
        
        # Vendor concentration
        if sorted_vendors:
            top_vendor = sorted_vendors[0]
            top_vendor_share = round(top_vendor[1]["total_fires"] / total_fires * 100, 1) if total_fires else 0
            
            result += f"""
• Vendor Concentration: {top_vendor[0]} dominates with {top_vendor_share}% of media tags
• Diversification: {len(media_vendors)} active media platforms
• Page-Level Tracking: {round(len(pages_with_media)/len(all_pages)*100, 1) if all_pages else 0}% coverage
• Link-Level Tracking: {round(len(links_with_media)/len(all_links)*100, 1) if all_links else 0}% coverage

SPEND EFFICIENCY:
"""
            
            if page_coverage >= 90:
                result += "✅ Strong page-level coverage ensures broad reach measurement\n"
            else:
                result += f"⚠️ Only {page_coverage}% page coverage - potential measurement gaps\n"
            
            if len(links_with_media) / len(all_links) < 0.1 if all_links else False:
                result += "✅ Selective link tracking - cost-efficient approach\n"
            else:
                result += "⚠️ High link-level tracking - review if all conversions need tracking\n"
        
        result += f"""

═══════════════════════════════════════════════════════════════

💡 RECOMMENDATIONS:

"""
        
        recommendations = []
        
        # Check for missing vendors
        if len(media_vendors) < 3:
            recommendations.append("Consider diversifying media vendors for better attribution")
        
        # Check page coverage
        if len(pages_with_media) / len(all_pages) < 0.9 if all_pages else False:
            recommendations.append(f"Improve page coverage - {len(pages_missing_media)} pages lack media tags")
        
        # Check vendor balance
        if sorted_vendors and sorted_vendors[0][1]["total_fires"] / total_fires > 0.7 if total_fires else False:
            recommendations.append(f"High concentration in {sorted_vendors[0][0]} - review attribution model")
        
        # Check for click tracking
        if total_clicks == 0:
            recommendations.append("No click-level media tracking detected - consider adding conversion tracking")
        
        if not recommendations:
            recommendations.append("✅ Media tag implementation looks solid!")
            recommendations.append("Continue monitoring for new pages and campaigns")
        
        for i, rec in enumerate(recommendations, 1):
            result += f"{i}. {rec}\n"
        
        return result
        
    except Exception as e:
        return f"Error analyzing media tags: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001)
