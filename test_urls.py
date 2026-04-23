"""
Quick URL validator for JobSpy scrapers.
Run this to check for common URL issues in scraped jobs.
"""

import re
from urllib.parse import urlparse

def validate_job_urls(jobs_df):
    """
    Validates job URLs for common issues.
    Returns a report of problematic URLs.
    """
    issues = {
        "double_slash": [],
        "relative_urls": [],
        "empty_urls": [],
        "malformed": [],
        "tracking_redirects": [],
    }
    
    url_patterns = {
        "double_slash": re.compile(r'https?://[^/]+//'),
        "tracking": re.compile(r'/(track|redirect|outbound|click).*\?.*url='),
    }
    
    for idx, row in jobs_df.iterrows():
        job_url = row.get('job_url', '')
        job_url_direct = row.get('job_url_direct', '')
        title = row.get('title', 'Unknown')
        site = row.get('site', 'Unknown')
        
        for url_type, url in [('job_url', job_url), ('job_url_direct', job_url_direct)]:
            if not url or pd.isna(url):
                if url_type == 'job_url':  # Only report empty main URLs
                    issues["empty_urls"].append({
                        'idx': idx, 'site': site, 'title': title[:50]
                    })
                continue
            
            # Check for double slash (except after protocol)
            if '//' in url[8:]:  # Skip https://
                issues["double_slash"].append({
                    'idx': idx, 'site': site, 'title': title[:50], 
                    'url': url[:100], 'type': url_type
                })
            
            # Check for relative URLs
            if not url.startswith('http'):
                issues["relative_urls"].append({
                    'idx': idx, 'site': site, 'title': title[:50], 
                    'url': url[:100], 'type': url_type
                })
            
            # Check for tracking redirects
            if url_patterns["tracking"].search(url):
                issues["tracking_redirects"].append({
                    'idx': idx, 'site': site, 'title': title[:50], 
                    'url': url[:100], 'type': url_type
                })
            
            # Try to parse URL
            try:
                parsed = urlparse(url)
                if not parsed.netloc or not parsed.scheme:
                    issues["malformed"].append({
                        'idx': idx, 'site': site, 'title': title[:50], 
                        'url': url[:100], 'type': url_type
                    })
            except Exception as e:
                issues["malformed"].append({
                    'idx': idx, 'site': site, 'title': title[:50], 
                    'url': url[:100], 'type': url_type, 'error': str(e)
                })
    
    return issues


def print_report(issues, total_jobs):
    """Print validation report"""
    print("\n" + "="*60)
    print(f"URL VALIDATION REPORT ({total_jobs} jobs checked)")
    print("="*60)
    
    total_issues = sum(len(v) for v in issues.values())
    if total_issues == 0:
        print("✓ All URLs look good!")
        return
    
    for issue_type, items in issues.items():
        if items:
            print(f"\n⚠ {issue_type.upper().replace('_', ' ')} ({len(items)} found)")
            for item in items[:5]:  # Show first 5
                print(f"  [{item.get('site', '?')}] {item.get('title', '?')[:40]}...")
                print(f"    URL: {item.get('url', 'N/A')[:80]}...")
            if len(items) > 5:
                print(f"  ... and {len(items) - 5} more")
    
    print(f"\nTotal issues: {total_issues}")


if __name__ == "__main__":
    import sys
    import pandas as pd
    
    # Try to load from command line or default files
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "all_jobs.csv"
    
    try:
        df = pd.read_csv(csv_file)
        issues = validate_job_urls(df)
        print_report(issues, len(df))
    except FileNotFoundError:
        print(f"File not found: {csv_file}")
        print("Run a scrape first or provide a CSV file path")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
