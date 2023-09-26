import concurrent.futures
import requests

def execute_parallel_requests(url, headers, num_requests, params):
    def send_request(_):
        try:
            response = requests.post(url, headers=headers, params=params)
            response.raise_for_status()
            return response.status_code, response.text
        except Exception as e:
            return None, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        results = list(executor.map(send_request, range(num_requests)))

    return results

# Example usage:
url = 'http://localhost:8080/testing'
headers = {
    'accept': 'application/json',
    'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImFhMDhlN2M3ODNkYjhjOGFjNGNhNzJhZjdmOWRkN2JiMzk4ZjE2ZGMiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiTmVrbyBOaWsiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EtL0FMVi1ValdCT2ZLTmRJQjR3LUtnUmtMdUVmekdGMXphVTBWZnlhOTA2elVVNGkwbHRqRjRFSTQ4ME5SY1ZfbVpOV3lfdTBnRjV3bV9TN0RNTlVrSDlhSlBfQTBlNDhLT2lTbnJBSTM0UkgwZHhrZGpsLVdYMkR5NkZIckdBMDNTR0YweUg1OXcyblk3UWF5QllRMkxia1pMTG5KZWlPdWNoUE8wd01nMjdPX1U4Ui1TMzdJUXJ6VHV4ZHZJMG9ja0J5V2tSV3BmZUhOZnJ2dTlic3V4V1JmQUxnZEFFd3pxaTdqNWN1bk5JQlZzNkJJNjBFSFNoSU45ekVyRUdsUGJvWlRiVk9rbDBhOGtKUWlZZElVQnZtT21kQlpiUmZPWm9lcTI4Y1k2WE9jSUYxS2xIcm5PSklLVzdVaXYtTi1VRFdpTWVkV0p0U3ZtY1IzSG9DNmVsNmpqZ05GT2t2UUxJWUhCMXRaUDNhY2h4eWVkWDM2WWdsNmhyRVZmbzZmakxrT3U3WEpwYnpkOENBSnY4YnpWQW83MWItb0tlNDBCdTFmTXlEbU0wb3BzWmdmWDFiM3dTWmhzU29iXzUtclNoZ2VfRXB2VFZlQ0FSakFuVTA5Vm5VNkNfOFdrRm5VY3JkWDJFdkwwNVRuNF90RE93TmxQMXMxYmwyTHVfNG5yeXYySm9hVHJxX0VIeWktS1F5QXdZdE4yWmpXYmZTdzk1WTRNd3g2T09xVlBQZTZtTnY5WVZLakl6dnYtcE5HaGFYUy1Gc3U4bFB2VEp3UWxlNGNtbU8wLTRJbW1BVGVqdUdfZHFzSFZaeUlxNUNPNXJtOWZUcUY1ZHVhcFlGd0JkbEl0QVRENHJYcnJ1MU84QWdlWEhTT1pYajJPdHNpdGFIdEZBM01obGl2b0xUaXZfTEx2MU16M0g1N0JWeV82NmItQUhrLU16UXNWUnA2YVdMVnZTR2pEMzFCc0JkV1FOeTJIT0FOOGEtVW85bFdjWXFuU2RIYW41QkhtenJzdjJzZXRZbS1OekNvb285SEdoVTBJZkREbjJabHU1WWM2MkJxYmJSVzNyNTk4SWt2WnNFbmJTU0h2S00xbEdXQ0d3c1ZjQU9uY1hGUWpTYl8wcG1PSHczUVVuSXZjS0NzMTFmOVg3Ylpjc3ppdjE3SGZtSm0yV0N1Y0tsd3AzUzZhclJiZ2M4R21PMjJZUmZYVGdoSzFOc19NNTRHY1VNbFk2N29SbkZVc2xsUkVJRXhyUE9xcF8zTEZSQUZGQXNLVjlTRkFQcEtFPXM5Ni1jIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL25la28tbmlrIiwiYXVkIjoibmVrby1uaWsiLCJhdXRoX3RpbWUiOjE2OTU1NDM0MTcsInVzZXJfaWQiOiJpS0U1dVpwSGpVVnVCS0pocjdzc29NdFdWbXMxIiwic3ViIjoiaUtFNXVacEhqVVZ1QktKaHI3c3NvTXRXVm1zMSIsImlhdCI6MTY5NTU1MTk4OCwiZXhwIjoxNjk1NTU1NTg4LCJlbWFpbCI6InRhbmRsZW5pa2hpbHJhakBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJnb29nbGUuY29tIjpbIjExNTEyMDIzOTMzMTI4MDUyNTE0MCJdLCJlbWFpbCI6WyJ0YW5kbGVuaWtoaWxyYWpAZ21haWwuY29tIl19LCJzaWduX2luX3Byb3ZpZGVyIjoiZ29vZ2xlLmNvbSJ9fQ.AH-CfseXxZyFjseIk1UUbvHeU3hSEEB0QU3_ggnLZKHD6bwHMmBzwd-Ihq9oFJ2DhmKhAlKx-zZLAT1Isybnv3TvVORwDSUa-NhWsHjwNY53K3-sRZM2of8EGpaxn3D0OCGsPvNQV89F-CdBHtrfwalNSw0i8jQfB5cGOR2Qxj6yLsyqwnov9CSkckHYa-5JdVnyBiTkKYQNkdjIKyro3d2PJ8_KbdnKBcf3Vr6JPsu1MGsaEtTUKPIt-Py86q5llKt8070dPuj5CEu-cqXNiveX-i7-CAWWTdUaxyzEcR_jPmogXUskwjfHZLQG7UqEkbygBt9BU5489Nk0usA_Aw'
}
params = {
    'user_email': 'tandlenikhilraj@gmail.com'
}
num_requests = 2000

results = execute_parallel_requests(url, headers, num_requests, params)

# Print the results
for idx, (status_code, response_text) in enumerate(results, start=1):
    if status_code is not None:
        print(f"Request {idx}: Status Code {status_code}")
        # You can process the response_text here as needed.
    else:
        print(f"Request {idx}: Failed - {response_text}")
