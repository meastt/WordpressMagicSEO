"""
report_generator.py
==================
Generate reports from technical SEO audit results in various formats.
"""

import json
import csv
from typing import Dict, List
from datetime import datetime
from io import StringIO


class SEOReportGenerator:
    """Generate SEO audit reports in multiple formats."""
    
    def __init__(self, audit_results: Dict):
        """
        Initialize report generator.
        
        Args:
            audit_results: Complete audit results dictionary from TechnicalSEOAuditor
        """
        self.audit_results = audit_results
    
    def generate_json(self) -> str:
        """Generate JSON report."""
        return json.dumps(self.audit_results, indent=2)
    
    def generate_csv(self) -> str:
        """Generate CSV report with one row per issue."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow([
            'URL',
            'Status Code',
            'Category',
            'Check Name',
            'Status',
            'Severity',
            'Confidence',
            'Message',
            'Value',
            'Edge Case'
        ])
        
        # Data rows
        for url_data in self.audit_results.get('urls', []):
            url = url_data.get('url', '')
            status_code = url_data.get('status_code', 0)
            
            for category, issues in url_data.get('issues', {}).items():
                for issue in issues:
                    writer.writerow([
                        url,
                        status_code,
                        category,
                        issue.get('check_name', ''),
                        issue.get('status', ''),
                        issue.get('severity', ''),
                        issue.get('confidence', ''),
                        issue.get('message', ''),
                        issue.get('value', ''),
                        issue.get('edge_case_detected', False)
                    ])
        
        return output.getvalue()
    
    def generate_html(self) -> str:
        """Generate HTML report with color-coded issues."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Technical SEO Audit Report - {self.audit_results.get('site_url', 'Unknown')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        
        .meta {{
            color: #7f8c8d;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #ecf0f1;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .summary-card.critical {{
            background: #fee;
            border: 2px solid #e74c3c;
        }}
        
        .summary-card.warning {{
            background: #fff8e1;
            border: 2px solid #f39c12;
        }}
        
        .summary-card.passed {{
            background: #e8f5e9;
            border: 2px solid #27ae60;
        }}
        
        .summary-card h3 {{
            font-size: 36px;
            margin-bottom: 5px;
        }}
        
        .summary-card p {{
            color: #555;
            font-weight: 500;
        }}
        
        .url-section {{
            margin-bottom: 40px;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }}
        
        .url-header {{
            margin-bottom: 15px;
        }}
        
        .url-header h2 {{
            color: #2c3e50;
            font-size: 20px;
            margin-bottom: 5px;
        }}
        
        .url-meta {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        
        .category {{
            margin-bottom: 20px;
        }}
        
        .category h3 {{
            color: #34495e;
            font-size: 16px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .issue {{
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 4px;
            border-left: 4px solid;
        }}
        
        .issue.critical {{
            background: #fee;
            border-color: #e74c3c;
        }}
        
        .issue.warning {{
            background: #fff8e1;
            border-color: #f39c12;
        }}
        
        .issue.optimal {{
            background: #e8f5e9;
            border-color: #27ae60;
        }}
        
        .issue.info {{
            background: #e3f2fd;
            border-color: #2196f3;
        }}
        
        .issue-name {{
            font-weight: 600;
            margin-bottom: 4px;
        }}
        
        .issue-message {{
            color: #555;
            font-size: 14px;
        }}
        
        .issue-meta {{
            margin-top: 6px;
            font-size: 12px;
            color: #7f8c8d;
        }}
        
        .edge-case {{
            display: inline-block;
            background: #fff3cd;
            color: #856404;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            margin-left: 8px;
        }}
        
        .no-issues {{
            color: #7f8c8d;
            font-style: italic;
            padding: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Technical SEO Audit Report</h1>
        <div class="meta">
            <p><strong>Site:</strong> {self.audit_results.get('site_url', 'Unknown')}</p>
            <p><strong>Date:</strong> {self.audit_results.get('audit_date', 'Unknown')}</p>
            <p><strong>URLs Checked:</strong> {self.audit_results.get('total_urls_checked', 0)}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card critical">
                <h3>{self.audit_results.get('summary', {}).get('critical_issues', 0)}</h3>
                <p>Critical Issues</p>
            </div>
            <div class="summary-card warning">
                <h3>{self.audit_results.get('summary', {}).get('warnings', 0)}</h3>
                <p>Warnings</p>
            </div>
            <div class="summary-card passed">
                <h3>{self.audit_results.get('summary', {}).get('passed', 0)}</h3>
                <p>Passed Checks</p>
            </div>
        </div>
"""
        
        # Add URL sections
        for url_data in self.audit_results.get('urls', []):
            url = url_data.get('url', '')
            status_code = url_data.get('status_code', 0)
            fetch_time = url_data.get('fetch_time', 0)
            
            html += f"""
        <div class="url-section">
            <div class="url-header">
                <h2>{url}</h2>
                <div class="url-meta">
                    Status: {status_code} | Fetch Time: {fetch_time:.3f}s
                </div>
            </div>
"""
            
            if url_data.get('error'):
                html += f'<p style="color: #e74c3c;">Error: {url_data.get("error")}</p>'
            else:
                # Add issues by category
                for category, issues in url_data.get('issues', {}).items():
                    if not issues:
                        continue
                    
                    html += f'<div class="category"><h3>{category.replace("_", " ").title()}</h3>'
                    
                    for issue in issues:
                        status = issue.get('status', '')
                        edge_case = issue.get('edge_case_detected', False)
                        edge_case_badge = '<span class="edge-case">Edge Case</span>' if edge_case else ''
                        
                        html += f"""
            <div class="issue {status}">
                <div class="issue-name">
                    {issue.get('check_name', 'Unknown').replace('_', ' ').title()} {edge_case_badge}
                </div>
                <div class="issue-message">{issue.get('message', '')}</div>
                <div class="issue-meta">
                    Severity: {issue.get('severity', 'unknown')} | 
                    Confidence: {issue.get('confidence', 'unknown')}
                    {f' | Value: {issue.get("value")}' if issue.get('value') else ''}
                </div>
            </div>
"""
                    
                    html += '</div>'
            
            html += '</div>'
        
        html += """
    </div>
</body>
</html>
"""
        
        return html

