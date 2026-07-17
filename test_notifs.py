import requests

base_url = 'http://127.0.0.1:5000/api'
# Register
res = requests.post(f'{base_url}/auth/signup', json={
    'full_name': 'Test User',
    'email': 'testnotif@example.com',
    'mobile': '9876543210',
    'password': 'Password123!',
    'confirm_password': 'Password123!'
})

if res.status_code == 409: # Already registered
    res = requests.post(f'{base_url}/auth/login', json={
        'email': 'testnotif@example.com',
        'password': 'Password123!'
    })

token = res.json().get('data', {}).get('access_token')
if not token:
    print('Failed to get token:', res.json())
    exit(1)

# Fetch notifications
notif_res = requests.get(f'{base_url}/notifications/', headers={'Authorization': f'Bearer {token}'})
print('STATUS:', notif_res.status_code)
print('RESPONSE:', notif_res.text)
