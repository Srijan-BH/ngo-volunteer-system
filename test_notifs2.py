import requests

base_url = 'http://127.0.0.2:5000/api'
# Register
res = requests.post(f'{base_url}/auth/signup', json={
    'full_name': 'Test User',
    'email': 'testnotif2@example.com',
    'mobile': '9876543211',
    'password': 'Password123!',
    'confirm_password': 'Password123!'
})

if res.status_code == 409: # Already registered
    res = requests.post(f'{base_url}/auth/login', json={
        'email': 'testnotif2@example.com',
        'password': 'Password123!'
    })

token = res.json().get('data', {}).get('access_token')
if not token:
    print('Failed to get token:', res.json())
    exit(1)

# Fetch notifications
notif_res = requests.get(f'{base_url}/notifications', headers={'Authorization': f'Bearer {token}'})
print('STATUS 1:', notif_res.status_code)
print('RESPONSE 1:', notif_res.text)

notif_res = requests.get(f'{base_url}/notifications/', headers={'Authorization': f'Bearer {token}'})
print('STATUS 2:', notif_res.status_code)
print('RESPONSE 2:', notif_res.text)

