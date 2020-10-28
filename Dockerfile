FROM python:3.7

WORKDIR  /opt/app/

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "/opt/app/src/lpr_api.py"]
# Run container as:
#     docker run -v (pwd):/opt/app -p 5000:5000 lpr
