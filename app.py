import os
import csv
import pandas as pd
from io import StringIO
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, Response
from werkzeug.utils import secure_filename
from config import Config
from classifier import classify_emails
from mailer import send_campaign
import re

app = Flask(__name__)
app.config.from_object(Config)

# Simple regex for email validation
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))
        
    if file and file.filename.endswith('.csv'):
        # Read CSV using pandas
        try:
            df = pd.read_csv(file)
            # Find an email column (case insensitive)
            email_col = next((col for col in df.columns if 'email' in col.lower()), None)
            
            if not email_col:
                flash('Could not find an "email" column in the CSV file.', 'error')
                return redirect(url_for('index'))
                
            raw_emails = df[email_col].dropna().astype(str).tolist()
            valid_emails = [e.strip() for e in raw_emails if EMAIL_REGEX.match(e.strip())]
            
            if not valid_emails:
                flash('No valid emails found in the CSV file.', 'error')
                return redirect(url_for('index'))
                
            # Classify emails
            classified = classify_emails(valid_emails)
            
            # Store in session
            session['classified_emails'] = classified
            flash(f'Successfully processed {len(valid_emails)} emails.', 'success')
            return redirect(url_for('classify'))
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a CSV.', 'error')
        return redirect(url_for('index'))

@app.route('/classify')
def classify():
    classified = session.get('classified_emails', {})
    if not classified:
        flash('No classified emails found. Please upload a list first.', 'error')
        return redirect(url_for('index'))
        
    return render_template('classify.html', classified=classified)

@app.route('/send', methods=['GET', 'POST'])
def send():
    classified = session.get('classified_emails', {})
    if not classified:
        flash('No recipients available. Please upload a list first.', 'error')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        audience = request.form.get('audience')
        subject = request.form.get('subject')
        body = request.form.get('body')
        
        # Build recipient list
        recipients = []
        if audience == 'Business':
            recipients = classified.get('Business', [])
        elif audience == 'Individual':
            recipients = classified.get('Individual', [])
        else: # All
            recipients = classified.get('Business', []) + classified.get('Individual', [])
            
        if not recipients:
            flash('Selected audience has no recipients.', 'error')
            return redirect(url_for('send'))
            
        # Handle attachment
        attachment = request.files.get('attachment')
        attachment_path = None
        if attachment and attachment.filename:
            filename = secure_filename(attachment.filename)
            attachment_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            attachment.save(attachment_path)
            
        # Send Campaign
        results = send_campaign(recipients, subject, body, attachment_path)
        
        # Cleanup attachment
        if attachment_path and os.path.exists(attachment_path):
            os.remove(attachment_path)
            
        # Calculate metrics
        total = len(results)
        delivered = sum(1 for r in results if r['status'] == 'Delivered')
        failed = total - delivered
        success_rate = round((delivered / total) * 100, 1) if total > 0 else 0
        
        metrics = {
            'total': total,
            'delivered': delivered,
            'failed': failed,
            'success_rate': success_rate
        }
        
        session['campaign_results'] = results
        session['campaign_metrics'] = metrics
        
        return redirect(url_for('report'))
        
    return render_template('send.html', 
                          business_count=len(classified.get('Business', [])),
                          individual_count=len(classified.get('Individual', [])))

@app.route('/report')
def report():
    results = session.get('campaign_results', [])
    metrics = session.get('campaign_metrics', {})
    
    if not results:
        flash('No campaign results available.', 'error')
        return redirect(url_for('index'))
        
    return render_template('report.html', results=results, metrics=metrics)

@app.route('/download-report')
def download_report():
    results = session.get('campaign_results', [])
    if not results:
        return redirect(url_for('index'))
        
    def generate():
        data = StringIO()
        writer = csv.writer(data)
        writer.writerow(('Email', 'Status', 'Timestamp'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        
        for r in results:
            writer.writerow((r['email'], r['status'], r['timestamp']))
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
            
    headers = {
        "Content-Disposition": "attachment; filename=campaign_report.csv",
        "Content-Type": "text/csv"
    }
    
    return Response(generate(), headers=headers)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
