## The script is used to start the API and will not effect the running API
## Change the path of the virtualenv and the gunicorn command accordingly

#start the gpt api
cd /home/nikhil/Repositories/ScrapeN && source .venv/bin/activate

#start the gpt api
gunicorn --workers=3 --threads=3 --reload --bind 0.0.0.0:443 --timeout 2500 --keyfile=/etc/letsencrypt/live/api.scrape-n.com/privkey.pem --certfile=/etc/letsencrypt/live/api.scrape-n.com/fullchain.pem --reload --capture-output --error-logfile logs/error_log.txt --access-logfile logs/guicorn_log.txt -k uvicorn.workers.UvicornWorker app:app &