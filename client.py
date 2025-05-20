import socket
import json
import tqdm

categories = {
    1: 'junior-intern',
    2: 'it-management',
    3: 'technical-support',
    4: 'hardware-and-engineering',
    5: 'customer-support',
    6: 'ui-ux-and-arts',
    7: 'erp-crm-development',
    8: 'data-science',
    9: 'mobile-development',
    10: 'operations',
    11: 'quality-assurance',
    12: 'pm-ba-and-more',
    13: 'full-stack-development',
    14: 'front-end-development',
    15: 'back-end-development'
}

def receive_file_from_server(client_socket):
    '''Function to receive the file from the server'''
    filename = 'received_job_listings.csv'
    with open(filename, 'wb') as file:
        print(f'Receiving file from server...')
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            file.write(data)
    print(f'File received and saved as {filename}')

def handle_server_updates(client_socket):
    '''Function to handle real-time updates from the server'''
    progress_bar = None  # None for printing reasons
    
    while True:
        response = client_socket.recv(1024).decode('utf-8')
        
        if response.isdigit():
            progress = int(response)
            
            if progress_bar is None:
                progress_bar = tqdm.tqdm(total=100, desc='Parsing Progress', unit='%')
            
            progress_bar.n = progress
            progress_bar.refresh()
            
        elif 'File is ready for download.' in response:
            if progress_bar:
                progress_bar.close()
            print(response)
            return  # Exit loop to proceed with file download
        else:
            print(f'Server: {response}')
            
def main():
    HOST = '127.0.0.1'
    PORT = 65432
    
    #getting the job category
    print('Available categories:')
    for idx, category in categories.items():
        print(f'{idx}. {category}')
        
    print('\nEnter the number corresponding to your job category:')
    category_index = input('> ').strip()
    
    try:
        category_index = int(category_index)
        selected_category = categories[category_index]
    except (ValueError, KeyError):
        print('Invalid category selection. Exiting.')
        exit()
        
        
    #getting the tech stack
    client_tech_stack = input('Enter your tech stack (comma-separated): ').split(',')
    client_tech_stack = [tech.strip().lower() for tech in client_tech_stack]
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))
        
        data = {'tech_stack': client_tech_stack, 'category': selected_category}
        client_socket.sendall(json.dumps(data).encode('utf-8'))
        
        handle_server_updates(client_socket)
        receive_file_from_server(client_socket) 
        
            
if __name__ == '__main__':
    main()


