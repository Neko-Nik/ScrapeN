import concurrent.futures
import requests

def execute_parallel_requests(url, headers, num_requests, params):
    def send_request(_):
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.status_code, response.text
        except Exception as e:
            return None, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        results = list(executor.map(send_request, range(num_requests)))

    return results

# Example usage:
url = 'http://localhost:8080/job/list'
headers = {
    'accept': 'application/json',
    'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImFkNWM1ZTlmNTdjOWI2NDYzYzg1ODQ1YTA4OTlhOWQ0MTI5MmM4YzMiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiTmVrbyIsImlzcyI6Imh0dHBzOi8vc2VjdXJldG9rZW4uZ29vZ2xlLmNvbS9uZWtvLW5payIsImF1ZCI6Im5la28tbmlrIiwiYXV0aF90aW1lIjoxNjk1NzM0OTIxLCJ1c2VyX2lkIjoiVUpsQXNLNnc2ZmRPUGZoQktSbWtkUGUxZ3hRMiIsInN1YiI6IlVKbEFzSzZ3NmZkT1BmaEJLUm1rZFBlMWd4UTIiLCJpYXQiOjE2OTU3NDMwNzcsImV4cCI6MTY5NTc0NjY3NywiZW1haWwiOiJjb21peWFzOTM1QGJub3ZlbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJjb21peWFzOTM1QGJub3ZlbC5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJwYXNzd29yZCJ9fQ.VE3d4nUyJpCj9Ueglru5Do5fPzsSqUjzykT2S34yHeSDdUn0AW3jDwZGSVxjTp8TOo7UDGKUT_YRo9jYdwL_K5zHaxIQhoAOi1Da1oOFfT0v7fWeYoE1Drmy8yZgHzDREdabKkBlM99Nui0gnqv8tlXLhGqdJc5uqndJydQSIZtb2lQgaeXy30F4wps1_bbnjUyvFR0JueYbe-E8yCdMzq3UTxP9kzVSv1KayghmufSTDVR8ECOdNAoUxAOqXKimHGXCI6BJmUdhOOOwQUAEpXRaEtQwT3arQeNPuWoVdeqsUYwYhi4mDbifRgP2DhbUJCZ91dDmN5hXmePRzAgwSg'
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
