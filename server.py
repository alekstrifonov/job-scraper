import socket
import threading
import requests
from bs4 import BeautifulSoup
import bs4
import csv
import os
import json
from datetime import datetime
import re

# Define the server's host and port
HOST = '127.0.0.1'
PORT = 65432

def scrape_jobs(url):
    '''Function to scrape pages and fetch job listings'''
    page = requests.get(url).text
    soup = BeautifulSoup(page, 'html.parser')
    
    jobs_container = soup.find_all('div', class_='job-listing-container')  # Adjust this selector as necessary
    return jobs_container

def get_jobs_info(jobs_container, client_tech_stack):
    '''Returns all the jobs that match the client's tech stack'''
    matching_jobs = []
    client_tech_stack = [x.lower() for x in client_tech_stack]
    
    for job in jobs_container:
        if isinstance(job, bs4.element.Tag):
            job_title_tag = job.find('h6', class_='job-title')
            job_title = job_title_tag.get_text(strip=True) if job_title_tag else 'N/A'
            
            # Extract the salary information
            salary_tag = job.find('span', class_='badge blue has-hidden-text has-tooltip')
            if salary_tag:
                salary = salary_tag.get_text(strip=True)
                salary = salary.split('лв.')[0].strip()
                salary += 'лв.'
            else:
                salary = 'N/A'
                
            job_link_tag = job.find('a', class_='overlay-link ab-trigger')
            job_link = job_link_tag.get('href') if job_link_tag else 'N/A'
            
            
            # Extract tech stack image titles
            tech_stack_images = job.find_all('img', class_='attachment-medium')
            tech_stack_titles = list({img.get('title') for img in tech_stack_images if img.get('title')})
            tech_stack_titles = [x.lower() for x in tech_stack_titles]

            # Filter based on tech stack matching
            if set(tech_stack_titles).issubset(set(client_tech_stack)):
                # print(''.join(tech_stack_titles))
                matching_jobs.append({
                    'Job Title': job_title,
                    'Salary': salary,
                    'Tech Stack Titles': ','.join(tech_stack_titles),  # Join tech stack titles into a single string
                    'Job Link': job_link
                })
                

    return matching_jobs

def get_pages(soup):
    '''Finds the number of pages in the given job category'''
    script_tag = soup.find('script', string=lambda s: s and 'window.FWP_JSON' in s)

    if script_tag:
        script_content = script_tag.string.strip()
        
        pattern = r'class=\\"facetwp-page last\\" data-page=\\"(\d+)\\"'
        
        match = re.search(pattern, script_content)
        
        last_page_number = match.group(1)
    
    return int(last_page_number)


def send_csv_response(client_socket, job_listings, client_address):
    '''Function to send a CSV response to the client'''
    
    # Create a unique filename using the client address and timestamp - uniqeness is needed for multithreading
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    client_identifier = f'{client_address[0]}_{client_address[1]}'  
    filename = f'job_listings_{client_identifier}_{timestamp}.csv'
    
    # Save the CSV content to a file
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['Job Title', 'Salary', 'Tech Stack Titles', 'Job Link'])
        writer.writeheader()
        writer.writerows(job_listings)
    
    # Notify the client of the file transfer initiation
    response_message = f'Preparing to send file: {filename}\n'
    client_socket.sendall(response_message.encode('utf-8'))
    
    # Send the CSV file content to the client
    with open(filename, 'rb') as file:
        client_socket.sendfile(file)
    
    # Notify the client of completion
    client_socket.sendall(b'\nFile transfer complete.\n')
    client_socket.close()

    # Optionally, delete the file after sending
    os.remove(filename)

def handle_client(client_socket, address):
    '''Handling each client connection'''
    print(f'Connection from {address} has been established!')
    
    # Receive the client's tech stack (JSON format)
    request = client_socket.recv(1024).decode('utf-8')
    
    data = json.loads(request)
    client_tech_stack = data['tech_stack']
    selected_category = data['category']

    
    # Scrape job listings (use a URL for the job listings page)
    URL = 'https://dev.bg/company/jobs/' + selected_category + '/'  
    page = requests.get(URL).text
    
    URL += '?_paged='
    
    doc = BeautifulSoup(page, 'html.parser')
    num_pages = get_pages(doc)
    client_socket.sendall('Parsing started...'.encode('utf-8'))
    
    matching_jobs = []
    progress = 0

    for num in range(1, num_pages + 1):

        PAGE_URL = URL + f'{num}'
        
        page = requests.get(PAGE_URL).text
        doc = BeautifulSoup(page, 'html.parser')

        jobs_container = doc.find(class_='jobs-loop facetwp-template')

        matching_jobs_this_page = get_jobs_info(jobs_container, client_tech_stack)
        # print(matching_jobs_this_page)
        matching_jobs.extend(matching_jobs_this_page)
        
        progress = int((num*100)/num_pages)
        client_socket.sendall(f'{progress}'.encode('utf-8')) 
        
    client_socket.sendall('File is ready for download.'.encode('utf-8'))
    
    # Send the matching jobs as a CSV response
    if matching_jobs:
        send_csv_response(client_socket, matching_jobs, address)
    else:
        client_socket.sendall('No matching jobs found.'.encode('utf-8'))
        client_socket.close()
        
def start_server():
    '''Function to start the server'''
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen(5) 
    
    print(f'Server is running on {HOST}:{PORT}...')
    
    while True:
        try:
            client_socket, address = server_socket.accept()
            
            # Create a new thread for each client connection
            client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
            client_thread.start()
        except KeyboardInterrupt:
            print('\nServer shutting down...')
            break
    server_socket.close()

if __name__ == '__main__':
    start_server()
